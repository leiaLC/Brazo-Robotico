"""Launch the GPU/workstation-side perception and voice nodes."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    launch_realsense = LaunchConfiguration("launch_realsense")
    launch_perception = LaunchConfiguration("launch_perception")
    launch_object_cloud_bridge = LaunchConfiguration("launch_object_cloud_bridge")
    launch_voice_parser = LaunchConfiguration("launch_voice_parser")

    task_share = Path(get_package_share_directory("robot_task_manager"))
    realsense_share = Path(get_package_share_directory("realsense_d415_bringup"))
    perception_share = Path(get_package_share_directory("robot_perception"))

    bridge_params = task_share / "config" / "object_cloud_bridge.yaml"

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "launch_realsense",
                default_value="true",
                description="Launch the RealSense D415 driver on the GPU workstation.",
            ),
            DeclareLaunchArgument(
                "launch_perception",
                default_value="true",
                description="Launch camera_node, YOLO and pointcloud perception.",
            ),
            DeclareLaunchArgument(
                "launch_object_cloud_bridge",
                default_value="true",
                description="Convert /perception/object_clouds into /perception/detections_3d for the Jetson BT.",
            ),
            DeclareLaunchArgument(
                "launch_voice_parser",
                default_value="true",
                description="Launch voice text parser on the GPU workstation.",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(realsense_share / "launch" / "d415_rgbd_pointcloud.launch.py")
                ),
                condition=IfCondition(launch_realsense),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(perception_share / "launch" / "perception.launch.py")
                ),
                condition=IfCondition(launch_perception),
            ),
            Node(
                package="robot_task_manager",
                executable="object_cloud_bridge",
                name="object_cloud_bridge",
                output="screen",
                parameters=[str(bridge_params)],
                condition=IfCondition(launch_object_cloud_bridge),
            ),
            Node(
                package="robot_voice_interface",
                executable="voice_command_parser",
                name="voice_command_parser",
                output="screen",
                condition=IfCondition(launch_voice_parser),
            ),
        ]
    )
