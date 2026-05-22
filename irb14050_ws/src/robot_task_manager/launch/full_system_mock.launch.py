"""Launch the full mock robot decision system."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    with_viewer = LaunchConfiguration("with_viewer")
    task_share = Path(get_package_share_directory("robot_task_manager"))
    xbox_share = Path(get_package_share_directory("robot_xbox_teleop"))
    perception_share = Path(get_package_share_directory("robot_perception"))
    arm_share = Path(get_package_share_directory("robot_arm_control"))

    tree_params = task_share / "config" / "tree_params.yaml"
    joint_limits = task_share / "config" / "joint_limits.yaml"
    sequences = task_share / "config" / "sequences.yaml"
    xbox_params = xbox_share / "config" / "xbox.yaml"
    perception_params = perception_share / "config" / "perception.yaml"
    arm_params = arm_share / "config" / "mock_arm.yaml"

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "with_viewer",
                default_value="false",
                description="Launch the graphical py_trees_ros_viewer.",
            ),
            Node(
                package="robot_task_manager",
                executable="robot_task_tree",
                name="robot_task_tree",
                output="screen",
                parameters=[
                    str(tree_params),
                    {
                        "joint_limits_file": str(joint_limits),
                        "sequences_file": str(sequences),
                        "simulation_mode": True,
                    },
                ],
            ),
            Node(
                package="robot_voice_interface",
                executable="voice_command_parser",
                name="voice_command_parser",
                output="screen",
            ),
            Node(
                package="robot_web_interface",
                executable="web_command_bridge",
                name="web_command_bridge",
                output="screen",
            ),
            Node(
                package="robot_xbox_teleop",
                executable="xbox_command_bridge",
                name="xbox_command_bridge",
                output="screen",
                parameters=[str(xbox_params)],
            ),
            Node(
                package="robot_perception",
                executable="mock_yolo_detector",
                name="mock_yolo_detector",
                output="screen",
                parameters=[str(perception_params)],
            ),
            Node(
                package="robot_arm_control",
                executable="mock_arm_action_server",
                name="mock_arm_action_server",
                output="screen",
                parameters=[str(arm_params)],
            ),
            Node(
                package="robot_arm_control",
                executable="mock_gripper_node",
                name="mock_gripper_node",
                output="screen",
                parameters=[str(arm_params)],
            ),
            Node(
                package="robot_arm_control",
                executable="mock_servo_node",
                name="mock_servo_node",
                output="screen",
                parameters=[str(arm_params)],
            ),
            ExecuteProcess(
                condition=IfCondition(with_viewer),
                cmd=["py-trees-tree-viewer"],
                output="screen",
            ),
        ]
    )
