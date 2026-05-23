"""
spawn_robot.launch.py — Gazebo Harmonic + IRB14050 + ros2_control (no MoveIt).

What it does, in order:
    1. Sets NVIDIA Optimus offload env vars (so Gazebo renders on the dGPU
       on hybrid Intel + NVIDIA laptops).
    2. Sets GZ_SIM_RESOURCE_PATH so Gazebo can resolve mesh URIs.
    3. Starts Gazebo Harmonic with the empty world.
    4. Bridges /clock from Gazebo to ROS (so use_sim_time works).
    5. Processes the xacro with sim_mode:=gazebo and publishes /robot_description.
    6. Spawns the robot entity in Gazebo from that topic.
    7. Sequenced spawn of controllers:
          spawn_robot → joint_state_broadcaster → arm controller → gripper controller

Use this launch to verify Gazebo + controllers without MoveIt in the loop.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # --- NVIDIA Optimus offload (hybrid Intel+NVIDIA laptops) -----------
    use_nvidia = LaunchConfiguration("use_nvidia")
    render_engine = LaunchConfiguration("render_engine")
    set_render_engine = SetEnvironmentVariable(
        name="GZ_RENDER_ENGINE",
        value=render_engine,
    )
    nvidia_offload = SetEnvironmentVariable(
        name="__NV_PRIME_RENDER_OFFLOAD", value="1", condition=IfCondition(use_nvidia)
    )
    nvidia_glx = SetEnvironmentVariable(
        name="__GLX_VENDOR_LIBRARY_NAME", value="nvidia", condition=IfCondition(use_nvidia)
    )
    nvidia_egl = SetEnvironmentVariable(
        name="__EGL_VENDOR_LIBRARY_FILENAMES",
        value="/usr/share/glvnd/egl_vendor.d/10_nvidia.json",
        condition=IfCondition(use_nvidia),
    )

    # --- Gazebo's resource search path ----------------------------------
    description_share = get_package_share_directory("abb_irb14050_description")
    description_share_parent = os.path.dirname(description_share)

    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    new_resource_path = (
        description_share_parent
        + (":" + existing_resource_path if existing_resource_path else "")
    )

    set_gz_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=new_resource_path,
    )

    # --- Paths -----------------------------------------------------------
    pkg_gazebo = FindPackageShare("abb_irb14050_gazebo")
    pkg_moveit_config = FindPackageShare("abb_irb14050_moveit_config")
    pkg_ros_gz_sim = FindPackageShare("ros_gz_sim")

    world_file = PathJoinSubstitution([pkg_gazebo, "worlds", "empty.world"])
    xacro_file = PathJoinSubstitution(
        [pkg_moveit_config, "config", "abb_irb14050.urdf.xacro"]
    )
    initial_positions_file = PathJoinSubstitution(
        [pkg_moveit_config, "config", "initial_positions.yaml"]
    )

    # --- Robot description (xacro processed with sim_mode:=gazebo) -------
    robot_description_content = ParameterValue(
        Command(
            [
                FindExecutable(name="xacro"),
                " ",
                xacro_file,
                " ",
                "sim_mode:=gazebo",
                " ",
                "initial_positions_file:=",
                initial_positions_file,
            ]
        ),
        value_type=str,
    )

    robot_description = {
        "robot_description": robot_description_content,
        "use_sim_time": True,
    }

    # --- Nodes -----------------------------------------------------------

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [pkg_ros_gz_sim, "/launch/gz_sim.launch.py"]
        ),
        launch_arguments={"gz_args": ["-r -v 3 ", world_file]}.items(),
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic", "robot_description",
            "-name", "abb_irb14050",
            "-z", "0.0",
            "-allow_renaming", "true",
        ],
        output="screen",
    )

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    # --- Controller spawners (sequenced after entity is spawned) ---------
    load_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager", "/controller_manager",
        ],
        output="screen",
    )

    load_arm = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "irb14050_arm_controller",
            "--controller-manager", "/controller_manager",
        ],
        output="screen",
    )

    load_gripper = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "gripper_controller",
            "--controller-manager", "/controller_manager",
        ],
        output="screen",
    )

    # Chain: spawn → jsb → arm → gripper
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn_robot, on_exit=[load_jsb])
    )
    after_jsb = RegisterEventHandler(
        OnProcessExit(target_action=load_jsb, on_exit=[load_arm])
    )
    after_arm = RegisterEventHandler(
        OnProcessExit(target_action=load_arm, on_exit=[load_gripper])
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use Gazebo simulation clock",
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
            set_render_engine,
            nvidia_offload,
            nvidia_glx,
            nvidia_egl,
            set_gz_resource_path,
            gazebo,
            clock_bridge,
            robot_state_publisher,
            spawn_robot,
            after_spawn,
            after_jsb,
            after_arm,
        ]
    )
