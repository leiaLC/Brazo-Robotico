# Intel RealSense D415 - ROS 2 Jazzy

This folder contains scripts and notes to start and verify an Intel RealSense D415 camera using ROS 2 Jazzy on Ubuntu 24.04.

## Tested environment

- Ubuntu 24.04 LTS
- ROS 2 Jazzy
- Intel RealSense D415
- ROS packages:
  - ros-jazzy-realsense2-camera
  - ros-jazzy-realsense2-camera-msgs
  - ros-jazzy-realsense2-description

## Folder structure

realsense_d415_ws/
├── README.md
├── scripts/
│   ├── start_d415.sh
│   ├── check_d415_topics.sh
│   └── view_d415.sh
├── notes/
└── src/

## Installation

Run:

sudo apt update

sudo apt install -y \
  ros-jazzy-realsense2-camera \
  ros-jazzy-realsense2-camera-msgs \
  ros-jazzy-realsense2-description

## Start the camera

From this folder:

cd ~/realsense_d415_ws
./scripts/start_d415.sh

## Expected main topics

/camera/camera/color/image_raw
/camera/camera/color/camera_info
/camera/camera/depth/image_rect_raw
/camera/camera/depth/camera_info

## Check topics and frame rate

In another terminal:

cd ~/realsense_d415_ws
./scripts/check_d415_topics.sh

## Visualize image

In another terminal:

cd ~/realsense_d415_ws
./scripts/view_d415.sh

Recommended topics:

/camera/camera/color/image_raw
/camera/camera/depth/image_rect_raw

Avoid selecting transport-specific topics directly, such as:

compressed
compressedDepth
theora
zstd
metadata

For RGB only, this command can also be used:

ros2 run rqt_image_view rqt_image_view /camera/camera/color/image_raw --ros-args -p image_transport:=raw

## Notes

Depth images are usually encoded as 16UC1, so they are not normal RGB images. If a viewer tries to decode depth as a compressed color image, OpenCV or image transport errors may appear.
