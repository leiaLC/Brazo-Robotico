"""Launch the voice command parser."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="robot_voice_interface",
                executable="voice_command_parser",
                name="voice_command_parser",
                output="screen",
            )
        ]
    )
