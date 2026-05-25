#!/usr/bin/env python3
"""Mock servo twist adapter."""

import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class MockServoNode(Node):
    """Log servo twist commands and timeout to a safe stopped state."""

    def __init__(self) -> None:
        super().__init__("mock_servo_node")
        self.declare_parameter("simulation_mode", True)
        self.declare_parameter("twist_topic", "/servo/twist_cmd")
        self.declare_parameter("command_timeout_s", 0.4)
        self.simulation_mode = bool(self.get_parameter("simulation_mode").value)
        self.twist_topic = str(self.get_parameter("twist_topic").value)
        self.command_timeout_s = float(self.get_parameter("command_timeout_s").value)

        self.sub = self.create_subscription(Twist, self.twist_topic, self._twist_callback, 10)
        self.timer = self.create_timer(0.1, self._timeout_check)
        self._last_command_time = self._now()
        self._last_log_time = 0.0
        self._timed_out = False
        self.get_logger().info(
            f"mock_servo_node listening on {self.twist_topic} "
            f"(simulation_mode={self.simulation_mode})"
        )

    def _twist_callback(self, twist: Twist) -> None:
        self._last_command_time = self._now()
        self._timed_out = False
        if self._nonzero(twist) and self._now() - self._last_log_time > 1.0:
            self._last_log_time = self._now()
            self.get_logger().info(
                "Mock servo twist "
                f"lin=({twist.linear.x:.3f}, {twist.linear.y:.3f}, {twist.linear.z:.3f}) "
                f"ang_z={twist.angular.z:.3f}"
            )

    def _timeout_check(self) -> None:
        age = self._now() - self._last_command_time
        if age > self.command_timeout_s and not self._timed_out:
            self._timed_out = True
            self.get_logger().debug("Servo command timeout; mock servo stopped")

    @staticmethod
    def _nonzero(twist: Twist) -> bool:
        values = [
            twist.linear.x,
            twist.linear.y,
            twist.linear.z,
            twist.angular.x,
            twist.angular.y,
            twist.angular.z,
        ]
        return any(math.fabs(value) > 1e-6 for value in values)

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockServoNode()
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
