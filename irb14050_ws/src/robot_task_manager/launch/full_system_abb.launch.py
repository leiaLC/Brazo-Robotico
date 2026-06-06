"""Launch the behavior-tree supervisor with the ABB MoveIt/EGM backend."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    with_viewer = LaunchConfiguration("with_viewer")
    launch_abb_stack = LaunchConfiguration("launch_abb_stack")
    launch_object_cloud_bridge = LaunchConfiguration("launch_object_cloud_bridge")
    launch_tool_camera_tf = LaunchConfiguration("launch_tool_camera_tf")
    launch_gripper_node = LaunchConfiguration("launch_gripper_node")
    launch_gripper_joint_states = LaunchConfiguration("launch_gripper_joint_states")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_gamepad_joy = LaunchConfiguration("launch_gamepad_joy")
    enable_octomap = LaunchConfiguration("enable_octomap")
    controller_ip = LaunchConfiguration("controller_ip")
    gripper_host = LaunchConfiguration("gripper_host")
    gripper_publish_rate_hz = LaunchConfiguration("gripper_publish_rate_hz")
    gripper_rws_timeout = LaunchConfiguration("gripper_rws_timeout")
    egm_rx_port = LaunchConfiguration("egm_rx_port")
    egm_tx_port = LaunchConfiguration("egm_tx_port")
    egm_max_speed_deg_s = LaunchConfiguration("egm_max_speed_deg_s")
    joy_dev = LaunchConfiguration("joy_dev")

    task_share = Path(get_package_share_directory("robot_task_manager"))
    gamepad_share = Path(get_package_share_directory("robot_xbox_teleop"))
    tree_params = task_share / "config" / "tree_params.yaml"
    abb_params = task_share / "config" / "abb_real_params.yaml"
    bridge_params = task_share / "config" / "object_cloud_bridge.yaml"
    joint_limits = task_share / "config" / "joint_limits.yaml"
    sequences = task_share / "config" / "sequences.yaml"
    gamepad_params = gamepad_share / "config" / "gamepad.yaml"

    moveit_config = (
        MoveItConfigsBuilder(
            "abb_irb14050",
            package_name="abb_irb14050_moveit_config",
        )
        .robot_description(
            file_path=os.path.join(
                get_package_share_directory("abb_irb14050_description"),
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
                get_package_share_directory("abb_irb14050_description"),
                "urdf",
                "abb_irb14050.urdf",
            )
        )
        .sensors_3d(file_path="config/sensors_3d_octomap.yaml")
        .to_moveit_configs()
    )
    rviz_config = os.path.join(
        get_package_share_directory("abb_irb14050_moveit_config"),
        "config",
        "moveit.rviz",
    )

    robot_state_publisher = Node(
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
        condition=IfCondition(launch_abb_stack),
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        name="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": False},
        ],
        condition=IfCondition(
            PythonExpression(
                ["'", launch_abb_stack, "' == 'true' and '", enable_octomap, "' != 'true'"]
            )
        ),
    )

    move_group_octomap = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        name="move_group",
        output="screen",
        parameters=[
            moveit_config_octomap.to_dict(),
            {"use_sim_time": False},
        ],
        condition=IfCondition(
            PythonExpression(
                ["'", launch_abb_stack, "' == 'true' and '", enable_octomap, "' == 'true'"]
            )
        ),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
        condition=IfCondition(launch_rviz),
    )

    egm_bridge = Node(
        package="abb_irb14050_egm",
        executable="egm_bridge",
        name="egm_bridge",
        output="screen",
        parameters=[
            {
                "egm_rx_port": egm_rx_port,
                "egm_tx_ip": controller_ip,
                "egm_tx_port": egm_tx_port,
                "max_speed_deg_s": egm_max_speed_deg_s,
            }
        ],
        condition=IfCondition(launch_abb_stack),
    )

    egm_moveit_executor = Node(
        package="abb_irb14050_egm",
        executable="egm_moveit_executor",
        name="egm_moveit_executor",
        output="screen",
        condition=IfCondition(launch_abb_stack),
    )

    tool_camera_static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="tool0_to_camera_link_tf",
        output="screen",
        arguments=[
            "0.01",
            "0.03",
            "0.09",
            "-1.57",
            "-1.57",
            "0",
            "tool0",
            "camera_link",
        ],
        condition=IfCondition(launch_tool_camera_tf),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "with_viewer",
                default_value="true",
                description="Launch the graphical py_trees_ros_viewer.",
            ),
            DeclareLaunchArgument(
                "launch_abb_stack",
                default_value="true",
                description="Launch MoveIt, robot_state_publisher, egm_bridge and egm_moveit_executor.",
            ),
            DeclareLaunchArgument(
                "launch_object_cloud_bridge",
                default_value="true",
                description="Bridge robot_interfaces/DetectedObjectCloudArray to Detection3D.",
            ),
            DeclareLaunchArgument(
                "launch_tool_camera_tf",
                default_value="true",
                description="Publish the calibrated static transform tool0 -> camera_link.",
            ),
            DeclareLaunchArgument(
                "launch_gripper_node",
                default_value="true",
                description="Launch abb_irb14050_egm/gripper_node for /gripper/command.",
            ),
            DeclareLaunchArgument(
                "launch_gripper_joint_states",
                default_value="true",
                description="Publish gripper_joint_l/r on /joint_states for MoveIt current state.",
            ),
            DeclareLaunchArgument(
                "launch_rviz",
                default_value="true",
                description="Launch RViz with the ABB MoveIt configuration.",
            ),
            DeclareLaunchArgument(
                "launch_gamepad_joy",
                default_value="false",
                description="Launch joy/joy_node for a connected controller.",
            ),
            DeclareLaunchArgument(
                "enable_octomap",
                default_value="false",
                description="Enable MoveIt OctoMap updates from the RealSense point cloud.",
            ),
            DeclareLaunchArgument(
                "joy_dev",
                default_value="/dev/input/js0",
                description="Linux joystick device used by joy_node.",
            ),
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
                description="UDP port on this computer/Jetson that receives ABB EGM feedback.",
            ),
            DeclareLaunchArgument(
                "egm_tx_port",
                default_value="6510",
                description="UDP port on the ABB controller that receives EGM commands.",
            ),
            DeclareLaunchArgument(
                "egm_max_speed_deg_s",
                default_value="35.0",
                description="Safety speed cap used by abb_irb14050_egm/egm_bridge.",
            ),
            robot_state_publisher,
            move_group,
            move_group_octomap,
            rviz,
            egm_bridge,
            egm_moveit_executor,
            tool_camera_static_tf,
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
                    {
                        "joint_limits_file": str(joint_limits),
                        "sequences_file": str(sequences),
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
                package="robot_speech",
                executable="voice_pipeline_node",
                name="voice_commander_node",
                output="screen",
            ),
            Node(
                package="robot_web_interface",
                executable="web_command_bridge",
                name="web_command_bridge",
                output="screen",
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
                parameters=[str(gamepad_params)],
            ),
            ExecuteProcess(
                condition=IfCondition(with_viewer),
                cmd=["py-trees-tree-viewer"],
                output="screen",
            ),
        ]
    )
