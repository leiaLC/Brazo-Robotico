"""
gazebo_moveit.launch.py — Full stack: Gazebo + IRB14050 + MoveIt2 + RViz.

Reuses spawn_robot.launch.py for the Gazebo half, then adds:
    - move_group node (MoveIt2 planning)
    - RViz with the MotionPlanning panel

Both move_group and RViz get use_sim_time=True so they stay in sync with
Gazebo's clock.
"""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder
import os


def generate_launch_description():
    # --- MoveIt config (xacro processed with sim_mode:=gazebo) -----------
    # The mappings dict is forwarded as xacro args, so the resulting
    # robot_description carries the <gazebo> plugin block AND the
    # gz_ros2_control hardware plugin.
    moveit_config = (
        MoveItConfigsBuilder("abb_irb14050", package_name="abb_irb14050_moveit_config")
        .robot_description(
            file_path="config/abb_irb14050.urdf.xacro",
            mappings={"sim_mode": "gazebo"},
        )
        .robot_description_semantic(file_path="config/abb_irb14050.srdf")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    # --- Gazebo + robot + controllers (reuse spawn_robot.launch.py) -----
    gazebo_pkg = FindPackageShare("abb_irb14050_gazebo")
    spawn_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [gazebo_pkg, "/launch/spawn_robot.launch.py"]
        )
    )

    # --- MoveIt move_group ----------------------------------------------
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": True},
        ],
    )

    # --- RViz with MoveIt's pre-configured layout -----------------------
    rviz_config_file = os.path.join(
        get_package_share_directory("abb_irb14050_moveit_config"),
        "config",
        "moveit.rviz",
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            {"use_sim_time": True},
        ],
    )

    return LaunchDescription(
        [
            spawn_robot,
            move_group_node,
            rviz_node,
        ]
    )
