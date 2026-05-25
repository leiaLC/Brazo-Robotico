#!/usr/bin/env python3
"""ROS 2 node that owns the central robot behavior tree."""

from __future__ import annotations

from pathlib import Path

import py_trees
import rclpy
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Twist
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Header, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.trees.robot_supervisor_tree import create_robot_supervisor_tree
from robot_task_manager.utils.command_utils import (
    command_rank,
    describe_command,
    mode_for_command,
    should_accept_command,
    validate_command,
)
from robot_task_manager.utils.joint_limits import JointLimitValidator
from robot_task_msgs.msg import Detection3D, RobotCommand, RobotStatus


class RobotTaskTreeNode(Node):
    """Central arbiter that is solely responsible for robot execution."""

    def __init__(self) -> None:
        super().__init__("robot_task_tree")

        self._declare_parameters()
        self._load_parameters()

        self.joint_limits = JointLimitValidator.from_yaml(self.joint_limits_file)
        if self.joint_count != self.joint_limits.joint_count:
            self.get_logger().warn(
                f"joint_count={self.joint_count} does not match limits file "
                f"({self.joint_limits.joint_count}); using limits file count"
            )
            self.joint_count = self.joint_limits.joint_count

        self.blackboard = py_trees.blackboard.Blackboard()
        self._initialise_blackboard()
        self._initialise_tf()

        self.command_sub = self.create_subscription(
            RobotCommand,
            "/robot_task/command",
            self._command_callback,
            10,
        )
        self.detection_sub = self.create_subscription(
            Detection3D,
            "/perception/detections_3d",
            self._detection_callback,
            10,
        )
        self.web_heartbeat_sub = self.create_subscription(
            Header,
            "/web/heartbeat",
            self._web_heartbeat_callback,
            10,
        )
        self.xbox_deadman_sub = self.create_subscription(
            Bool,
            "/xbox/deadman",
            self._xbox_deadman_callback,
            10,
        )
        self.joint_state_sub = self.create_subscription(
            JointState,
            self.joint_states_topic,
            self._joint_state_callback,
            10,
        )

        self.status_pub = self.create_publisher(RobotStatus, "/robot_task/status", 10)
        self.servo_pub = self.create_publisher(Twist, self.servo_twist_topic, 10)
        self.gripper_pub = self.create_publisher(String, self.gripper_command_topic, 10)
        self.gripper_trajectory_pub = self.create_publisher(
            JointTrajectory,
            self.gripper_trajectory_topic,
            10,
        )
        self.gripper_action_client = ActionClient(
            self,
            FollowJointTrajectory,
            self.gripper_action_name,
        )

        root = create_robot_supervisor_tree(self)
        self.tree = self._create_behaviour_tree(root)
        self._snapshot_visitor = None
        self._configure_introspection()

        self._detections: list[Detection3D] = []
        self._last_detection_time = 0.0
        self._last_tree_log_time = 0.0

        tick_period = 1.0 / max(1.0, float(self.tick_hz))
        self.tick_timer = self.create_timer(tick_period, self._tick_tree)

        self.get_logger().info(
            "robot_task_tree started "
            f"(tick_hz={self.tick_hz}, simulation_mode={self.simulation_mode})"
        )

    def _declare_parameters(self) -> None:
        self.declare_parameter("tick_hz", 20.0)
        self.declare_parameter("use_introspection", True)
        self.declare_parameter("simulation_mode", True)
        self.declare_parameter("motion_backend", "mock")
        self.declare_parameter("robot_ready_default", True)
        self.declare_parameter("joint_count", 7)
        self.declare_parameter(
            "joint_names",
            ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"],
        )
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("joint_limits_file", "")
        self.declare_parameter("sequences_file", "")
        self.declare_parameter("web_heartbeat_timeout_s", 1.0)
        self.declare_parameter("xbox_deadman_timeout_s", 0.5)
        self.declare_parameter("detection_timeout_s", 2.0)
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("servo_twist_topic", "/servo/twist_cmd")
        self.declare_parameter("gripper_command_topic", "/gripper/command")
        self.declare_parameter("gripper_trajectory_topic", "/gripper_controller/joint_trajectory")
        self.declare_parameter("gripper_action_name", "/gripper_controller/follow_joint_trajectory")
        self.declare_parameter("gripper_joint_names", ["gripper_joint_l", "gripper_joint_r"])
        self.declare_parameter("gripper_open_position_m", 0.025)
        self.declare_parameter("gripper_closed_position_m", 0.0)
        self.declare_parameter("arm_action_name", "/arm/move_joint")
        self.declare_parameter("move_group_action_name", "/move_action")
        self.declare_parameter("execute_trajectory_action_name", "/execute_trajectory")
        self.declare_parameter("cartesian_path_service_name", "/compute_cartesian_path")
        self.declare_parameter("planning_group", "irb14050_arm")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("ee_frame", "tool0")
        self.declare_parameter("planning_time", 5.0)
        self.declare_parameter("velocity_scale", 0.15)
        self.declare_parameter("cartesian_max_step", 0.005)
        self.declare_parameter("cartesian_min_fraction", 0.90)
        self.declare_parameter("action_server_timeout_s", 10.0)
        self.declare_parameter("simulation_motion_duration_s", 1.5)
        self.declare_parameter("gripper_motion_duration_s", 0.3)
        self.declare_parameter("workspace_min_x", 0.15)
        self.declare_parameter("workspace_max_x", 0.85)
        self.declare_parameter("workspace_min_y", -0.45)
        self.declare_parameter("workspace_max_y", 0.45)
        self.declare_parameter("workspace_min_z", 0.02)
        self.declare_parameter("workspace_max_z", 0.75)
        self.declare_parameter("pregrasp_offset_z", 0.10)
        self.declare_parameter("grasp_offset_z", 0.01)
        self.declare_parameter("retreat_offset_z", 0.12)
        self.declare_parameter("default_place_x", 0.35)
        self.declare_parameter("default_place_y", -0.30)
        self.declare_parameter("default_place_z", 0.20)
        self.declare_parameter("use_top_down_grasp_orientation", True)
        self.declare_parameter("top_down_qx", 1.0)
        self.declare_parameter("top_down_qy", 0.0)
        self.declare_parameter("top_down_qz", 0.0)
        self.declare_parameter("top_down_qw", 0.0)
        self.declare_parameter("tf_timeout_s", 1.0)

    def _load_parameters(self) -> None:
        self.tick_hz = float(self.get_parameter("tick_hz").value)
        self.use_introspection = bool(self.get_parameter("use_introspection").value)
        self.simulation_mode = bool(self.get_parameter("simulation_mode").value)
        self.motion_backend = str(self.get_parameter("motion_backend").value)
        self.robot_ready_default = bool(self.get_parameter("robot_ready_default").value)
        self.joint_count = int(self.get_parameter("joint_count").value)
        self.joint_names = list(self.get_parameter("joint_names").value)
        self.joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.joint_limits_file = str(self.get_parameter("joint_limits_file").value)
        self.sequences_file = str(self.get_parameter("sequences_file").value)
        self.web_heartbeat_timeout_s = float(self.get_parameter("web_heartbeat_timeout_s").value)
        self.xbox_deadman_timeout_s = float(self.get_parameter("xbox_deadman_timeout_s").value)
        self.detection_timeout_s = float(self.get_parameter("detection_timeout_s").value)
        self.confidence_threshold = float(self.get_parameter("confidence_threshold").value)
        self.servo_twist_topic = str(self.get_parameter("servo_twist_topic").value)
        self.gripper_command_topic = str(self.get_parameter("gripper_command_topic").value)
        self.gripper_trajectory_topic = str(self.get_parameter("gripper_trajectory_topic").value)
        self.gripper_action_name = str(self.get_parameter("gripper_action_name").value)
        self.gripper_joint_names = list(self.get_parameter("gripper_joint_names").value)
        self.gripper_open_position_m = float(self.get_parameter("gripper_open_position_m").value)
        self.gripper_closed_position_m = float(self.get_parameter("gripper_closed_position_m").value)
        self.arm_action_name = str(self.get_parameter("arm_action_name").value)
        self.move_group_action_name = str(self.get_parameter("move_group_action_name").value)
        self.execute_trajectory_action_name = str(self.get_parameter("execute_trajectory_action_name").value)
        self.cartesian_path_service_name = str(self.get_parameter("cartesian_path_service_name").value)
        self.planning_group = str(self.get_parameter("planning_group").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.ee_frame = str(self.get_parameter("ee_frame").value)
        self.planning_time = float(self.get_parameter("planning_time").value)
        self.velocity_scale = float(self.get_parameter("velocity_scale").value)
        self.cartesian_max_step = float(self.get_parameter("cartesian_max_step").value)
        self.cartesian_min_fraction = float(self.get_parameter("cartesian_min_fraction").value)
        self.action_server_timeout_s = float(self.get_parameter("action_server_timeout_s").value)
        self.simulation_motion_duration_s = float(self.get_parameter("simulation_motion_duration_s").value)
        self.gripper_motion_duration_s = float(self.get_parameter("gripper_motion_duration_s").value)
        self.workspace_min_x = float(self.get_parameter("workspace_min_x").value)
        self.workspace_max_x = float(self.get_parameter("workspace_max_x").value)
        self.workspace_min_y = float(self.get_parameter("workspace_min_y").value)
        self.workspace_max_y = float(self.get_parameter("workspace_max_y").value)
        self.workspace_min_z = float(self.get_parameter("workspace_min_z").value)
        self.workspace_max_z = float(self.get_parameter("workspace_max_z").value)
        self.pregrasp_offset_z = float(self.get_parameter("pregrasp_offset_z").value)
        self.grasp_offset_z = float(self.get_parameter("grasp_offset_z").value)
        self.retreat_offset_z = float(self.get_parameter("retreat_offset_z").value)
        self.default_place_x = float(self.get_parameter("default_place_x").value)
        self.default_place_y = float(self.get_parameter("default_place_y").value)
        self.default_place_z = float(self.get_parameter("default_place_z").value)
        self.use_top_down_grasp_orientation = bool(
            self.get_parameter("use_top_down_grasp_orientation").value
        )
        self.top_down_qx = float(self.get_parameter("top_down_qx").value)
        self.top_down_qy = float(self.get_parameter("top_down_qy").value)
        self.top_down_qz = float(self.get_parameter("top_down_qz").value)
        self.top_down_qw = float(self.get_parameter("top_down_qw").value)
        self.tf_timeout_s = float(self.get_parameter("tf_timeout_s").value)

        if self.tick_hz <= 0.0:
            self.get_logger().warn("tick_hz must be > 0; using 20 Hz")
            self.tick_hz = 20.0

        if not self.joint_limits_file:
            self.joint_limits_file = self._default_config_path("joint_limits.yaml")
        if not self.sequences_file:
            self.sequences_file = self._default_config_path("sequences.yaml")

    def _default_config_path(self, filename: str) -> str:
        try:
            share_dir = Path(get_package_share_directory("robot_task_manager"))
            return str(share_dir / "config" / filename)
        except PackageNotFoundError:
            return str(Path(__file__).resolve().parents[1] / "config" / filename)

    def _initialise_blackboard(self) -> None:
        self.blackboard.set(bb_keys.CURRENT_COMMAND, None)
        self.blackboard.set(bb_keys.CURRENT_MODE, "IDLE")
        self.blackboard.set(bb_keys.ROBOT_READY, bool(self.robot_ready_default or self.simulation_mode))
        self.blackboard.set(bb_keys.ESTOP_ACTIVE, False)
        self.blackboard.set(bb_keys.ARM_BUSY, False)
        self.blackboard.set(bb_keys.TELEOP_ACTIVE, False)
        self.blackboard.set(bb_keys.YOLO_DETECTIONS, [])
        self.blackboard.set(bb_keys.JOINT_STATE_DEG, [0.0] * int(self.joint_count))
        self.blackboard.set(bb_keys.STATUS_TEXT, "Idle")
        self.blackboard.set(bb_keys.ERROR_CODE, "")
        self.blackboard.set(bb_keys.TASK_PROGRESS, 0.0)
        self.blackboard.set(bb_keys.CURRENT_TASK, "")
        self.blackboard.set(bb_keys.XBOX_DEADMAN_PRESSED, False)
        self.blackboard.set(bb_keys.XBOX_DEADMAN_LAST_TIME, 0.0)

    def _initialise_tf(self) -> None:
        self.tf_buffer = None
        self.tf_listener = None
        try:
            from tf2_ros import Buffer, TransformListener
        except ImportError:
            self.get_logger().warn("tf2_ros unavailable; base-frame transforms disabled")
            return
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

    def _create_behaviour_tree(self, root):
        if not self.use_introspection:
            return py_trees.trees.BehaviourTree(root)

        try:
            import py_trees_ros.trees
        except ImportError as exc:
            self.get_logger().warn(
                "py_trees_ros is not importable; falling back to local py_trees "
                f"introspection only: {exc}"
            )
            return py_trees.trees.BehaviourTree(root)

        tree = py_trees_ros.trees.BehaviourTree(root)
        tree.setup(node=self, node_name="robot_task_tree", timeout=5.0)
        return tree

    def _configure_introspection(self) -> None:
        if not self.use_introspection:
            return

        if hasattr(self.tree, "snapshot_streams"):
            self._enable_default_snapshot_stream()
            self.get_logger().info(
                "py_trees_ros live introspection enabled on /robot_task_tree/snapshots"
            )
            return

        self._snapshot_visitor = py_trees.visitors.SnapshotVisitor()
        self.tree.add_visitor(self._snapshot_visitor)
        self.get_logger().warn("Using local py_trees snapshot visitor only")

    def _enable_default_snapshot_stream(self) -> None:
        snapshot_period = float(self.get_parameter("default_snapshot_period").value)
        blackboard_data = bool(self.get_parameter("default_snapshot_blackboard_data").value)
        blackboard_activity = bool(self.get_parameter("default_snapshot_blackboard_activity").value)
        self.set_parameters(
            [
                Parameter("default_snapshot_period", Parameter.Type.DOUBLE, snapshot_period),
                Parameter("default_snapshot_blackboard_data", Parameter.Type.BOOL, blackboard_data),
                Parameter("default_snapshot_blackboard_activity", Parameter.Type.BOOL, blackboard_activity),
                Parameter("default_snapshot_stream", Parameter.Type.BOOL, True),
            ]
        )

    def _command_callback(self, command: RobotCommand) -> None:
        now = self._now()
        if command.header.stamp.sec == 0 and command.header.stamp.nanosec == 0:
            command.header.stamp = self.get_clock().now().to_msg()
        if not command.header.frame_id:
            command.header.frame_id = "robot_task_command"

        valid, message = validate_command(command)
        if not valid:
            self.get_logger().warn(f"Rejected malformed command: {message}")
            self.blackboard.set(bb_keys.STATUS_TEXT, f"Rejected command: {message}")
            self.blackboard.set(bb_keys.ERROR_CODE, "INVALID_COMMAND")
            return

        if command.priority <= 0.0:
            command.priority = float(100 - command_rank(command.command_type))

        if command.command_type == "RESUME":
            self.blackboard.set(bb_keys.ESTOP_ACTIVE, False)
            self.blackboard.set(bb_keys.CURRENT_COMMAND, None)
            self.blackboard.set(bb_keys.CURRENT_MODE, "IDLE")
            self.blackboard.set(bb_keys.STATUS_TEXT, "Resumed")
            self.blackboard.set(bb_keys.ERROR_CODE, "")
            self.publish_zero_twist()
            self.get_logger().info("Resumed from ESTOP/paused state")
            return

        if command.command_type == "PAUSE":
            self.blackboard.set(bb_keys.CURRENT_COMMAND, None)
            self.blackboard.set(bb_keys.STATUS_TEXT, "Paused")
            self.publish_zero_twist()
            self.get_logger().info("Paused by command")
            return

        if self.blackboard.get(bb_keys.ESTOP_ACTIVE) and command.command_type not in {"ESTOP", "CANCEL"}:
            self.get_logger().warn("Ignoring command while ESTOP is active; send RESUME first")
            self.blackboard.set(bb_keys.STATUS_TEXT, "ESTOP active; command ignored")
            return

        if command.command_type == "WEB_TELEOP":
            self.blackboard.set(bb_keys.WEB_LAST_HEARTBEAT_TIME, now)

        current = self.blackboard.get(bb_keys.CURRENT_COMMAND)
        arm_busy = bool(self.blackboard.get(bb_keys.ARM_BUSY))
        accepted, reason = should_accept_command(command, current, arm_busy)
        if not accepted:
            self.get_logger().warn(f"Rejected command {command.command_type}: {reason}")
            self.blackboard.set(bb_keys.STATUS_TEXT, f"Rejected {command.command_type}: {reason}")
            return

        if command.command_type == "ESTOP":
            self.blackboard.set(bb_keys.ESTOP_ACTIVE, True)
            self.publish_zero_twist()

        self.blackboard.set(bb_keys.CURRENT_COMMAND, command)
        self.blackboard.set(bb_keys.CURRENT_MODE, mode_for_command(command))
        self.blackboard.set(bb_keys.CURRENT_TASK, describe_command(command))
        self.blackboard.set(bb_keys.ERROR_CODE, "")
        self.get_logger().info(f"Accepted command {command.command_type} from {command.source}: {reason}")

    def _detection_callback(self, detection: Detection3D) -> None:
        now = self._now()
        if now - self._last_detection_time > 0.30:
            self._detections = []
        self._last_detection_time = now
        self._detections.append(detection)
        self._detections = self._detections[-20:]
        self.blackboard.set(bb_keys.YOLO_DETECTIONS, list(self._detections))

    def _joint_state_callback(self, msg: JointState) -> None:
        positions_by_name = {
            name: position for name, position in zip(msg.name, msg.position)
        }
        if not positions_by_name:
            return
        try:
            values_rad = [positions_by_name[name] for name in self.joint_names]
        except KeyError:
            return
        values_deg = [float(value) * 180.0 / 3.141592653589793 for value in values_rad]
        self.blackboard.set(bb_keys.JOINT_STATE_DEG, values_deg)
        if not self.simulation_mode:
            self.blackboard.set(bb_keys.ROBOT_READY, True)

    def _web_heartbeat_callback(self, _msg: Header) -> None:
        self.blackboard.set(bb_keys.WEB_LAST_HEARTBEAT_TIME, self._now())

    def _xbox_deadman_callback(self, msg: Bool) -> None:
        self.blackboard.set(bb_keys.XBOX_DEADMAN_PRESSED, bool(msg.data))
        self.blackboard.set(bb_keys.XBOX_DEADMAN_LAST_TIME, self._now())
        if not msg.data:
            self.publish_zero_twist()

    def _tick_tree(self) -> None:
        try:
            self.tree.tick()
        except Exception as exc:  # noqa: BLE001 - keep robot state visible on behavior errors.
            self.get_logger().exception(f"Behavior tree tick failed: {exc}")
            self.blackboard.set(bb_keys.CURRENT_MODE, "ERROR")
            self.blackboard.set(bb_keys.STATUS_TEXT, str(exc))
            self.blackboard.set(bb_keys.ERROR_CODE, "TREE_EXCEPTION")
            self.publish_zero_twist()

        self._publish_status()
        self._maybe_log_tree()

    def _publish_status(self) -> None:
        status = RobotStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = "robot_task_tree"
        status.mode = str(self.blackboard.get(bb_keys.CURRENT_MODE))
        status.current_task = str(self.blackboard.get(bb_keys.CURRENT_TASK))
        status.message = str(self.blackboard.get(bb_keys.STATUS_TEXT))
        status.robot_ready = bool(self.blackboard.get(bb_keys.ROBOT_READY))
        status.arm_busy = bool(self.blackboard.get(bb_keys.ARM_BUSY))
        status.estop_active = bool(self.blackboard.get(bb_keys.ESTOP_ACTIVE))
        status.teleop_active = bool(self.blackboard.get(bb_keys.TELEOP_ACTIVE))
        status.progress = float(self.blackboard.get(bb_keys.TASK_PROGRESS))
        status.error_code = str(self.blackboard.get(bb_keys.ERROR_CODE))
        self.status_pub.publish(status)

    def _maybe_log_tree(self) -> None:
        if not self.use_introspection:
            return
        now = self._now()
        if now - self._last_tree_log_time < 5.0:
            return
        self._last_tree_log_time = now
        tree_text = py_trees.display.unicode_tree(root=self.tree.root, show_status=True)
        self.get_logger().debug("\n" + tree_text)

    def publish_zero_twist(self) -> None:
        if not rclpy.ok():
            return
        try:
            self.servo_pub.publish(Twist())
        except Exception as exc:  # noqa: BLE001 - publisher context can be invalid during shutdown.
            self.get_logger().debug(f"Skipping zero twist publish during shutdown: {exc}")

    def publish_gripper_command(self, command: str) -> None:
        normalized = command.strip().lower()
        if normalized not in {"open", "close"}:
            self.get_logger().warn(f"Ignoring unsupported gripper command: {command}")
            return

        text_command = String()
        text_command.data = normalized
        self.gripper_pub.publish(text_command)

        target = (
            self.gripper_open_position_m
            if normalized == "open"
            else self.gripper_closed_position_m
        )
        trajectory = JointTrajectory()
        trajectory.joint_names = list(self.gripper_joint_names)
        point = JointTrajectoryPoint()
        point.positions = [target] * len(trajectory.joint_names)
        point.time_from_start.sec = int(self.gripper_motion_duration_s)
        point.time_from_start.nanosec = int(
            max(0.0, self.gripper_motion_duration_s - int(self.gripper_motion_duration_s))
            * 1_000_000_000
        )
        trajectory.points = [point]
        self.gripper_trajectory_pub.publish(trajectory)
        if self.gripper_action_client.server_is_ready():
            goal = FollowJointTrajectory.Goal()
            goal.trajectory = trajectory
            self.gripper_action_client.send_goal_async(goal)
        else:
            self.get_logger().debug(
                f"Gripper action server not ready: {self.gripper_action_name}"
            )

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def destroy_node(self) -> bool:
        self.publish_zero_twist()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotTaskTreeNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
