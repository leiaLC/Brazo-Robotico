#!/usr/bin/env python3
"""ROS bridge for web teleoperation and sequence requests."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Header, String

from robot_task_msgs.msg import RobotCommand


class WebCommandBridge(Node):
    """Convert web-facing topics into common RobotCommand messages."""

    def __init__(self) -> None:
        super().__init__("web_command_bridge")
        self.declare_parameter("heartbeat_hz", 10.0)
        heartbeat_hz = max(1.0, float(self.get_parameter("heartbeat_hz").value))

        self.command_pub = self.create_publisher(RobotCommand, "/robot_task/command", 10)
        self.heartbeat_pub = self.create_publisher(Header, "/web/heartbeat", 10)
        self.teleop_sub = self.create_subscription(Twist, "/web/teleop_twist", self._teleop_callback, 10)
        self.sequence_sub = self.create_subscription(String, "/web/sequence_id", self._sequence_callback, 10)
        self.heartbeat_timer = self.create_timer(1.0 / heartbeat_hz, self._publish_heartbeat)
        self.get_logger().info("web_command_bridge ready")

    def _base_command(self) -> RobotCommand:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = "web_command_bridge"
        command.source = "web"
        return command

    def _teleop_callback(self, twist: Twist) -> None:
        command = self._base_command()
        command.command_type = "WEB_TELEOP"
        command.teleop_twist = twist
        command.priority = 97.0
        self.command_pub.publish(command)

    def _sequence_callback(self, msg: String) -> None:
        sequence_id = msg.data.strip()
        if not sequence_id:
            self.get_logger().warn("Ignoring empty /web/sequence_id")
            return
        command = self._base_command()
        command.command_type = "RUN_SEQUENCE"
        command.sequence_id = sequence_id
        command.priority = 95.0
        self.command_pub.publish(command)
        self.get_logger().info(f"Published web sequence command: {sequence_id}")

    def _publish_heartbeat(self) -> None:
        heartbeat = Header()
        heartbeat.stamp = self.get_clock().now().to_msg()
        heartbeat.frame_id = "web_command_bridge"
        self.heartbeat_pub.publish(heartbeat)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WebCommandBridge()
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
