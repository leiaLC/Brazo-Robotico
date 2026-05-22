"""Launch the central robot task manager."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    with_viewer = LaunchConfiguration("with_viewer")
    share = Path(get_package_share_directory("robot_task_manager"))
    params = share / "config" / "tree_params.yaml"
    joint_limits = share / "config" / "joint_limits.yaml"
    sequences = share / "config" / "sequences.yaml"

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
                    str(params),
                    {
                        "joint_limits_file": str(joint_limits),
                        "sequences_file": str(sequences),
                    },
                ],
            ),
            ExecuteProcess(
                condition=IfCondition(with_viewer),
                cmd=["py-trees-tree-viewer"],
                output="screen",
            ),
        ]
    )
