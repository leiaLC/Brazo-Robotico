"""Launch the Xbox command bridge."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("robot_xbox_teleop"))
    params = share / "config" / "xbox.yaml"
    return LaunchDescription(
        [
            Node(
                package="robot_xbox_teleop",
                executable="xbox_command_bridge",
                name="xbox_command_bridge",
                output="screen",
                parameters=[str(params)],
            )
        ]
    )
