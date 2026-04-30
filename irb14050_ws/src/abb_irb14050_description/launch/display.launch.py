"""
display.launch.py

Lanza solo robot_state_publisher + RViz.

La fuente de /joint_states queda libre. Las dos opciones normales son:

  A) Test manual con ros2 topic pub (ver instrucciones en README/chat)
  B) El bridge EGM real:
        ros2 run abb_irb14050_egm egm_bridge

NOTA: el QoS override sobre /joint_states hace que rsp escuche
RELIABLE, que es lo que publican tanto `ros2 topic pub` como el
bridge. Sin esto, los mensajes no llegarían a rsp.
"""

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('abb_irb14050_description')

    urdf_path = os.path.join(pkg_share, 'urdf', 'abb_irb14050.urdf')
    rviz_config = os.path.join(pkg_share, 'rviz', 'display.rviz')

    with open(urdf_path, 'r') as f:
        robot_description_xml = f.read()

    robot_description_param = {'robot_description': robot_description_xml}

    rsp_qos_overrides = {
        'qos_overrides': {
            '/joint_states': {
                'subscription': {
                    'reliability': 'reliable',
                    'durability': 'volatile',
                    'history': 'keep_last',
                    'depth': 10,
                }
            }
        }
    }

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[robot_description_param, rsp_qos_overrides],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ])