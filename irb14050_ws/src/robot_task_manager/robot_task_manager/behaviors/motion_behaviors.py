"""Motion-related behavior-tree behaviours."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import py_trees
from geometry_msgs.msg import Pose
from rclpy.action import ActionClient

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior
from robot_task_manager.utils.command_utils import describe_command
from robot_task_msgs.action import MoveJoint

try:
    from moveit_msgs.action import ExecuteTrajectory, MoveGroup
    from moveit_msgs.msg import (
        BoundingVolume,
        Constraints,
        JointConstraint,
        MoveItErrorCodes,
        MotionPlanRequest,
        OrientationConstraint,
        PositionConstraint,
    )
    from moveit_msgs.srv import GetCartesianPath
    from shape_msgs.msg import SolidPrimitive

    MOVEIT_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on robot deployment image.
    ExecuteTrajectory = None
    MoveGroup = None
    BoundingVolume = None
    Constraints = None
    JointConstraint = None
    MoveItErrorCodes = None
    MotionPlanRequest = None
    OrientationConstraint = None
    PositionConstraint = None
    GetCartesianPath = None
    SolidPrimitive = None
    MOVEIT_AVAILABLE = False


class CancelArmGoals(BlackboardBehavior):
    """Cancel active arm activity and mark the blackboard as no longer busy."""

    def update(self) -> py_trees.common.Status:
        self.node.get_logger().warn("Cancelling active arm goals")
        self.bb_set(bb_keys.ARM_BUSY, False)
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.publish_zero_twist()
        self.set_status(mode="IDLE", message="Arm goals cancelled", progress=0.0)
        return py_trees.common.Status.SUCCESS


class BuildJointGoal(BlackboardBehavior):
    """Build a full joint vector from a RobotCommand."""

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if command is None:
            self.set_status(mode="ERROR", message="No command for joint goal", error_code="NO_COMMAND")
            return py_trees.common.Status.FAILURE

        joint_count = int(self.node.joint_count)
        current = list(self.bb_get(bb_keys.JOINT_STATE_DEG, [0.0] * joint_count))
        if len(current) != joint_count:
            current = [0.0] * joint_count

        if command.joint_values:
            goal = [float(value) for value in command.joint_values]
        else:
            if command.joint_id < 1 or command.joint_id > joint_count:
                self.set_status(
                    mode="ERROR",
                    message=f"Invalid joint_id {command.joint_id}",
                    error_code="INVALID_JOINT_ID",
                )
                return py_trees.common.Status.FAILURE

            goal = current[:]
            index = command.joint_id - 1
            if command.relative:
                goal[index] = current[index] + float(command.joint_delta_deg)
            else:
                goal[index] = float(command.joint_target_deg)

        self.bb_set(bb_keys.JOINT_GOAL, goal)
        self.set_status(
            mode="VOICE_JOINT",
            message=f"Built joint goal: {[round(v, 2) for v in goal]}",
            progress=0.05,
            current_task=describe_command(command),
            error_code="",
        )
        return py_trees.common.Status.SUCCESS


class ValidateJointGoal(BlackboardBehavior):
    """Validate a joint vector with the configured joint limits."""

    def update(self) -> py_trees.common.Status:
        goal = self.bb_get(bb_keys.JOINT_GOAL)
        if goal is None:
            self.set_status(mode="ERROR", message="No joint goal to validate", error_code="NO_JOINT_GOAL")
            return py_trees.common.Status.FAILURE

        valid, message = self.node.joint_limits.validate(goal)
        if not valid:
            self.node.get_logger().error(f"Rejected joint goal: {message}")
            self.set_status(mode="ERROR", message=message, error_code="JOINT_LIMIT")
            self.bb_set(bb_keys.CURRENT_COMMAND, None)
            self.bb_set(bb_keys.JOINT_GOAL, None)
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.FAILURE

        self.set_status(mode="VOICE_JOINT", message="Joint goal validated", progress=0.10, error_code="")
        return py_trees.common.Status.SUCCESS


class ExecuteJointGoal(BlackboardBehavior):
    """Execute a joint goal through simulation, MoveIt, or a MoveJoint action server."""

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._start_time: float | None = None
        self._action_client: ActionClient | None = None
        self._move_group_client: ActionClient | None = None
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._failed_message: str | None = None
        self._wait_error: tuple[str, str] | None = None
        if not self.node.simulation_mode and self.node.motion_backend == "abb_moveit" and MOVEIT_AVAILABLE:
            self._move_group_client = ActionClient(self.node, MoveGroup, self.node.move_group_action_name)
        elif not self.node.simulation_mode:
            self._action_client = ActionClient(self.node, MoveJoint, self.node.arm_action_name)

    def initialise(self) -> None:
        self._start_time = self.now()
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._failed_message = None
        self._wait_error = None
        self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode="VOICE_JOINT", message="Executing joint goal", progress=0.10)

    def update(self) -> py_trees.common.Status:
        goal = self.bb_get(bb_keys.JOINT_GOAL)
        if goal is None:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(mode="ERROR", message="No joint goal", error_code="NO_JOINT_GOAL")
            return py_trees.common.Status.FAILURE

        if self.node.simulation_mode:
            return self._update_simulation(goal)

        if self.node.motion_backend == "abb_moveit":
            return self._update_moveit_joint(goal)

        return self._update_action(goal)

    def _update_simulation(self, goal: list[float]) -> py_trees.common.Status:
        duration = max(0.05, float(self.node.simulation_motion_duration_s))
        elapsed = self.now() - (self._start_time or self.now())
        progress = min(1.0, elapsed / duration)
        self.set_status(
            mode="VOICE_JOINT",
            message="Simulating joint move",
            progress=0.10 + 0.90 * progress,
            error_code="",
        )
        if progress >= 1.0:
            self.bb_set(bb_keys.JOINT_STATE_DEG, list(goal))
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.node.get_logger().info(f"Simulated joint goal reached: {[round(v, 2) for v in goal]}")
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING

    def _update_moveit_joint(self, goal: list[float]) -> py_trees.common.Status:
        if not MOVEIT_AVAILABLE or self._move_group_client is None:
            return self._fail("MoveIt messages/action client unavailable", "MOVEIT_UNAVAILABLE")

        if self._send_future is None:
            if not self._wait_for_action_server(self._move_group_client, "move_group"):
                if self._wait_error is not None:
                    return self._fail(*self._wait_error)
                return py_trees.common.Status.RUNNING
            self._send_future = self._move_group_client.send_goal_async(
                self._build_move_group_joint_goal(goal)
            )
            return py_trees.common.Status.RUNNING

        return self._finish_move_group_result(goal)

    def _update_action(self, goal: list[float]) -> py_trees.common.Status:
        if self._action_client is None:
            return self._fail("Action client unavailable", "NO_ACTION_CLIENT")

        if self._send_future is None:
            if not self._action_client.server_is_ready():
                return self._fail(f"Action server not ready: {self.node.arm_action_name}", "ACTION_SERVER_NOT_READY")

            goal_msg = MoveJoint.Goal()
            goal_msg.joint_values = list(goal)
            goal_msg.max_velocity_scaling = 0.2
            goal_msg.max_acceleration_scaling = 0.2
            self._send_future = self._action_client.send_goal_async(
                goal_msg,
                feedback_callback=self._feedback_callback,
            )
            return py_trees.common.Status.RUNNING

        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                return self._fail("MoveJoint goal rejected", "GOAL_REJECTED")
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        self.bb_set(bb_keys.ARM_BUSY, False)
        if result.success:
            self.bb_set(bb_keys.JOINT_STATE_DEG, list(goal))
            self.set_status(mode="VOICE_JOINT", message=result.message, progress=1.0, error_code="")
            return py_trees.common.Status.SUCCESS

        self.set_status(mode="ERROR", message=result.message, error_code="MOVE_JOINT_FAILED")
        return py_trees.common.Status.FAILURE

    def _build_move_group_joint_goal(self, values_deg: list[float]):
        goal_msg = MoveGroup.Goal()
        request = self._base_motion_plan_request()
        constraints = Constraints()
        for name, value_deg in zip(self.node.joint_names, values_deg):
            joint_constraint = JointConstraint()
            joint_constraint.joint_name = name
            joint_constraint.position = math.radians(float(value_deg))
            joint_constraint.tolerance_above = math.radians(1.0)
            joint_constraint.tolerance_below = math.radians(1.0)
            joint_constraint.weight = 1.0
            constraints.joint_constraints.append(joint_constraint)
        request.goal_constraints.append(constraints)
        goal_msg.request = request
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.replan = True
        goal_msg.planning_options.replan_attempts = 3
        goal_msg.planning_options.planning_scene_diff.is_diff = True
        goal_msg.planning_options.planning_scene_diff.robot_state.is_diff = True
        return goal_msg

    def _base_motion_plan_request(self):
        request = MotionPlanRequest()
        request.group_name = self.node.planning_group
        request.num_planning_attempts = 5
        request.allowed_planning_time = self.node.planning_time
        request.max_velocity_scaling_factor = self.node.velocity_scale
        request.max_acceleration_scaling_factor = self.node.velocity_scale * 0.5
        request.workspace_parameters.header.frame_id = self.node.base_frame
        request.workspace_parameters.min_corner.x = self.node.workspace_min_x
        request.workspace_parameters.min_corner.y = self.node.workspace_min_y
        request.workspace_parameters.min_corner.z = self.node.workspace_min_z
        request.workspace_parameters.max_corner.x = self.node.workspace_max_x
        request.workspace_parameters.max_corner.y = self.node.workspace_max_y
        request.workspace_parameters.max_corner.z = self.node.workspace_max_z
        request.start_state.is_diff = True
        return request

    def _finish_move_group_result(self, goal: list[float]) -> py_trees.common.Status:
        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                return self._fail("MoveGroup joint goal rejected", "GOAL_REJECTED")
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        success = result.error_code.val == MoveItErrorCodes.SUCCESS
        self.bb_set(bb_keys.ARM_BUSY, False)
        if success:
            self.bb_set(bb_keys.JOINT_STATE_DEG, list(goal))
            self.set_status(mode="VOICE_JOINT", message="MoveIt joint goal complete", progress=1.0, error_code="")
            return py_trees.common.Status.SUCCESS
        return self._fail(f"MoveIt joint goal failed: {result.error_code.val}", "MOVEIT_JOINT_FAILED")

    def _wait_for_action_server(self, client: ActionClient, label: str) -> bool:
        if client.server_is_ready():
            return True
        elapsed = self.now() - (self._start_time or self.now())
        if elapsed > self.node.action_server_timeout_s:
            self._wait_error = (f"{label} action server timeout", "ACTION_SERVER_TIMEOUT")
            return False
        self.set_status(mode="VOICE_JOINT", message=f"Waiting for {label}", progress=0.10)
        return False

    def _feedback_callback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        self.set_status(
            mode="VOICE_JOINT",
            message=feedback.current_state,
            progress=float(feedback.progress),
        )

    def _fail(self, message: str, code: str) -> py_trees.common.Status:
        self.bb_set(bb_keys.ARM_BUSY, False)
        self.set_status(mode="ERROR", message=message, error_code=code)
        return py_trees.common.Status.FAILURE

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
            self.bb_set(bb_keys.ARM_BUSY, False)


class _MoveItPoseBehavior(BlackboardBehavior):
    """Execute a pose motion via MoveIt, or timed simulation in mock mode."""

    pose_key = ""
    mode = "move_group"
    fallback_to_ompl = False
    status_message = "Moving"
    progress_start = 0.60
    progress_end = 0.80

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._start_time: float | None = None
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._cartesian_future = None
        self._execute_send_future = None
        self._execute_result_future = None
        self._execute_goal_handle = None
        self._using_fallback = False
        self._wait_error: tuple[str, str] | None = None
        self._move_group_client = None
        self._execute_client = None
        self._cartesian_client = None
        if not self.node.simulation_mode and self.node.motion_backend == "abb_moveit" and MOVEIT_AVAILABLE:
            self._move_group_client = ActionClient(self.node, MoveGroup, self.node.move_group_action_name)
            self._execute_client = ActionClient(
                self.node,
                ExecuteTrajectory,
                self.node.execute_trajectory_action_name,
            )
            self._cartesian_client = self.node.create_client(
                GetCartesianPath,
                self.node.cartesian_path_service_name,
            )

    def initialise(self) -> None:
        self._start_time = self.now()
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._cartesian_future = None
        self._execute_send_future = None
        self._execute_result_future = None
        self._execute_goal_handle = None
        self._using_fallback = False
        self._wait_error = None
        self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode="VOICE_PICK", message=self.status_message, progress=self.progress_start)

    def update(self) -> py_trees.common.Status:
        if self.node.simulation_mode:
            return self._update_simulation()

        if self.node.motion_backend != "abb_moveit":
            return self._fail(
                "Refusing real motion without motion_backend=abb_moveit",
                "NO_REAL_MOTION_BACKEND",
            )

        if not MOVEIT_AVAILABLE:
            return self._fail("MoveIt Python interfaces unavailable", "MOVEIT_UNAVAILABLE")

        pose = self.bb_get(self.pose_key)
        if pose is None:
            return self._fail(f"Missing pose for {self.name}", "MISSING_POSE")

        if self.mode == "cartesian" and not self._using_fallback:
            return self._update_cartesian(pose)
        return self._update_move_group_pose(pose)

    def _update_simulation(self) -> py_trees.common.Status:
        duration = max(0.05, float(self.node.simulation_motion_duration_s))
        elapsed = self.now() - (self._start_time or self.now())
        fraction = min(1.0, elapsed / duration)
        progress = self.progress_start + (self.progress_end - self.progress_start) * fraction
        self.set_status(mode="VOICE_PICK", message=f"Simulating {self.status_message}", progress=progress)
        if fraction >= 1.0:
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING

    def _update_move_group_pose(self, pose) -> py_trees.common.Status:
        if self._move_group_client is None:
            return self._fail("MoveGroup client unavailable", "MOVE_GROUP_UNAVAILABLE")
        if self._send_future is None:
            if not self._wait_for_action_server(self._move_group_client, "move_group"):
                if self._wait_error is not None:
                    return self._fail(*self._wait_error)
                return py_trees.common.Status.RUNNING
            p = pose.pose.position
            q = pose.pose.orientation
            self.node.get_logger().info(
                f"{self.name} target in {pose.header.frame_id}: "
                f"p=({p.x:.3f}, {p.y:.3f}, {p.z:.3f}), "
                f"q=({q.x:.3f}, {q.y:.3f}, {q.z:.3f}, {q.w:.3f}), "
                f"pos_tol={self.node.pose_position_tolerance_m:.3f} m, "
                f"ori_tol={self.node.pose_orientation_tolerance_rad:.3f} rad"
            )
            self._send_future = self._move_group_client.send_goal_async(
                self._build_move_group_pose_goal(pose)
            )
            return py_trees.common.Status.RUNNING
        return self._finish_move_group_result()

    def _update_cartesian(self, pose) -> py_trees.common.Status:
        if self._cartesian_client is None or self._execute_client is None:
            return self._fail("Cartesian MoveIt clients unavailable", "CARTESIAN_UNAVAILABLE")

        if self._cartesian_future is None:
            if not self._wait_for_service(self._cartesian_client, "compute_cartesian_path"):
                if self._wait_error is not None:
                    return self._fail(*self._wait_error)
                return py_trees.common.Status.RUNNING
            request = GetCartesianPath.Request()
            request.header = pose.header
            request.group_name = self.node.planning_group
            request.link_name = self.node.ee_frame
            request.waypoints = [pose.pose]
            request.max_step = self.node.cartesian_max_step
            request.jump_threshold = 0.0
            request.avoid_collisions = True
            request.max_velocity_scaling_factor = self.node.velocity_scale * 0.5
            request.max_acceleration_scaling_factor = self.node.velocity_scale * 0.25
            self._cartesian_future = self._cartesian_client.call_async(request)
            return py_trees.common.Status.RUNNING

        if not self._cartesian_future.done():
            return py_trees.common.Status.RUNNING

        result = self._cartesian_future.result()
        if result is None:
            return self._cartesian_fallback_or_fail("Cartesian path service returned no result")

        if result.fraction < self.node.cartesian_min_fraction:
            return self._cartesian_fallback_or_fail(
                f"Cartesian path incomplete: fraction={result.fraction:.2f}"
            )

        if self._execute_send_future is None:
            if not self._wait_for_action_server(self._execute_client, "execute_trajectory"):
                if self._wait_error is not None:
                    return self._fail(*self._wait_error)
                return py_trees.common.Status.RUNNING
            goal = ExecuteTrajectory.Goal()
            goal.trajectory = result.solution
            self._execute_send_future = self._execute_client.send_goal_async(goal)
            return py_trees.common.Status.RUNNING

        if self._execute_goal_handle is None:
            if not self._execute_send_future.done():
                return py_trees.common.Status.RUNNING
            self._execute_goal_handle = self._execute_send_future.result()
            if not self._execute_goal_handle.accepted:
                return self._fail("ExecuteTrajectory goal rejected", "EXECUTE_REJECTED")
            self._execute_result_future = self._execute_goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._execute_result_future is None or not self._execute_result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._execute_result_future.result().result
        success = result.error_code.val == MoveItErrorCodes.SUCCESS
        if success:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(mode="VOICE_PICK", message=f"{self.status_message} complete", progress=self.progress_end)
            return py_trees.common.Status.SUCCESS
        return self._fail(f"ExecuteTrajectory failed: {result.error_code.val}", "EXECUTE_FAILED")

    def _cartesian_fallback_or_fail(self, message: str) -> py_trees.common.Status:
        if not self.fallback_to_ompl:
            return self._fail(message, "CARTESIAN_FAILED")
        self.node.get_logger().warn(f"{message}; falling back to MoveGroup")
        self._using_fallback = True
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        return py_trees.common.Status.RUNNING

    def _build_move_group_pose_goal(self, target_pose):
        goal_msg = MoveGroup.Goal()
        request = MotionPlanRequest()
        request.group_name = self.node.planning_group
        request.num_planning_attempts = 5
        request.allowed_planning_time = self.node.planning_time
        request.max_velocity_scaling_factor = self.node.velocity_scale
        request.max_acceleration_scaling_factor = self.node.velocity_scale * 0.5
        request.workspace_parameters.header.frame_id = self.node.base_frame
        request.workspace_parameters.min_corner.x = self.node.workspace_min_x
        request.workspace_parameters.min_corner.y = self.node.workspace_min_y
        request.workspace_parameters.min_corner.z = self.node.workspace_min_z
        request.workspace_parameters.max_corner.x = self.node.workspace_max_x
        request.workspace_parameters.max_corner.y = self.node.workspace_max_y
        request.workspace_parameters.max_corner.z = self.node.workspace_max_z

        constraints = Constraints()
        position_constraint = PositionConstraint()
        position_constraint.header = target_pose.header
        position_constraint.link_name = self.node.ee_frame
        position_constraint.weight = 1.0
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [float(self.node.pose_position_tolerance_m)]
        sphere_pose = Pose()
        sphere_pose.position = target_pose.pose.position
        sphere_pose.orientation.w = 1.0
        volume = BoundingVolume()
        volume.primitives.append(sphere)
        volume.primitive_poses.append(sphere_pose)
        position_constraint.constraint_region = volume
        constraints.position_constraints.append(position_constraint)

        orientation_constraint = OrientationConstraint()
        orientation_constraint.header = target_pose.header
        orientation_constraint.link_name = self.node.ee_frame
        orientation_constraint.orientation = target_pose.pose.orientation
        orientation_tolerance = float(self.node.pose_orientation_tolerance_rad)
        orientation_constraint.absolute_x_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_y_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_z_axis_tolerance = orientation_tolerance
        orientation_constraint.weight = 1.0
        constraints.orientation_constraints.append(orientation_constraint)

        request.goal_constraints.append(constraints)
        goal_msg.request = request
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.replan = True
        goal_msg.planning_options.replan_attempts = 3
        return goal_msg

    def _finish_move_group_result(self) -> py_trees.common.Status:
        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                return self._fail("MoveGroup goal rejected", "GOAL_REJECTED")
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        success = result.error_code.val == MoveItErrorCodes.SUCCESS
        if success:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(mode="VOICE_PICK", message=f"{self.status_message} complete", progress=self.progress_end)
            return py_trees.common.Status.SUCCESS
        self.node.get_logger().error(
            f"{self.name} MoveGroup failed with error_code={result.error_code.val}"
        )
        return self._fail(f"MoveGroup failed: {result.error_code.val}", "MOVE_GROUP_FAILED")

    def _wait_for_action_server(self, client: ActionClient, label: str) -> bool:
        if client.server_is_ready():
            return True
        elapsed = self.now() - (self._start_time or self.now())
        if elapsed > self.node.action_server_timeout_s:
            self._wait_error = (f"{label} action server timeout", "ACTION_SERVER_TIMEOUT")
            return False
        self.set_status(mode="VOICE_PICK", message=f"Waiting for {label}", progress=self.progress_start)
        return False

    def _wait_for_service(self, client, label: str) -> bool:
        if client.service_is_ready():
            return True
        elapsed = self.now() - (self._start_time or self.now())
        if elapsed > self.node.action_server_timeout_s:
            self._wait_error = (f"{label} service timeout", "SERVICE_TIMEOUT")
            return False
        self.set_status(mode="VOICE_PICK", message=f"Waiting for {label}", progress=self.progress_start)
        return False

    def _fail(self, message: str, code: str) -> py_trees.common.Status:
        self.bb_set(bb_keys.ARM_BUSY, False)
        self.set_status(mode="ERROR", message=message, error_code=code)
        return py_trees.common.Status.FAILURE

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
            if self._execute_goal_handle is not None:
                self._execute_goal_handle.cancel_goal_async()
            self.bb_set(bb_keys.ARM_BUSY, False)


class MoveToPerceptionPose(ExecuteJointGoal):
    """Move to the SRDF group_state used for perception before detecting objects."""

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._goal_error: tuple[str, str] | None = None

    def initialise(self) -> None:
        self._goal_error = None
        goal = self._load_perception_group_state()
        if goal is None:
            return

        valid, message = self.node.joint_limits.validate(goal)
        if not valid:
            self._goal_error = (message, "PERCEPTION_JOINT_LIMIT")
            return

        self.bb_set(bb_keys.JOINT_GOAL, goal)
        super().initialise()
        self.set_status(
            mode="VOICE_PICK",
            message=f"Moving to perception pose '{self.node.perception_group_state_name}'",
            progress=0.02,
        )

    def update(self) -> py_trees.common.Status:
        if self._goal_error is not None:
            message, code = self._goal_error
            self.set_status(mode="ERROR", message=message, error_code=code)
            return py_trees.common.Status.FAILURE

        result = super().update()
        if result == py_trees.common.Status.RUNNING:
            self.set_status(
                mode="VOICE_PICK",
                message=f"Moving to perception pose '{self.node.perception_group_state_name}'",
                progress=0.12,
            )
        elif result == py_trees.common.Status.SUCCESS:
            self.set_status(
                mode="VOICE_PICK",
                message=f"Reached perception pose '{self.node.perception_group_state_name}'",
                progress=0.15,
                error_code="",
            )
        return result

    def _load_perception_group_state(self) -> list[float] | None:
        srdf_path = Path(self.node.srdf_file)
        state_name = self.node.perception_group_state_name
        group_name = self.node.planning_group
        if not srdf_path.exists():
            self._goal_error = (f"SRDF file not found: {srdf_path}", "SRDF_NOT_FOUND")
            return None

        try:
            root = ET.parse(srdf_path).getroot()
        except ET.ParseError as exc:
            self._goal_error = (f"Could not parse SRDF: {exc}", "SRDF_PARSE_ERROR")
            return None

        group_state = None
        for candidate in root.findall("group_state"):
            if candidate.get("name") == state_name and candidate.get("group") == group_name:
                group_state = candidate
                break

        if group_state is None:
            self._goal_error = (
                f"SRDF group_state '{state_name}' for group '{group_name}' not found",
                "GROUP_STATE_NOT_FOUND",
            )
            return None

        values_rad = {
            joint.get("name"): float(joint.get("value", "nan"))
            for joint in group_state.findall("joint")
            if joint.get("name")
        }
        missing = [joint_name for joint_name in self.node.joint_names if joint_name not in values_rad]
        if missing:
            self._goal_error = (
                f"SRDF group_state '{state_name}' missing joints: {missing}",
                "GROUP_STATE_INCOMPLETE",
            )
            return None

        return [math.degrees(values_rad[joint_name]) for joint_name in self.node.joint_names]

    def terminate(self, new_status: py_trees.common.Status) -> None:
        super().terminate(new_status)


class MoveToPreGrasp(_MoveItPoseBehavior):
    pose_key = bb_keys.PRE_GRASP_POSE
    mode = "move_group"
    status_message = "Moving to pre-grasp pose"
    progress_start = 0.65
    progress_end = 0.72


class MoveToGrasp(_MoveItPoseBehavior):
    pose_key = bb_keys.GRASP_POSE
    mode = "cartesian"
    status_message = "Moving to grasp pose"
    progress_start = 0.72
    progress_end = 0.80


class Retreat(_MoveItPoseBehavior):
    pose_key = bb_keys.RETREAT_POSE
    mode = "cartesian"
    status_message = "Retreating from grasp"
    progress_start = 0.84
    progress_end = 0.90


class MoveToPlacePose(_MoveItPoseBehavior):
    pose_key = bb_keys.PLACE_POSE
    mode = "cartesian"
    fallback_to_ompl = True
    status_message = "Moving to place pose"
    progress_start = 0.90
    progress_end = 0.97
