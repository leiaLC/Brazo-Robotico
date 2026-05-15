"""
Launch the EGM bridge with the default IRB 14050 settings.

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

    return LaunchDescription([
        DeclareLaunchArgument(
            'egm_rx_port', default_value='6511',
            description='UDP port to listen on for EgmRobot'),
        DeclareLaunchArgument(
            'egm_tx_ip', default_value='192.168.125.1',
            description='IP of the IRC5 controller'),
        DeclareLaunchArgument(
            'egm_tx_port', default_value='6510',
            description='UDP port the IRC5 listens on'),
        DeclareLaunchArgument(
            'max_speed_deg_s', default_value='5.0',
            description='Cap on slew rate for joint targets'),

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
    ])
