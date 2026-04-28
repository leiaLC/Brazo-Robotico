#!/bin/bash

source /opt/ros/jazzy/setup.bash

echo "Iniciando Intel RealSense D415 en ROS 2 Jazzy..."
echo "Tópicos principales esperados:"
echo "  /camera/camera/color/image_raw"
echo "  /camera/camera/depth/image_rect_raw"
echo ""

ros2 launch realsense2_camera rs_launch.py
