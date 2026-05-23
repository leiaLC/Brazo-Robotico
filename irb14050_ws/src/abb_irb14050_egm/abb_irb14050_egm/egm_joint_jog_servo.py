#!/usr/bin/env python3
"""Lightweight Twist-to-joint-jog adapter for the ABB EGM bridge."""

from __future__ import annotations

import math
from threading import Lock

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import JointState


DEFAULT_JOINT_NAMES = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
    "joint_7",
]

DEFAULT_MIN_DEG = [-168.5, -143.5, -168.5, -123.5, -290.0, -88.0, -229.0]
DEFAULT_MAX_DEG = [168.5, 43.5, 168.5, 80.0, 290.0, 138.0, 229.0]


class EgmJointJogServo(Node):
    """Integrate normalized Twist channels into EGM joint targets."""

    def __init__(self) -> None:
        super().__init__("egm_joint_jog_servo")
        self._declare_parameters()
        self._load_parameters()

        self._lock = Lock()
        self._current_positions: list[float] | None = None
        self._latest_twist = Twist()
        self._last_twist_time: float | None = None
        self._last_tick_time = self._now()

        self.command_pub = self.create_publisher(
            JointState,
            self.joint_command_topic,
            10,
        )
        self.create_subscription(
            JointState,
            self.joint_states_topic,
            self._joint_state_callback,
            10,
        )
        self.create_subscription(
            Twist,
            self.twist_topic,
            self._twist_callback,
            10,
        )
        self.timer = self.create_timer(
            1.0 / max(1.0, self.publish_rate_hz),
            self._timer_callback,
        )
        self.get_logger().info(
            "egm_joint_jog_servo ready: "
            f"{self.twist_topic} -> {self.joint_command_topic}, "
            f"rate={self.publish_rate_hz:.1f} Hz"
        )

    def _declare_parameters(self) -> None:
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("joint_command_topic", "/joint_command")
        self.declare_parameter("twist_topic", "/servo/twist_cmd")
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("command_timeout_s", 0.25)
        self.declare_parameter("input_deadzone", 0.02)
        self.declare_parameter("max_step_deg", 0.5)
        self.declare_parameter("joint_names", DEFAULT_JOINT_NAMES)
        self.declare_parameter(
            "joint_twist_fields",
            [
                "linear.y",
                "linear.x",
                "linear.z",
                "angular.z",
                "angular.x",
                "angular.y",
                "",
            ],
        )
        self.declare_parameter(
            "joint_velocity_scale_deg_s",
            [4.0, 4.0, 3.0, 4.0, 3.0, 3.0, 0.0],
        )
        self.declare_parameter("joint_min_deg", DEFAULT_MIN_DEG)
        self.declare_parameter("joint_max_deg", DEFAULT_MAX_DEG)

    def _load_parameters(self) -> None:
        self.joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.joint_command_topic = str(self.get_parameter("joint_command_topic").value)
        self.twist_topic = str(self.get_parameter("twist_topic").value)
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.command_timeout_s = float(self.get_parameter("command_timeout_s").value)
        self.input_deadzone = float(self.get_parameter("input_deadzone").value)
        self.max_step_rad = math.radians(float(self.get_parameter("max_step_deg").value))
        self.joint_names = list(self.get_parameter("joint_names").value)
        self.joint_twist_fields = list(self.get_parameter("joint_twist_fields").value)
        velocity_deg_s = list(self.get_parameter("joint_velocity_scale_deg_s").value)
        self.joint_velocity_scale = [math.radians(float(v)) for v in velocity_deg_s]
        self.joint_min = [
            math.radians(float(v)) for v in list(self.get_parameter("joint_min_deg").value)
        ]
        self.joint_max = [
            math.radians(float(v)) for v in list(self.get_parameter("joint_max_deg").value)
        ]
        self._validate_vector_lengths()

    def _validate_vector_lengths(self) -> None:
        expected = len(self.joint_names)
        for name, values in (
            ("joint_twist_fields", self.joint_twist_fields),
            ("joint_velocity_scale_deg_s", self.joint_velocity_scale),
            ("joint_min_deg", self.joint_min),
            ("joint_max_deg", self.joint_max),
        ):
            if len(values) != expected:
                raise ValueError(f"{name} must contain {expected} values")

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

    def _twist_callback(self, msg: Twist) -> None:
        with self._lock:
            self._latest_twist = msg
            self._last_twist_time = self._now()

    def _timer_callback(self) -> None:
        now = self._now()
        dt = max(0.0, min(now - self._last_tick_time, 0.1))
        self._last_tick_time = now

        with self._lock:
            current = None if self._current_positions is None else list(self._current_positions)
            twist = self._latest_twist
            last_twist_time = self._last_twist_time

        if current is None or last_twist_time is None:
            return
        if now - last_twist_time > self.command_timeout_s:
            return

        velocities = self._joint_velocities(twist)
        if not any(abs(value) > 1e-9 for value in velocities):
            return

        target = []
        for index, (position, velocity) in enumerate(zip(current, velocities)):
            step = max(-self.max_step_rad, min(velocity * dt, self.max_step_rad))
            unclamped = position + step
            target.append(max(self.joint_min[index], min(unclamped, self.joint_max[index])))

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self.joint_names)
        msg.position = target
        self.command_pub.publish(msg)

    def _joint_velocities(self, twist: Twist) -> list[float]:
        velocities = []
        for field, scale in zip(self.joint_twist_fields, self.joint_velocity_scale):
            value = self._twist_value(twist, str(field))
            if abs(value) < self.input_deadzone:
                value = 0.0
            velocities.append(value * scale)
        return velocities

    @staticmethod
    def _twist_value(twist: Twist, field: str) -> float:
        if field == "linear.x":
            return float(twist.linear.x)
        if field == "linear.y":
            return float(twist.linear.y)
        if field == "linear.z":
            return float(twist.linear.z)
        if field == "angular.x":
            return float(twist.angular.x)
        if field == "angular.y":
            return float(twist.angular.y)
        if field == "angular.z":
            return float(twist.angular.z)
        return 0.0

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EgmJointJogServo()
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
