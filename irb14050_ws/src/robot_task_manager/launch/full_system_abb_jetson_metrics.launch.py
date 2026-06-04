"""Launch the ABB stack plus Jetson metrics publishing for the web dashboard."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    with_viewer = LaunchConfiguration("with_viewer")
    launch_abb_stack = LaunchConfiguration("launch_abb_stack")
    launch_object_cloud_bridge = LaunchConfiguration("launch_object_cloud_bridge")
    launch_tool_camera_tf = LaunchConfiguration("launch_tool_camera_tf")
    launch_gripper_node = LaunchConfiguration("launch_gripper_node")
    launch_gripper_joint_states = LaunchConfiguration("launch_gripper_joint_states")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_gamepad_joy = LaunchConfiguration("launch_gamepad_joy")
    joy_dev = LaunchConfiguration("joy_dev")
    controller_ip = LaunchConfiguration("controller_ip")
    gripper_host = LaunchConfiguration("gripper_host")
    gripper_publish_rate_hz = LaunchConfiguration("gripper_publish_rate_hz")
    gripper_rws_timeout = LaunchConfiguration("gripper_rws_timeout")
    egm_rx_port = LaunchConfiguration("egm_rx_port")
    egm_tx_port = LaunchConfiguration("egm_tx_port")
    egm_max_speed_deg_s = LaunchConfiguration("egm_max_speed_deg_s")
    launch_jetson_metrics = LaunchConfiguration("launch_jetson_metrics")
    jetson_metrics_topic = LaunchConfiguration("jetson_metrics_topic")
    jetson_metrics_publish_hz = LaunchConfiguration("jetson_metrics_publish_hz")

    abb_launch = Path(__file__).resolve().parent / "full_system_abb.launch.py"

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
            DeclareLaunchArgument(
                "launch_jetson_metrics",
                default_value="true",
                description="Publish Jetson metrics on ROS2 for the web dashboard.",
            ),
            DeclareLaunchArgument(
                "jetson_metrics_topic",
                default_value="/system/jetson_metrics",
                description="Topic used by robot_web_interface/jetson_metrics_publisher.",
            ),
            DeclareLaunchArgument(
                "jetson_metrics_publish_hz",
                default_value="0.5",
                description="Jetson metrics publish frequency in Hz.",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(abb_launch)),
                launch_arguments={
                    "with_viewer": with_viewer,
                    "launch_abb_stack": launch_abb_stack,
                    "launch_object_cloud_bridge": launch_object_cloud_bridge,
                    "launch_tool_camera_tf": launch_tool_camera_tf,
                    "launch_gripper_node": launch_gripper_node,
                    "launch_gripper_joint_states": launch_gripper_joint_states,
                    "launch_rviz": launch_rviz,
                    "launch_gamepad_joy": launch_gamepad_joy,
                    "joy_dev": joy_dev,
                    "controller_ip": controller_ip,
                    "gripper_host": gripper_host,
                    "gripper_publish_rate_hz": gripper_publish_rate_hz,
                    "gripper_rws_timeout": gripper_rws_timeout,
                    "egm_rx_port": egm_rx_port,
                    "egm_tx_port": egm_tx_port,
                    "egm_max_speed_deg_s": egm_max_speed_deg_s,
                }.items(),
            ),
            Node(
                package="robot_web_interface",
                executable="jetson_metrics_publisher",
                name="jetson_metrics_publisher",
                output="screen",
                parameters=[
                    {
                        "topic": jetson_metrics_topic,
                        "publish_hz": ParameterValue(
                            jetson_metrics_publish_hz,
                            value_type=float,
                        ),
                    }
                ],
                condition=IfCondition(launch_jetson_metrics),
            ),
        ]
    )
