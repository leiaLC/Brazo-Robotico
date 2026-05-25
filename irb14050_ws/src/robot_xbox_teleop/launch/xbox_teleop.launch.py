"""Launch the backward-compatible Xbox/gamepad command bridge."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("robot_xbox_teleop"))
    params = share / "config" / "xbox.yaml"
    launch_joy = LaunchConfiguration("launch_joy")
    joy_dev = LaunchConfiguration("joy_dev")
    joy_deadzone = LaunchConfiguration("joy_deadzone")
    joy_autorepeat_rate = LaunchConfiguration("joy_autorepeat_rate")
    config_file = LaunchConfiguration("config_file")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "launch_joy",
                default_value="true",
                description="Launch joy/joy_node to publish sensor_msgs/Joy on /joy.",
            ),
            DeclareLaunchArgument(
                "joy_dev",
                default_value="/dev/input/js0",
                description="Linux joystick device used by joy_node.",
            ),
            DeclareLaunchArgument(
                "joy_deadzone",
                default_value="0.05",
                description="Low-level joystick deadzone used by joy_node.",
            ),
            DeclareLaunchArgument(
                "joy_autorepeat_rate",
                default_value="25.0",
                description="Joy autorepeat rate so held sticks keep streaming.",
            ),
            DeclareLaunchArgument(
                "config_file",
                default_value=str(params),
                description="YAML file with gamepad bridge parameters.",
            ),
            Node(
                package="joy",
                executable="joy_node",
                name="joy_node",
                output="screen",
                parameters=[
                    {
                        "dev": joy_dev,
                        "deadzone": joy_deadzone,
                        "autorepeat_rate": joy_autorepeat_rate,
                    }
                ],
                condition=IfCondition(launch_joy),
            ),
            Node(
                package="robot_xbox_teleop",
                executable="xbox_command_bridge",
                name="xbox_command_bridge",
                output="screen",
                parameters=[config_file],
            )
        ]
    )
