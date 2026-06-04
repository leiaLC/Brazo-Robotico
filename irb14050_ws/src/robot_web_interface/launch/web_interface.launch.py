"""Launch the web command bridge."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="robot_web_interface",
                executable="web_command_bridge",
                name="web_command_bridge",
                output="screen",
            ),
            Node(
                package="robot_web_interface",
                executable="jetson_metrics_publisher",
                name="jetson_metrics_publisher",
                output="screen",
            )
        ]
    )
