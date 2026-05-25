"""Sequence loading, validation, and execution behaviours."""

from __future__ import annotations

from pathlib import Path
import math

import py_trees
import yaml
from rclpy.action import ActionClient

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior
from robot_task_manager.behaviors.motion_behaviors import (
    MOVEIT_AVAILABLE,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    MoveGroup,
    MoveItErrorCodes,
)
from robot_task_msgs.action import MoveJoint


class LoadSequence(BlackboardBehavior):
    """Load a named sequence from the configured YAML file."""

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if command is None:
            self.set_status(mode="ERROR", message="No sequence command", error_code="NO_COMMAND")
            return py_trees.common.Status.FAILURE

        sequence_path = Path(self.node.sequences_file)
        if not sequence_path.exists():
            self.set_status(
                mode="ERROR",
                message=f"Sequences file not found: {sequence_path}",
                error_code="SEQUENCE_FILE_MISSING",
            )
            return py_trees.common.Status.FAILURE

        data = yaml.safe_load(sequence_path.read_text(encoding="utf-8")) or {}
        entry = data.get(command.sequence_id)
        if entry is None:
            self.set_status(
                mode="ERROR",
                message=f"Unknown sequence: {command.sequence_id}",
                error_code="UNKNOWN_SEQUENCE",
            )
            return py_trees.common.Status.FAILURE

        steps = list(entry.get("steps", []))
        self.bb_set(bb_keys.SEQUENCE_STEPS, steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Loaded sequence {command.sequence_id}: {entry.get('description', '')}",
            progress=0.05,
            error_code="",
            current_task=f"sequence {command.sequence_id}",
        )
        return py_trees.common.Status.SUCCESS


class ValidateSequence(BlackboardBehavior):
    """Validate step types and joint values before execution."""

    VALID_STEP_TYPES = {"move_joints", "gripper", "pick_object"}

    def update(self) -> py_trees.common.Status:
        steps = list(self.bb_get(bb_keys.SEQUENCE_STEPS, []))
        if not steps:
            self.set_status(mode="ERROR", message="Sequence has no steps", error_code="EMPTY_SEQUENCE")
            return py_trees.common.Status.FAILURE

        for index, step in enumerate(steps):
            step_type = step.get("type")
            if step_type not in self.VALID_STEP_TYPES:
                self.set_status(
                    mode="ERROR",
                    message=f"Invalid step type at {index}: {step_type}",
                    error_code="INVALID_SEQUENCE_STEP",
                )
                return py_trees.common.Status.FAILURE

            if step_type == "move_joints":
                valid, message = self.node.joint_limits.validate(step.get("joint_values_deg", []))
                if not valid:
                    self.set_status(mode="ERROR", message=message, error_code="SEQUENCE_JOINT_LIMIT")
                    return py_trees.common.Status.FAILURE

            if step_type == "gripper" and step.get("command") not in {"open", "close"}:
                self.set_status(mode="ERROR", message="Invalid gripper command", error_code="INVALID_GRIPPER")
                return py_trees.common.Status.FAILURE

        self.set_status(mode="WEB_SEQUENCE", message="Sequence validated", progress=0.10, error_code="")
        return py_trees.common.Status.SUCCESS


