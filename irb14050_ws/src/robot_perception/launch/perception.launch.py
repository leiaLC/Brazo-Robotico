from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('robot_perception'),
        'config', 'yolo_params.yaml'
    )

    return LaunchDescription([
        Node(
            package='robot_perception',
            executable='camera_node',
            name='camera_node',
            output='screen',
        ),
        Node(
            package='robot_perception',
            executable='yolo_node',
            name='yolo_node',
            output='screen',
            parameters=[config],
        ),
    ])