#!/usr/bin/env python3
"""Publish estimated gripper joint states for MoveIt current-state tracking."""

from __future__ import annotations

import re

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String


class GripperJointStatePublisher(Node):
    """Bridge gripper commands/state into gripper_joint_l/r JointState entries."""

    def __init__(self):
        super().__init__("gripper_joint_state_publisher")

        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("gripper_command_topic", "/gripper/command")
        self.declare_parameter("gripper_state_topic", "/gripper/state")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("open_position_m", 0.025)
        self.declare_parameter("closed_position_m", 0.0)
        self.declare_parameter("default_position_m", 0.0)
        self.declare_parameter("motion_duration_s", 0.8)
        self.declare_parameter("use_rws_position", False)
        self.declare_parameter("rws_position_scale", 0.000001)

        self.joint_states_topic = self.get_parameter("joint_states_topic").value
        self.open_position = float(self.get_parameter("open_position_m").value)
        self.closed_position = float(self.get_parameter("closed_position_m").value)
        self.current_position = float(self.get_parameter("default_position_m").value)
        self.start_position = self.current_position
        self.target_position = self.current_position
        self.motion_duration = max(0.01, float(self.get_parameter("motion_duration_s").value))
        self.use_rws_position = bool(self.get_parameter("use_rws_position").value)
        self.rws_position_scale = float(self.get_parameter("rws_position_scale").value)
        self.motion_start_time = self._now()

        self.pub = self.create_publisher(JointState, self.joint_states_topic, 10)
        self.create_subscription(
            String,
            self.get_parameter("gripper_command_topic").value,
            self._command_callback,
            10,
        )
        self.create_subscription(
            String,
            self.get_parameter("gripper_state_topic").value,
            self._state_callback,
            10,
        )
        rate = max(1.0, float(self.get_parameter("publish_rate_hz").value))
        self.timer = self.create_timer(1.0 / rate, self._publish)

        self.get_logger().info(
            "Publishing estimated gripper JointState entries on "
            f"{self.joint_states_topic}: closed={self.closed_position:.4f} m, "
            f"open={self.open_position:.4f} m"
        )

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _command_callback(self, msg: String) -> None:
        command = msg.data.strip().lower()
        if command == "open":
            self._set_target(self.open_position)
        elif command == "close":
            self._set_target(self.closed_position)
        elif command == "standby":
            return
        else:
            self.get_logger().debug(f"Ignoring unknown gripper command for joint state: {msg.data}")

    def _state_callback(self, msg: String) -> None:
        if not self.use_rws_position:
            return
        match = re.search(r"position=([-+]?\d+(?:\.\d+)?)", msg.data)
        if not match:
            return
        raw_position = float(match.group(1))
        position = raw_position * self.rws_position_scale
        position = max(self.closed_position, min(self.open_position, position))
        self.current_position = position
        self.start_position = position
        self.target_position = position
        self.motion_start_time = self._now()

    def _set_target(self, position: float) -> None:
        self._update_current_position()
        self.start_position = self.current_position
        self.target_position = float(position)
        self.motion_start_time = self._now()

    def _update_current_position(self) -> None:
        elapsed = self._now() - self.motion_start_time
        fraction = min(1.0, max(0.0, elapsed / self.motion_duration))
        self.current_position = self.start_position + (
            self.target_position - self.start_position
        ) * fraction

    def _publish(self) -> None:
        self._update_current_position()
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ["gripper_joint_l", "gripper_joint_r"]
        msg.position = [self.current_position, self.current_position]
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GripperJointStatePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
