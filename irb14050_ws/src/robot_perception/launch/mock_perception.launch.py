"""Launch mock perception."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("robot_perception"))
    params = share / "config" / "perception.yaml"
    return LaunchDescription(
        [
            Node(
                package="robot_perception",
                executable="mock_yolo_detector",
                name="mock_yolo_detector",
                output="screen",
                parameters=[str(params)],
            )
        ]
    )
