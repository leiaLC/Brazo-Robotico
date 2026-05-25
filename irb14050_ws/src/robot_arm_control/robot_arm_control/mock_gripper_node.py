#!/usr/bin/env python3
"""Mock gripper adapter."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MockGripperNode(Node):
    """Log gripper open/close commands."""

    def __init__(self) -> None:
        super().__init__("mock_gripper_node")
        self.declare_parameter("simulation_mode", True)
        self.declare_parameter("command_topic", "/gripper/command")
        self.simulation_mode = bool(self.get_parameter("simulation_mode").value)
        self.command_topic = str(self.get_parameter("command_topic").value)
        self.sub = self.create_subscription(String, self.command_topic, self._command_callback, 10)
        self.get_logger().info(
            f"mock_gripper_node listening on {self.command_topic} "
            f"(simulation_mode={self.simulation_mode})"
        )

    def _command_callback(self, msg: String) -> None:
        command = msg.data.strip().lower()
        if command not in {"open", "close"}:
            self.get_logger().warn(f"Ignoring unsupported gripper command: {msg.data}")
            return
        self.get_logger().info(f"Mock gripper would {command}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockGripperNode()
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
