#!/usr/bin/env python3
"""MoveJoint action server backed directly by the ABB EGM bridge."""

from __future__ import annotations

import math
import time
from threading import Lock

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

from robot_task_msgs.action import MoveJoint


DEFAULT_JOINT_NAMES = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
    "joint_7",
]


class EgmMoveJointActionServer(Node):
    """Execute MoveJoint goals by publishing one target to /joint_command."""

    def __init__(self) -> None:
        super().__init__("egm_move_joint_action_server")
        self.declare_parameter("action_name", "/arm/move_joint")
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("joint_command_topic", "/joint_command")
        self.declare_parameter("joint_names", DEFAULT_JOINT_NAMES)
        self.declare_parameter("goal_tolerance_deg", 3.0)
        self.declare_parameter("settle_timeout_s", 15.0)
        self.declare_parameter("feedback_rate_hz", 10.0)

        self.action_name = str(self.get_parameter("action_name").value)
        self.joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.joint_command_topic = str(self.get_parameter("joint_command_topic").value)
        self.joint_names = list(self.get_parameter("joint_names").value)
        self.goal_tolerance_rad = math.radians(
            float(self.get_parameter("goal_tolerance_deg").value)
        )
        self.settle_timeout_s = float(self.get_parameter("settle_timeout_s").value)
        self.feedback_rate_hz = float(self.get_parameter("feedback_rate_hz").value)

        self._lock = Lock()
        self._current_positions: list[float] | None = None
        cb_group = ReentrantCallbackGroup()

        self.create_subscription(
            JointState,
            self.joint_states_topic,
            self._joint_state_callback,
            10,
            callback_group=cb_group,
        )
        self.command_pub = self.create_publisher(
            JointState,
            self.joint_command_topic,
            10,
        )
        self.action_server = ActionServer(
            self,
            MoveJoint,
            self.action_name,
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=cb_group,
        )
        self.get_logger().info(
            f"egm_move_joint_action_server ready on {self.action_name}"
        )

    def _joint_state_callback(self, msg: JointState) -> None:
        if not msg.name:
            positions = list(msg.position[: len(self.joint_names)])
        else:
            index = {name: idx for idx, name in enumerate(msg.name)}
            if any(name not in index for name in self.joint_names):
                return
            positions = [msg.position[index[name]] for name in self.joint_names]
        if len(positions) != len(self.joint_names):
            return
        with self._lock:
            self._current_positions = list(positions)

    def _goal_callback(self, goal_request) -> GoalResponse:
        if len(goal_request.joint_values) != len(self.joint_names):
            self.get_logger().warn(
                f"Rejecting MoveJoint goal: expected {len(self.joint_names)} values, "
                f"got {len(goal_request.joint_values)}"
            )
            return GoalResponse.REJECT
        if self._read_current() is None:
            self.get_logger().warn("Rejecting MoveJoint goal: no /joint_states yet")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _cancel_callback(self, _goal_handle) -> CancelResponse:
        self.get_logger().warn("MoveJoint cancel requested")
        return CancelResponse.ACCEPT

    def _execute_callback(self, goal_handle):
        target_rad = [math.radians(float(value)) for value in goal_handle.request.joint_values]
        self._publish_target(target_rad)

        start = time.monotonic()
        deadline = start + self.settle_timeout_s
        initial_error = self._max_error(target_rad) or 1.0
        feedback_period = 1.0 / max(1.0, self.feedback_rate_hz)

        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested:
                current = self._read_current()
                if current is not None:
                    self._publish_target(current)
                goal_handle.canceled()
                return self._result(False, "EGM MoveJoint cancelled")

            error = self._max_error(target_rad)
            if error is not None:
                progress = 1.0 - min(1.0, error / max(initial_error, 1e-6))
                feedback = MoveJoint.Feedback()
                feedback.progress = float(max(0.0, min(progress, 1.0)))
                feedback.current_state = f"EGM joint error {math.degrees(error):.2f} deg"
                goal_handle.publish_feedback(feedback)

                if error <= self.goal_tolerance_rad:
                    goal_handle.succeed()
                    return self._result(True, "EGM MoveJoint complete")

            time.sleep(feedback_period)

        goal_handle.abort()
        return self._result(False, "EGM MoveJoint settle timeout")

    def _publish_target(self, target_rad: list[float]) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self.joint_names)
        msg.position = list(target_rad)
        self.command_pub.publish(msg)
        self.get_logger().info(
            "Published EGM MoveJoint target (deg): "
            + "[" + ", ".join(f"{math.degrees(v):+.2f}" for v in target_rad) + "]"
        )

    def _read_current(self) -> list[float] | None:
        with self._lock:
            return None if self._current_positions is None else list(self._current_positions)

    def _max_error(self, target_rad: list[float]) -> float | None:
        current = self._read_current()
        if current is None:
            return None
        return max(abs(c - t) for c, t in zip(current, target_rad))

    @staticmethod
    def _result(success: bool, message: str) -> MoveJoint.Result:
        result = MoveJoint.Result()
        result.success = success
        result.message = message
        return result


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EgmMoveJointActionServer()
    executor = MultiThreadedExecutor(num_threads=2)
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
