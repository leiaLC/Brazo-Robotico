"""Launch Gazebo + MoveIt + the behavior-tree web/voice command path."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    launch_rviz = LaunchConfiguration("launch_rviz")
    use_nvidia = LaunchConfiguration("use_nvidia")
    render_engine = LaunchConfiguration("render_engine")
    launch_gamepad = LaunchConfiguration("launch_gamepad")
    launch_gamepad_joy = LaunchConfiguration("launch_gamepad_joy")
    joy_dev = LaunchConfiguration("joy_dev")

    task_share = Path(get_package_share_directory("robot_task_manager"))
    gazebo_share = Path(get_package_share_directory("abb_irb14050_gazebo"))
    gamepad_share = Path(get_package_share_directory("robot_xbox_teleop"))

    tree_params = task_share / "config" / "tree_params.yaml"
    abb_params = task_share / "config" / "abb_real_params.yaml"
    joint_limits = task_share / "config" / "joint_limits.yaml"
    sequences = task_share / "config" / "sequences.yaml"
    gamepad_params = gamepad_share / "config" / "gamepad.yaml"

    gazebo_moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(gazebo_share / "launch" / "gazebo_moveit.launch.py")
        ),
        launch_arguments={
            "launch_rviz": launch_rviz,
            "use_nvidia": use_nvidia,
            "render_engine": render_engine,
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "launch_rviz",
                default_value="false",
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
            DeclareLaunchArgument(
                "launch_gamepad",
                default_value="true",
                description="Launch the generic gamepad-to-task-command bridge.",
            ),
            DeclareLaunchArgument(
                "launch_gamepad_joy",
                default_value="false",
                description="Launch joy/joy_node for a connected controller.",
            ),
            DeclareLaunchArgument(
                "joy_dev",
                default_value="/dev/input/js0",
                description="Linux joystick device used by joy_node.",
            ),
            gazebo_moveit,
            Node(
                package="robot_task_manager",
                executable="robot_task_tree",
                name="robot_task_tree",
                output="screen",
                parameters=[
                    str(tree_params),
                    str(abb_params),
                    {
                        "joint_limits_file": str(joint_limits),
                        "sequences_file": str(sequences),
                        "use_sim_time": True,
                        "simulation_mode": False,
                        "motion_backend": "abb_moveit",
                        "action_server_timeout_s": 20.0,
                    },
                ],
            ),
            Node(
                package="robot_web_interface",
                executable="web_command_bridge",
                name="web_command_bridge",
                output="screen",
                parameters=[{"use_sim_time": True}],
            ),
            Node(
                package="robot_speech",
                executable="voice_pipeline_node",
                name="voice_commander_node",
                output="screen",
                parameters=[{"use_sim_time": True}],
            ),
            Node(
                package="joy",
                executable="joy_node",
                name="joy_node",
                output="screen",
                parameters=[
                    {
                        "dev": joy_dev,
                        "deadzone": 0.05,
                        "autorepeat_rate": 25.0,
                    }
                ],
                condition=IfCondition(launch_gamepad_joy),
            ),
            Node(
                package="robot_xbox_teleop",
                executable="gamepad_command_bridge",
                name="gamepad_command_bridge",
                output="screen",
                parameters=[str(gamepad_params), {"use_sim_time": True}],
                condition=IfCondition(launch_gamepad),
            ),
        ]
    )
