#!/usr/bin/env python3
"""Xbox Joy bridge that publishes common robot teleop commands."""

import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

from robot_task_msgs.msg import RobotCommand


class XboxCommandBridge(Node):
    """Map Joy messages to XBOX_TELEOP RobotCommand messages."""

    def __init__(self) -> None:
        super().__init__("xbox_command_bridge")
        self._declare_parameters()
        self._load_parameters()

        self.command_pub = self.create_publisher(RobotCommand, "/robot_task/command", 10)
        self.deadman_pub = self.create_publisher(Bool, "/xbox/deadman", 10)
        self.joy_sub = self.create_subscription(Joy, "/joy", self._joy_callback, 10)
        self._last_deadman = False
        self.get_logger().info(
            f"xbox_command_bridge ready (deadman_button={self.deadman_button})"
        )

    def _declare_parameters(self) -> None:
        self.declare_parameter("deadman_button", 4)
        self.declare_parameter("axis_linear_x", 1)
        self.declare_parameter("axis_linear_y", 0)
        self.declare_parameter("axis_linear_z", 4)
        self.declare_parameter("axis_angular_z", 3)
        self.declare_parameter("scale_linear_x", 0.20)
        self.declare_parameter("scale_linear_y", 0.20)
        self.declare_parameter("scale_linear_z", 0.12)
        self.declare_parameter("scale_angular_z", 0.60)
        self.declare_parameter("deadzone", 0.08)
        self.declare_parameter("publish_zero_on_release", True)

    def _load_parameters(self) -> None:
        self.deadman_button = int(self.get_parameter("deadman_button").value)
        self.axis_linear_x = int(self.get_parameter("axis_linear_x").value)
        self.axis_linear_y = int(self.get_parameter("axis_linear_y").value)
        self.axis_linear_z = int(self.get_parameter("axis_linear_z").value)
        self.axis_angular_z = int(self.get_parameter("axis_angular_z").value)
        self.scale_linear_x = float(self.get_parameter("scale_linear_x").value)
        self.scale_linear_y = float(self.get_parameter("scale_linear_y").value)
        self.scale_linear_z = float(self.get_parameter("scale_linear_z").value)
        self.scale_angular_z = float(self.get_parameter("scale_angular_z").value)
        self.deadzone = float(self.get_parameter("deadzone").value)
        self.publish_zero_on_release = bool(self.get_parameter("publish_zero_on_release").value)

    def _joy_callback(self, joy: Joy) -> None:
        deadman_pressed = self._button(joy, self.deadman_button) > 0
        deadman_msg = Bool()
        deadman_msg.data = deadman_pressed
        self.deadman_pub.publish(deadman_msg)

        if not deadman_pressed:
            if self._last_deadman and self.publish_zero_on_release:
                self._publish_command(Twist())
            self._last_deadman = False
            return

        self._last_deadman = True
        twist = Twist()
        twist.linear.x = self._axis(joy, self.axis_linear_x) * self.scale_linear_x
        twist.linear.y = self._axis(joy, self.axis_linear_y) * self.scale_linear_y
        twist.linear.z = self._axis(joy, self.axis_linear_z) * self.scale_linear_z
        twist.angular.z = self._axis(joy, self.axis_angular_z) * self.scale_angular_z
        self._publish_command(twist)

    def _publish_command(self, twist: Twist) -> None:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = "xbox_command_bridge"
        command.source = "xbox"
        command.command_type = "XBOX_TELEOP"
        command.teleop_twist = twist
        command.priority = 98.0
        self.command_pub.publish(command)

    def _axis(self, joy: Joy, index: int) -> float:
        if index < 0 or index >= len(joy.axes):
            return 0.0
        value = float(joy.axes[index])
        if math.fabs(value) < self.deadzone:
            return 0.0
        return value

    @staticmethod
    def _button(joy: Joy, index: int) -> int:
        if index < 0 or index >= len(joy.buttons):
            return 0
        return int(joy.buttons[index])


def main(args=None) -> None:
    rclpy.init(args=args)
    node = XboxCommandBridge()
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
