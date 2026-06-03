"""Launch the Jetson control-only robot stack with laptop AI inputs.

This profile keeps CUDA-heavy vision/STT/LLM work off the Jetson. The Jetson
owns only robot authority: behavior tree, MoveIt, EGM, gripper, teleop servo,
and lightweight command bridges.
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    controller_ip = LaunchConfiguration("controller_ip")
    gripper_host = LaunchConfiguration("gripper_host")
    joy_dev = LaunchConfiguration("joy_dev")
    launch_gamepad = LaunchConfiguration("launch_gamepad")
    launch_joy_node = LaunchConfiguration("launch_joy_node")
    launch_object_cloud_bridge = LaunchConfiguration("launch_object_cloud_bridge")
    launch_voice_parser = LaunchConfiguration("launch_voice_parser")

    task_share = Path(get_package_share_directory("robot_task_manager"))
    jetson_base_launch = task_share / "launch" / "full_system_jetson.launch.py"

    control_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(jetson_base_launch)),
        launch_arguments={
            "controller_ip": controller_ip,
            "gripper_host": gripper_host,
            "motion_backend": "abb_moveit",
            "tick_hz": "15.0",
            "use_introspection": "false",
            "launch_moveit": "true",
            "launch_robot_state_publisher": "true",
            "launch_egm_bridge": "true",
            "launch_egm_moveit_executor": "true",
            "launch_egm_direct_action": "false",
            "launch_egm_joint_jog_servo": "true",
            "launch_gripper_node": "true",
            "launch_gripper_joint_states": "true",
            "launch_web_bridge": "true",
            # Keep this false when the RTX laptop publishes Detection3D
            # through the Jetson backend. Enable it only if the laptop sends
            # robot_interfaces/DetectedObjectCloudArray over ROS.
            "launch_object_cloud_bridge": launch_object_cloud_bridge,
            "launch_gamepad_bridge": launch_gamepad,
            "launch_gamepad_joy": launch_joy_node,
            "joy_dev": joy_dev,
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "controller_ip",
                default_value="192.168.125.1",
                description="ABB controller IP used by EGM.",
            ),
            DeclareLaunchArgument(
                "gripper_host",
                default_value="192.168.125.1",
                description="SmartGripper RWS host. RWS is exposed by the ABB controller.",
            ),
            DeclareLaunchArgument(
                "launch_gamepad",
                default_value="false",
                description="Launch gamepad_command_bridge on the Jetson.",
            ),
            DeclareLaunchArgument(
                "launch_joy_node",
                default_value="false",
                description="Launch joy_node for a controller connected to the Jetson.",
            ),
            DeclareLaunchArgument(
                "joy_dev",
                default_value="/dev/input/js0",
                description="Linux joystick device when launch_joy_node is true.",
            ),
            DeclareLaunchArgument(
                "launch_object_cloud_bridge",
                default_value="false",
                description=(
                    "Enable only if the RTX laptop publishes "
                    "robot_interfaces/DetectedObjectCloudArray over ROS."
                ),
            ),
            DeclareLaunchArgument(
                "launch_voice_parser",
                default_value="true",
                description="Parse text from /voice/text into RobotCommand on the Jetson.",
            ),
            control_stack,
            Node(
                package="robot_voice_interface",
                executable="voice_command_parser",
                name="voice_command_parser",
                output="screen",
                condition=IfCondition(launch_voice_parser),
            ),
        ]
    )
