"""
gazebo_moveit.launch.py — Full stack: Gazebo + IRB14050 + MoveIt2 + RViz.

Reuses spawn_robot.launch.py for the Gazebo half, then adds:
    - move_group node (MoveIt2 planning)
    - RViz with the MotionPlanning panel

Both move_group and RViz get use_sim_time=True so they stay in sync with
Gazebo's clock.

NOTE on start_state_max_bounds_error:
    Gazebo's physics engine leaves joints with sub-micron numerical noise
    (e.g. gripper_joint_l = -9.9e-15 m when it should be exactly 0). By default
    MoveIt's CheckStartStateBounds planning request adapter rejects any plan
    whose start state is even microscopically outside the joint limits, so
    every plan from a fresh sim aborts with START_STATE_INVALID.

    Setting `start_state_max_bounds_error` to a small but non-zero value (here
    0.1 rad ≈ 5.7° for revolute, or 0.1 m for prismatic — overkill for both)
    tells MoveIt to silently clamp the start state instead of refusing.
    Without this, planning ever works from Gazebo.
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder
import os


def generate_launch_description():
    launch_rviz = LaunchConfiguration("launch_rviz")
    use_nvidia = LaunchConfiguration("use_nvidia")
    render_engine = LaunchConfiguration("render_engine")

    # --- MoveIt config (xacro processed with sim_mode:=gazebo) -----------
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
        ),
        launch_arguments={
            "use_nvidia": use_nvidia,
            "render_engine": render_engine,
        }.items(),
    )

    # --- MoveIt move_group ----------------------------------------------
    # The extra parameters below relax start-state validation to absorb the
    # numerical noise that Gazebo introduces in joint values.
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": True},
            # Tolerance for start-state validation (CheckStartStateBounds adapter)
            {"start_state_max_bounds_error": 0.1},
            # Companion tolerance for path constraints validation
            {"start_state_max_path_constraints_error": 0.1},
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
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "launch_rviz",
                default_value="true",
                description="Launch RViz with the MoveIt MotionPlanning panel.",
            ),
            DeclareLaunchArgument(
                "use_nvidia",
                default_value="false",
                description="Enable NVIDIA Optimus offload variables for Gazebo rendering.",
            ),
            DeclareLaunchArgument(
                "render_engine",
                default_value="ogre",
                description="Gazebo render engine. Use ogre on laptops where ogre2/OpenGL crashes.",
            ),
            spawn_robot,
            move_group_node,
            rviz_node,
        ]
    )
