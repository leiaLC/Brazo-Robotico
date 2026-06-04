from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    image_topic = LaunchConfiguration("image_topic")
    output_dir = LaunchConfiguration("output_dir")
    filename_prefix = LaunchConfiguration("filename_prefix")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/camera/color/image_raw",
                description="RGB image topic published by the RealSense camera.",
            ),
            DeclareLaunchArgument(
                "output_dir",
                default_value="~/robot_yolo_dataset/realsense_435i/images",
                description="Directory outside the workspace where captured images are saved.",
            ),
            DeclareLaunchArgument(
                "filename_prefix",
                default_value="realsense_435i",
                description="Prefix used for saved image filenames.",
            ),
            Node(
                package="robot_perception",
                executable="dataset_capture_node",
                name="dataset_capture_node",
                output="screen",
                parameters=[
                    {
                        "image_topic": image_topic,
                        "output_dir": output_dir,
                        "filename_prefix": filename_prefix,
                    }
                ],
            ),
        ]
    )
