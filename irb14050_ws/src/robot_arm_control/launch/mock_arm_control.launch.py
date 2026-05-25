"""Launch mock arm, gripper, and servo adapters."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("robot_arm_control"))
    params = share / "config" / "mock_arm.yaml"
    return LaunchDescription(
        [
            Node(
                package="robot_arm_control",
                executable="mock_arm_action_server",
                name="mock_arm_action_server",
                output="screen",
                parameters=[str(params)],
            ),
            Node(
                package="robot_arm_control",
                executable="mock_gripper_node",
                name="mock_gripper_node",
                output="screen",
                parameters=[str(params)],
            ),
            Node(
                package="robot_arm_control",
                executable="mock_servo_node",
                name="mock_servo_node",
                output="screen",
                parameters=[str(params)],
            ),
        ]
    )
