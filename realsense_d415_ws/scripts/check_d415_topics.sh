#!/bin/bash

source /opt/ros/jazzy/setup.bash

echo "=== Nodos activos ==="
ros2 node list

echo ""
echo "=== Tópicos RealSense ==="
ros2 topic list | grep -E "camera|depth|color|infra|points"

echo ""
echo "=== Frecuencia imagen color ==="
timeout 5 ros2 topic hz /camera/camera/color/image_raw

echo ""
echo "=== Frecuencia imagen depth ==="
timeout 5 ros2 topic hz /camera/camera/depth/image_rect_raw
