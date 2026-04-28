#!/bin/bash

source /opt/ros/jazzy/setup.bash

echo "Abriendo rqt_image_view..."
echo "Selecciona alguno de estos tópicos:"
echo "  /camera/camera/color/image_raw"
echo "  /camera/camera/depth/image_rect_raw"
echo ""

ros2 run rqt_image_view rqt_image_view
