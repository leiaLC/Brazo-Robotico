from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    pkg_share = Path(get_package_share_directory('realsense_d415_bringup'))
    params_file = pkg_share / 'config' / 'd415_params.yaml'

    realsense_node = Node(
        package='realsense2_camera',
        executable='realsense2_camera_node',
        name='camera',
        namespace='camera',
        output='screen',
        parameters=[str(params_file)],
    )

    return LaunchDescription([
        realsense_node,
    ])