# ABB Robotic Arm Web Dashboard

This project implements a web-based supervision dashboard for an ABB robotic arm system integrated with ROS2.

The final robotic system is intended to use an Intel RealSense camera mounted on the ABB robotic arm. The camera will provide visual feedback, while ROS2 topics will provide telemetry such as joint states, end-effector pose and system status.

At this stage, the ABB robot and RealSense camera are not physically connected to the dashboard. Therefore, this version uses simulated video and simulated telemetry to validate the web architecture.

## Features

- Simulated RealSense video stream.
- Real-time ABB robot telemetry.
- Joint angle visualization.
- End-effector pose visualization.
- Camera status.
- System alerts.
- Emergency stop button.
- Modular structure prepared for future ROS2 integration.

## Future ROS2 Integration

The simulated modules can later be replaced by real ROS2 subscribers.

Possible future ROS2 topics:

- `/camera/color/image_raw`
- `/camera/depth/image_rect_raw`
- `/joint_states`
- `/tool_pose`
- `/abb_robot/state`

## Run the project

Install dependencies:

```bash
pip install -r requirements.txt