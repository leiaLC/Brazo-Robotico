#!/usr/bin/env python3
"""Generic Joy/gamepad bridge that publishes safe robot task commands."""

from __future__ import annotations

import math
from typing import Iterable

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool, String

from robot_task_msgs.msg import RobotCommand


class GamepadCommandBridge(Node):
    """Map sensor_msgs/Joy messages to the robot task manager command API."""

    AXES = (
        "linear_x",
        "linear_y",
        "linear_z",
        "angular_x",
        "angular_y",
        "angular_z",
    )

    def __init__(self) -> None:
        super().__init__("gamepad_command_bridge")
        self._declare_parameters()
        self._load_parameters()

        self.command_pub = self.create_publisher(RobotCommand, self.command_topic, 10)
        self.deadman_pub = self.create_publisher(Bool, self.deadman_topic, 10)
        self.gripper_pub = self.create_publisher(String, self.gripper_command_topic, 10)
        self.joy_sub = self.create_subscription(Joy, self.joy_topic, self._joy_callback, 10)

        self._latest_twist = Twist()
        self._last_joy_time: float | None = None
        self._last_buttons: list[int] = []
        self._deadman_pressed = False
        self._zero_sent_after_release = True
        self._joy_shape_logged = False

        timer_period = 1.0 / max(self.publish_rate_hz, 1.0)
        self.timer = self.create_timer(timer_period, self._timer_callback)

        if self.log_mapping_on_start:
            self.get_logger().info(
                "gamepad_command_bridge ready: "
                f"joy_topic={self.joy_topic}, command_topic={self.command_topic}, "
                f"deadman_topic={self.deadman_topic}, deadman_button={self.deadman_button}, "
                f"secondary_deadman_button={self.secondary_deadman_button}, "
                f"mode={self.deadman_mode}"
            )

    def _declare_parameters(self) -> None:
        self.declare_parameter("joy_topic", "/joy")
        self.declare_parameter("command_topic", "/robot_task/command")
        self.declare_parameter("deadman_topic", "/xbox/deadman")
        self.declare_parameter("gripper_command_topic", "/gripper/command")
        self.declare_parameter("source", "gamepad")
        self.declare_parameter("frame_id", "gamepad_command_bridge")
        self.declare_parameter("teleop_command_type", "XBOX_TELEOP")
        self.declare_parameter("priority", 98.0)

        self.declare_parameter("deadman_button", 4)
        self.declare_parameter("secondary_deadman_button", -1)
        self.declare_parameter("deadman_mode", "any")
        self.declare_parameter("require_deadman", True)
        self.declare_parameter("estop_button", -1)
        self.declare_parameter("resume_button", -1)
        self.declare_parameter("cancel_button", -1)
        self.declare_parameter("open_gripper_button", -1)
        self.declare_parameter("close_gripper_button", -1)
        self.declare_parameter("require_deadman_for_gripper", True)

        self.declare_parameter("axis_linear_x", 1)
        self.declare_parameter("axis_linear_y", 0)
        self.declare_parameter("axis_linear_z", 4)
        self.declare_parameter("axis_angular_x", -1)
        self.declare_parameter("axis_angular_y", -1)
        self.declare_parameter("axis_angular_z", 3)
        self.declare_parameter("scale_linear_x", 0.20)
        self.declare_parameter("scale_linear_y", 0.20)
        self.declare_parameter("scale_linear_z", 0.12)
        self.declare_parameter("scale_angular_x", 0.0)
        self.declare_parameter("scale_angular_y", 0.0)
        self.declare_parameter("scale_angular_z", 0.60)

        self.declare_parameter("deadzone", 0.08)
        self.declare_parameter("rescale_after_deadzone", True)
        self.declare_parameter("normalize_linear_xy", True)
        self.declare_parameter("publish_rate_hz", 25.0)
        self.declare_parameter("joy_timeout_s", 0.6)
        self.declare_parameter("publish_zero_on_release", True)
        self.declare_parameter("log_mapping_on_start", True)
        self.declare_parameter("log_joy_shape_once", True)
        self.declare_parameter("log_button_edges", False)

    def _load_parameters(self) -> None:
        self.joy_topic = str(self.get_parameter("joy_topic").value)
        self.command_topic = str(self.get_parameter("command_topic").value)
        self.deadman_topic = str(self.get_parameter("deadman_topic").value)
        self.gripper_command_topic = str(self.get_parameter("gripper_command_topic").value)
        self.source = str(self.get_parameter("source").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.teleop_command_type = str(self.get_parameter("teleop_command_type").value)
        self.priority = float(self.get_parameter("priority").value)

        self.deadman_button = int(self.get_parameter("deadman_button").value)
        self.secondary_deadman_button = int(
            self.get_parameter("secondary_deadman_button").value
        )
        self.deadman_mode = str(self.get_parameter("deadman_mode").value).lower()
        if self.deadman_mode not in {"any", "all"}:
            self.get_logger().warn(
                f"Unsupported deadman_mode '{self.deadman_mode}', using 'any'"
            )
            self.deadman_mode = "any"
        self.require_deadman = bool(self.get_parameter("require_deadman").value)
        self.estop_button = int(self.get_parameter("estop_button").value)
        self.resume_button = int(self.get_parameter("resume_button").value)
        self.cancel_button = int(self.get_parameter("cancel_button").value)
        self.open_gripper_button = int(self.get_parameter("open_gripper_button").value)
        self.close_gripper_button = int(self.get_parameter("close_gripper_button").value)
        self.require_deadman_for_gripper = bool(
            self.get_parameter("require_deadman_for_gripper").value
        )

        self.axis_index = {
            name: int(self.get_parameter(f"axis_{name}").value)
            for name in self.AXES
        }
        self.axis_scale = {
            name: float(self.get_parameter(f"scale_{name}").value)
            for name in self.AXES
        }

        self.deadzone = max(0.0, min(float(self.get_parameter("deadzone").value), 0.99))
        self.rescale_after_deadzone = bool(
            self.get_parameter("rescale_after_deadzone").value
        )
        self.normalize_linear_xy = bool(self.get_parameter("normalize_linear_xy").value)
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.joy_timeout_s = float(self.get_parameter("joy_timeout_s").value)
        self.publish_zero_on_release = bool(
            self.get_parameter("publish_zero_on_release").value
        )
        self.log_mapping_on_start = bool(self.get_parameter("log_mapping_on_start").value)
        self.log_joy_shape_once = bool(self.get_parameter("log_joy_shape_once").value)
        self.log_button_edges = bool(self.get_parameter("log_button_edges").value)

    def _joy_callback(self, joy: Joy) -> None:
        now = self._now_seconds()
        self._last_joy_time = now

        if self.log_joy_shape_once and not self._joy_shape_logged:
            self._joy_shape_logged = True
            self.get_logger().info(
                f"Detected Joy message shape: axes={len(joy.axes)}, buttons={len(joy.buttons)}"
            )

        self._handle_button_edges(joy)
        self._deadman_pressed = self._compute_deadman(joy)
        self._latest_twist = self._twist_from_joy(joy)
        self._publish_current_state(fresh=True)

    def _timer_callback(self) -> None:
        fresh = self._last_joy_time is not None and (
            self._now_seconds() - self._last_joy_time
        ) <= self.joy_timeout_s
        self._publish_current_state(fresh=fresh)

    def _publish_current_state(self, fresh: bool) -> None:
        active = fresh and (self._deadman_pressed or not self.require_deadman)

        self._publish_deadman(active)
        if active:
            self._publish_command(self.teleop_command_type, self._latest_twist)
            self._zero_sent_after_release = False
            return

        if self.publish_zero_on_release and not self._zero_sent_after_release:
            self._publish_command(self.teleop_command_type, Twist())
            self._zero_sent_after_release = True

    def _handle_button_edges(self, joy: Joy) -> None:
        previous = self._last_buttons
        current = [int(value) for value in joy.buttons]

        for index, value in enumerate(current):
            was_pressed = index < len(previous) and previous[index] > 0
            is_pressed = value > 0
            if not is_pressed or was_pressed:
                continue
            if self.log_button_edges:
                self.get_logger().info(f"Button {index} pressed")
            self._handle_button_press(index, joy)

        self._last_buttons = current

    def _handle_button_press(self, index: int, joy: Joy) -> None:
        if index == self.estop_button:
            self._publish_command("ESTOP")
            return
        if index == self.resume_button:
            self._publish_command("RESUME")
            return
        if index == self.cancel_button:
            self._publish_command("CANCEL")
            return

        gripper_allowed = (
            not self.require_deadman_for_gripper
            or self._compute_deadman(joy)
            or not self.require_deadman
        )
        if index == self.open_gripper_button and gripper_allowed:
            self._publish_gripper("open")
        elif index == self.close_gripper_button and gripper_allowed:
            self._publish_gripper("close")

    def _compute_deadman(self, joy: Joy) -> bool:
        if not self.require_deadman:
            return True

        states = [
            self._button(joy, index) > 0
            for index in (self.deadman_button, self.secondary_deadman_button)
            if index >= 0
        ]
        if not states:
            return False
        if self.deadman_mode == "all":
            return all(states)
        return any(states)

    def _twist_from_joy(self, joy: Joy) -> Twist:
        values = {
            name: self._axis(joy, self.axis_index[name]) * self.axis_scale[name]
            for name in self.AXES
        }
        if self.normalize_linear_xy:
            values["linear_x"], values["linear_y"] = self._normalize_pair(
                values["linear_x"],
                values["linear_y"],
                self.axis_scale["linear_x"],
                self.axis_scale["linear_y"],
            )

        twist = Twist()
        twist.linear.x = values["linear_x"]
        twist.linear.y = values["linear_y"]
        twist.linear.z = values["linear_z"]
        twist.angular.x = values["angular_x"]
        twist.angular.y = values["angular_y"]
        twist.angular.z = values["angular_z"]
        return twist

    def _publish_command(self, command_type: str, twist: Twist | None = None) -> None:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = self.frame_id
        command.source = self.source
        command.command_type = command_type
        command.priority = self.priority if command_type == self.teleop_command_type else 1.0
        if twist is not None:
            command.teleop_twist = twist
        self.command_pub.publish(command)

    def _publish_deadman(self, pressed: bool) -> None:
        msg = Bool()
        msg.data = pressed
        self.deadman_pub.publish(msg)

    def _publish_gripper(self, command: str) -> None:
        msg = String()
        msg.data = command
        self.gripper_pub.publish(msg)
        self.get_logger().info(f"Published gripper command: {command}")

    def _axis(self, joy: Joy, index: int) -> float:
        if index < 0 or index >= len(joy.axes):
            return 0.0
        value = float(joy.axes[index])
        if math.fabs(value) < self.deadzone:
            return 0.0
        if self.rescale_after_deadzone:
            sign = 1.0 if value >= 0.0 else -1.0
            value = sign * (math.fabs(value) - self.deadzone) / (1.0 - self.deadzone)
        return max(-1.0, min(value, 1.0))

    @staticmethod
    def _button(joy: Joy, index: int) -> int:
        if index < 0 or index >= len(joy.buttons):
            return 0
        return int(joy.buttons[index])

    @staticmethod
    def _normalize_pair(x: float, y: float, x_scale: float, y_scale: float) -> tuple[float, float]:
        x_limit = abs(x_scale) if abs(x_scale) > 1e-9 else 1.0
        y_limit = abs(y_scale) if abs(y_scale) > 1e-9 else 1.0
        nx = x / x_limit
        ny = y / y_limit
        magnitude = math.hypot(nx, ny)
        if magnitude <= 1.0:
            return x, y
        return (nx / magnitude) * x_limit, (ny / magnitude) * y_limit

    def _now_seconds(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9


def main(args: Iterable[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GamepadCommandBridge()
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