class ExecuteSequence(BlackboardBehavior):
    """Execute sequence steps through simulation or the configured motion backend."""

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._index = 0
        self._step_start: float | None = None
        self._published_step = -1
        self._move_group_client = None
        self._action_client = None
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._wait_error: tuple[str, str] | None = None
        if not self.node.simulation_mode and self.node.motion_backend == "abb_moveit" and MOVEIT_AVAILABLE:
            self._move_group_client = ActionClient(self.node, MoveGroup, self.node.move_group_action_name)
        elif not self.node.simulation_mode:
            self._action_client = ActionClient(self.node, MoveJoint, self.node.arm_action_name)

    def initialise(self) -> None:
        self._index = 0
        self._step_start = self.now()
        self._published_step = -1
        self._reset_motion_state()
        self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode="WEB_SEQUENCE", message="Executing sequence", progress=0.10)

    def update(self) -> py_trees.common.Status:
        steps = list(self.bb_get(bb_keys.SEQUENCE_STEPS, []))
        if not steps:
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.SUCCESS

        if self._index >= len(steps):
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(mode="WEB_SEQUENCE", message="Sequence complete", progress=1.0, error_code="")
            return py_trees.common.Status.SUCCESS

        step = steps[self._index]
        self._publish_step_start(step)

        if self._uses_real_moveit(step):
            return self._update_real_move_joints(step, len(steps))
        if self._uses_real_action(step):
            return self._update_action_move_joints(step, len(steps))

        duration = self._step_duration(step)
        elapsed = self.now() - (self._step_start or self.now())
        step_fraction = 1.0 if duration <= 0.0 else min(1.0, elapsed / duration)
        total_progress = (self._index + step_fraction) / max(1, len(steps))
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Step {self._index + 1}/{len(steps)}: {step.get('type')}",
            progress=total_progress,
        )

        if step_fraction < 1.0:
            return py_trees.common.Status.RUNNING

        self._finish_step(step)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        return py_trees.common.Status.RUNNING

    def _uses_real_moveit(self, step: dict) -> bool:
        return (
            not self.node.simulation_mode
            and self.node.motion_backend == "abb_moveit"
            and step.get("type") == "move_joints"
        )

    def _uses_real_action(self, step: dict) -> bool:
        return (
            not self.node.simulation_mode
            and self.node.motion_backend != "abb_moveit"
            and step.get("type") == "move_joints"
        )

    def _update_real_move_joints(self, step: dict, total_steps: int) -> py_trees.common.Status:
        if not MOVEIT_AVAILABLE or self._move_group_client is None:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message="MoveIt unavailable for real sequence step",
                error_code="MOVEIT_UNAVAILABLE",
            )
            return py_trees.common.Status.FAILURE

        values_deg = [float(value) for value in step.get("joint_values_deg", [])]
        self._set_real_move_status(total_steps)

        if self._send_future is None:
            if not self._wait_for_action_server(self._move_group_client, "move_group"):
                if self._wait_error is not None:
                    message, code = self._wait_error
                    self.bb_set(bb_keys.ARM_BUSY, False)
                    self.set_status(mode="ERROR", message=message, error_code=code)
                    return py_trees.common.Status.FAILURE
                return py_trees.common.Status.RUNNING
            self._send_future = self._move_group_client.send_goal_async(
                self._build_move_group_joint_goal(values_deg)
            )
            return py_trees.common.Status.RUNNING

        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                self.bb_set(bb_keys.ARM_BUSY, False)
                self.set_status(mode="ERROR", message="Sequence MoveGroup goal rejected", error_code="GOAL_REJECTED")
                return py_trees.common.Status.FAILURE
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=f"Sequence MoveGroup failed: {result.error_code.val}",
                error_code="SEQUENCE_MOVEIT_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self.bb_set(bb_keys.JOINT_STATE_DEG, values_deg)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        progress = self._index / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Sequence joint step {self._index}/{total_steps} complete",
            progress=progress,
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _update_action_move_joints(self, step: dict, total_steps: int) -> py_trees.common.Status:
        if self._action_client is None:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message="MoveJoint action client unavailable",
                error_code="ACTION_CLIENT_UNAVAILABLE",
            )
            return py_trees.common.Status.FAILURE

        values_deg = [float(value) for value in step.get("joint_values_deg", [])]
        self._set_real_move_status(total_steps)

        if self._send_future is None:
            if not self._wait_for_action_server(self._action_client, "move_joint"):
                if self._wait_error is not None:
                    message, code = self._wait_error
                    self.bb_set(bb_keys.ARM_BUSY, False)
                    self.set_status(mode="ERROR", message=message, error_code=code)
                    return py_trees.common.Status.FAILURE
                return py_trees.common.Status.RUNNING

            goal_msg = MoveJoint.Goal()
            goal_msg.joint_values = values_deg
            goal_msg.max_velocity_scaling = float(self.node.velocity_scale)
            goal_msg.max_acceleration_scaling = float(self.node.velocity_scale) * 0.5
            self._send_future = self._action_client.send_goal_async(goal_msg)
            return py_trees.common.Status.RUNNING

        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                self.bb_set(bb_keys.ARM_BUSY, False)
                self.set_status(mode="ERROR", message="Sequence MoveJoint goal rejected", error_code="GOAL_REJECTED")
                return py_trees.common.Status.FAILURE
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        if not result.success:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=result.message,
                error_code="SEQUENCE_MOVE_JOINT_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self.bb_set(bb_keys.JOINT_STATE_DEG, values_deg)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        progress = self._index / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Sequence joint step {self._index}/{total_steps} complete",
            progress=progress,
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _set_real_move_status(self, total_steps: int) -> None:
        duration = max(0.1, float(self.node.simulation_motion_duration_s))
        elapsed = self.now() - (self._step_start or self.now())
        step_fraction = min(0.95, elapsed / duration)
        progress = (self._index + step_fraction) / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Executing sequence joint step {self._index + 1}/{total_steps}",
            progress=progress,
        )

    def _step_duration(self, step: dict) -> float:
        step_type = step.get("type")
        if step_type == "gripper":
            return float(self.node.gripper_motion_duration_s)
        if step_type == "pick_object":
            return 1.0
        return float(self.node.simulation_motion_duration_s)

    def _publish_step_start(self, step: dict) -> None:
        if self._published_step == self._index:
            return
        self._published_step = self._index

        step_type = step.get("type")
        if step_type == "gripper":
            command = step.get("command", "open")
            self.node.publish_gripper_command(command)
            self.node.get_logger().info(f"Sequence gripper command: {command}")
        elif step_type == "move_joints":
            self.node.get_logger().info(f"Sequence move_joints: {step.get('joint_values_deg')}")
        elif step_type == "pick_object":
            self.node.get_logger().info(
                "Sequence pick_object: "
                f"{step.get('object_color', '')} {step.get('object_class', '')}"
            )

    def _finish_step(self, step: dict) -> None:
        if step.get("type") == "move_joints":
            self.bb_set(bb_keys.JOINT_STATE_DEG, [float(v) for v in step.get("joint_values_deg", [])])

    def _build_move_group_joint_goal(self, values_deg: list[float]):
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
        return goal_msg

    def _wait_for_action_server(self, client, label: str) -> bool:
        if client.server_is_ready():
            return True
        elapsed = self.now() - (self._step_start or self.now())
        if elapsed > self.node.action_server_timeout_s:
            self._wait_error = (f"{label} action server timeout", "ACTION_SERVER_TIMEOUT")
            return False
        self.set_status(mode="WEB_SEQUENCE", message=f"Waiting for {label}", progress=0.10)
        return False

    def _reset_motion_state(self) -> None:
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._wait_error = None

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
            self.bb_set(bb_keys.ARM_BUSY, False)
