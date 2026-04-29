# realsense_d415_bringup

ROS 2 bringup package for Intel RealSense D415 using ROS 2 Jazzy.

## Features

- RGB stream
- Depth stream
- Aligned depth
- RGBD
- Point cloud
- TF publishing

## Build

From the workspace root:

colcon build --symlink-install --packages-select realsense_d415_bringup

Then source the workspace:

source install/setup.bash

## Launch

ros2 launch realsense_d415_bringup d415_rgbd_pointcloud.launch.py

## Useful topics

/camera/camera/color/image_raw
/camera/camera/color/camera_info
/camera/camera/depth/image_rect_raw
/camera/camera/depth/camera_info
/camera/camera/aligned_depth_to_color/image_raw
/camera/camera/aligned_depth_to_color/camera_info
/camera/camera/rgbd
/camera/camera/depth/color/points
