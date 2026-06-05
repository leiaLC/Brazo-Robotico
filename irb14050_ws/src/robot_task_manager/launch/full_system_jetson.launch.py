"""Launch the lightweight real-robot stack intended for the Jetson Orin NX."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    controller_ip = LaunchConfiguration("controller_ip")
    egm_rx_port = LaunchConfiguration("egm_rx_port")
    egm_tx_port = LaunchConfiguration("egm_tx_port")
    egm_send_rate_hz = LaunchConfiguration("egm_send_rate_hz")
    egm_max_speed_deg_s = LaunchConfiguration("egm_max_speed_deg_s")
    motion_backend = LaunchConfiguration("motion_backend")
    tick_hz = LaunchConfiguration("tick_hz")
    use_introspection = LaunchConfiguration("use_introspection")
    launch_moveit = LaunchConfiguration("launch_moveit")
    enable_octomap = LaunchConfiguration("enable_octomap")
    launch_robot_state_publisher = LaunchConfiguration("launch_robot_state_publisher")
    launch_egm_bridge = LaunchConfiguration("launch_egm_bridge")
    launch_egm_moveit_executor = LaunchConfiguration("launch_egm_moveit_executor")
    launch_egm_direct_action = LaunchConfiguration("launch_egm_direct_action")
    launch_egm_joint_jog_servo = LaunchConfiguration("launch_egm_joint_jog_servo")
    launch_gripper_node = LaunchConfiguration("launch_gripper_node")
    launch_gripper_joint_states = LaunchConfiguration("launch_gripper_joint_states")
    launch_web_bridge = LaunchConfiguration("launch_web_bridge")
    launch_object_cloud_bridge = LaunchConfiguration("launch_object_cloud_bridge")
    launch_tool_camera_tf = LaunchConfiguration("launch_tool_camera_tf")
    launch_gamepad_bridge = LaunchConfiguration("launch_gamepad_bridge")
    launch_gamepad_joy = LaunchConfiguration("launch_gamepad_joy")
    gamepad_config = LaunchConfiguration("gamepad_config")
    joy_dev = LaunchConfiguration("joy_dev")
    gripper_host = LaunchConfiguration("gripper_host")
    gripper_publish_rate_hz = LaunchConfiguration("gripper_publish_rate_hz")
    gripper_rws_timeout = LaunchConfiguration("gripper_rws_timeout")

    task_share = Path(get_package_share_directory("robot_task_manager"))
    gamepad_share = Path(get_package_share_directory("robot_xbox_teleop"))
    description_share = Path(get_package_share_directory("abb_irb14050_description"))

    tree_params = task_share / "config" / "tree_params.yaml"
    abb_params = task_share / "config" / "abb_real_params.yaml"
    jetson_params = task_share / "config" / "jetson_params.yaml"
    bridge_params = task_share / "config" / "object_cloud_bridge.yaml"
    joint_limits = task_share / "config" / "joint_limits.yaml"
    sequences = task_share / "config" / "sequences.yaml"
    gamepad_params = gamepad_share / "config" / "gamepad_jetson.yaml"

    moveit_config = (
        MoveItConfigsBuilder(
            "abb_irb14050",
            package_name="abb_irb14050_moveit_config",
        )
        .robot_description(
            file_path=os.path.join(
                str(description_share),
                "urdf",
                "abb_irb14050.urdf",
            )
        )
        .to_moveit_configs()
    )
    moveit_config_octomap = (
        MoveItConfigsBuilder(
            "abb_irb14050",
            package_name="abb_irb14050_moveit_config",
        )
        .robot_description(
            file_path=os.path.join(
                str(description_share),
                "urdf",
                "abb_irb14050.urdf",
            )
        )
        .sensors_3d(file_path="config/sensors_3d_octomap.yaml")
        .to_moveit_configs()
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "controller_ip",
                default_value="192.168.125.1",
                description="ABB controller IP used by EGM TX.",
            ),
            DeclareLaunchArgument(
                "gripper_host",
                default_value="192.168.125.1",
                description="IP/host used by the RWS gripper client.",
            ),
            DeclareLaunchArgument(
                "gripper_publish_rate_hz",
                default_value="0.0",
                description="RWS gripper state polling rate. 0 disables polling so commands stay responsive.",
            ),
            DeclareLaunchArgument(
                "gripper_rws_timeout",
                default_value="0.75",
                description="HTTP timeout in seconds for RWS gripper reads/writes.",
            ),
            DeclareLaunchArgument(
                "egm_rx_port",
                default_value="6511",
                description="UDP port on the Jetson that receives ABB EGM feedback.",
            ),
            DeclareLaunchArgument(
                "egm_tx_port",
                default_value="6510",
                description="UDP port on the ABB controller that receives EGM commands.",
            ),
            DeclareLaunchArgument(
                "egm_send_rate_hz",
                default_value="250.0",
                description="EGM command send rate.",
            ),
            DeclareLaunchArgument(
                "egm_max_speed_deg_s",
                default_value="5.0",
                description="Safety speed cap used by abb_irb14050_egm/egm_bridge.",
            ),
            DeclareLaunchArgument(
                "motion_backend",
                default_value="abb_moveit",
                description="Use abb_moveit for full planning or egm_direct for joint-only lightweight motion.",
            ),
            DeclareLaunchArgument(
                "tick_hz",
                default_value="15.0",
                description="Behavior tree tick frequency tuned for the Jetson profile.",
            ),
            DeclareLaunchArgument(
                "use_introspection",
                default_value="false",
                description="Disable py_trees introspection by default to reduce Jetson CPU/network load.",
            ),
            DeclareLaunchArgument(
                "launch_moveit",
                default_value="true",
                description="Launch headless MoveIt move_group on the Jetson.",
            ),
            DeclareLaunchArgument(
                "enable_octomap",
                default_value="false",
                description="Enable MoveIt OctoMap updates from the RealSense point cloud.",
            ),
            DeclareLaunchArgument(
                "launch_robot_state_publisher",
                default_value="true",
                description="Publish robot TF from /joint_states.",
            ),
            DeclareLaunchArgument(
                "launch_egm_bridge",
                default_value="true",
                description="Launch the UDP EGM bridge on the Jetson.",
            ),
            DeclareLaunchArgument(
                "launch_egm_moveit_executor",
                default_value="true",
                description="Launch the FollowJointTrajectory executor used by MoveIt.",
            ),
            DeclareLaunchArgument(
                "launch_egm_direct_action",
                default_value="false",
                description="Launch direct /arm/move_joint action server for motion_backend:=egm_direct.",
            ),
            DeclareLaunchArgument(
                "launch_egm_joint_jog_servo",
                default_value="true",
                description="Convert BT teleop Twist commands into EGM /joint_command jogs.",
            ),
            DeclareLaunchArgument(
                "launch_gripper_node",
                default_value="true",
                description="Launch abb_irb14050_egm/gripper_node for /gripper/command.",
            ),
            DeclareLaunchArgument(
                "launch_gripper_joint_states",
                default_value="true",
                description="Publish estimated gripper joint states for MoveIt current-state tracking.",
            ),
            DeclareLaunchArgument(
                "launch_web_bridge",
                default_value="true",
                description="Launch the lightweight web command bridge on the Jetson.",
            ),
            DeclareLaunchArgument(
                "launch_object_cloud_bridge",
                default_value="false",
                description="Launch object_cloud_bridge here if the GPU PC does not publish /perception/detections_3d.",
            ),
            DeclareLaunchArgument(
                "launch_tool_camera_tf",
                default_value="true",
                description="Publish the calibrated static transform tool0 -> camera_link.",
            ),
            DeclareLaunchArgument(
                "launch_gamepad_bridge",
                default_value="true",
                description="Launch the gamepad command bridge on the Jetson.",
            ),
            DeclareLaunchArgument(
                "launch_gamepad_joy",
                default_value="true",
                description="Launch joy/joy_node for the controller connected to the Jetson.",
            ),
            DeclareLaunchArgument(
                "gamepad_config",
                default_value=str(gamepad_params),
                description="YAML file with gamepad_command_bridge mapping parameters.",
            ),
            DeclareLaunchArgument(
                "joy_dev",
                default_value="/dev/input/js0",
                description="Linux joystick device used by joy_node.",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    moveit_config.robot_description,
                    {
                        "qos_overrides": {
                            "/joint_states": {
                                "subscription": {
                                    "reliability": "reliable",
                                    "durability": "volatile",
                                    "history": "keep_last",
                                    "depth": 10,
                                }
                            }
                        }
                    },
                ],
                condition=IfCondition(launch_robot_state_publisher),
            ),
            Node(
                package="moveit_ros_move_group",
                executable="move_group",
                name="move_group",
                output="screen",
                parameters=[moveit_config.to_dict(), {"use_sim_time": False}],
                condition=IfCondition(
                    PythonExpression(
                        ["'", launch_moveit, "' == 'true' and '", enable_octomap, "' != 'true'"]
                    )
                ),
            ),
            Node(
                package="moveit_ros_move_group",
                executable="move_group",
                name="move_group",
                output="screen",
                parameters=[moveit_config_octomap.to_dict(), {"use_sim_time": False}],
                condition=IfCondition(
                    PythonExpression(
                        ["'", launch_moveit, "' == 'true' and '", enable_octomap, "' == 'true'"]
                    )
                ),
            ),
            Node(
                package="abb_irb14050_egm",
                executable="egm_bridge",
                name="egm_bridge",
                output="screen",
                parameters=[
                    {
                        "egm_rx_port": ParameterValue(egm_rx_port, value_type=int),
                        "egm_tx_ip": controller_ip,
                        "egm_tx_port": ParameterValue(egm_tx_port, value_type=int),
                        "send_rate_hz": ParameterValue(egm_send_rate_hz, value_type=float),
                        "max_speed_deg_s": ParameterValue(egm_max_speed_deg_s, value_type=float),
                    }
                ],
                condition=IfCondition(launch_egm_bridge),
            ),
            Node(
                package="abb_irb14050_egm",
                executable="egm_moveit_executor",
                name="egm_moveit_executor",
                output="screen",
                condition=IfCondition(launch_egm_moveit_executor),
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="tool0_to_camera_link_tf",
                output="screen",
                arguments=[
                    "0.0",
                    "0.05",
                    "0.09",
                    "-1.57",
                    "-1.57",
                    "0",
                    "tool0",
                    "camera_link",
                ],
                condition=IfCondition(launch_tool_camera_tf),
            ),
            Node(
                package="abb_irb14050_egm",
                executable="egm_move_joint_action_server",
                name="egm_move_joint_action_server",
                output="screen",
                parameters=[str(jetson_params)],
                condition=IfCondition(launch_egm_direct_action),
            ),
            Node(
                package="abb_irb14050_egm",
                executable="egm_joint_jog_servo",
                name="egm_joint_jog_servo",
                output="screen",
                parameters=[str(jetson_params)],
                condition=IfCondition(launch_egm_joint_jog_servo),
            ),
            Node(
                package="abb_irb14050_egm",
                executable="gripper_node",
                name="gripper_node",
                output="screen",
                parameters=[
                    {
                        "host": gripper_host,
                        "publish_rate_hz": ParameterValue(
                            gripper_publish_rate_hz,
                            value_type=float,
                        ),
                        "timeout": ParameterValue(
                            gripper_rws_timeout,
                            value_type=float,
                        ),
                    }
                ],
                condition=IfCondition(launch_gripper_node),
            ),
            Node(
                package="robot_task_manager",
                executable="gripper_joint_state_publisher",
                name="gripper_joint_state_publisher",
                output="screen",
                parameters=[
                    {
                        "joint_states_topic": "/joint_states",
                        "gripper_command_topic": "/gripper/command",
                        "gripper_state_topic": "/gripper/state",
                        "open_position_m": 0.025,
                        "closed_position_m": 0.0,
                        "default_position_m": 0.0,
                    }
                ],
                condition=IfCondition(launch_gripper_joint_states),
            ),
            Node(
                package="robot_task_manager",
                executable="robot_task_tree",
                name="robot_task_tree",
                output="screen",
                parameters=[
                    str(tree_params),
                    str(abb_params),
                    str(jetson_params),
                    {
                        "joint_limits_file": str(joint_limits),
                        "sequences_file": str(sequences),
                        "simulation_mode": False,
                        "motion_backend": motion_backend,
                        "tick_hz": ParameterValue(tick_hz, value_type=float),
                        "use_introspection": ParameterValue(use_introspection, value_type=bool),
                    },
                ],
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
                package="robot_web_interface",
                executable="web_command_bridge",
                name="web_command_bridge",
                output="screen",
                condition=IfCondition(launch_web_bridge),
            ),
            Node(
                package="robot_web_interface",
                executable="jetson_metrics_publisher",
                name="jetson_metrics_publisher",
                output="screen",
                condition=IfCondition(launch_web_bridge),
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
                        "autorepeat_rate": 40.0,
                    }
                ],
                condition=IfCondition(launch_gamepad_joy),
            ),
            Node(
                package="robot_xbox_teleop",
                executable="gamepad_command_bridge",
                name="gamepad_command_bridge",
                output="screen",
                parameters=[gamepad_config],
                condition=IfCondition(launch_gamepad_bridge),
            ),
        ]
    )
