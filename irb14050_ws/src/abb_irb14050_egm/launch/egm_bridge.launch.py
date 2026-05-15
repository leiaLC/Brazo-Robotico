"""
Launch the EGM bridge (arm) + gripper node, both targeting the IRB 14050.

    ros2 launch abb_irb14050_egm egm_bridge.launch.py

Override a parameter:
    ros2 launch abb_irb14050_egm egm_bridge.launch.py \\
        egm_tx_ip:=192.168.125.1 max_speed_deg_s:=3.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    egm_rx_port = LaunchConfiguration('egm_rx_port')
    egm_tx_ip = LaunchConfiguration('egm_tx_ip')
    egm_tx_port = LaunchConfiguration('egm_tx_port')
    max_speed_deg_s = LaunchConfiguration('max_speed_deg_s')
    gripper_publish_rate_hz = LaunchConfiguration('gripper_publish_rate_hz')

    return LaunchDescription([
        # ---- arguments ----
        DeclareLaunchArgument(
            'egm_rx_port', default_value='6511',
            description='UDP port to listen on for EgmRobot'),
        DeclareLaunchArgument(
            'egm_tx_ip', default_value='192.168.125.1',
            description='IP of the OmniCore controller '
                        '(used by both EGM and the gripper RWS client)'),
        DeclareLaunchArgument(
            'egm_tx_port', default_value='6510',
            description='UDP port the controller listens on for EGM'),
        DeclareLaunchArgument(
            'max_speed_deg_s', default_value='5.0',
            description='Cap on slew rate for joint targets'),
        DeclareLaunchArgument(
            'gripper_publish_rate_hz', default_value='2.0',
            description='Rate at which /gripper/state is published (Hz)'),

        # ---- EGM bridge (arm motion via UDP) ----
        Node(
            package='abb_irb14050_egm',
            executable='egm_bridge',
            name='egm_bridge',
            output='screen',
            parameters=[{
                'egm_rx_port': egm_rx_port,
                'egm_tx_ip': egm_tx_ip,
                'egm_tx_port': egm_tx_port,
                'max_speed_deg_s': max_speed_deg_s,
            }],
        ),

        # ---- Gripper node (RWS IO signals via HTTPS) ----
        Node(
            package='abb_irb14050_egm',
            executable='gripper_node',
            name='gripper_node',
            output='screen',
            parameters=[{
                'host': egm_tx_ip,                       # same controller as EGM
                'publish_rate_hz': gripper_publish_rate_hz,
            }],
        ),
    ])
