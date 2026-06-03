# Jetson Control Stack

This profile is intended for a Jetson Orin NX running the robot-control side
only. CUDA-heavy vision, STT, and LLM workloads stay on the RTX laptop.

## Jetson ROS2 Launch

Inside the Jetson ROS2 Jazzy environment:

```bash
cd ~/Brazo-Robotico
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash

ros2 launch robot_task_manager jetson_control_stack.launch.py
```

By default this uses `controller_ip:=192.168.125.1` for EGM and
`gripper_host:=192.168.125.1` for the SmartGripper RWS client. The
`gripper_host` value is the host that exposes ABB RWS, not necessarily the
separate network address of the physical gripper device.
Web gripper requests still go through the behavior tree as
`open_gripper`/`close_gripper`; the tree then publishes `/gripper/command`,
and `gripper_node` performs the RWS `10 -> open/close` sequence.

The default launch starts:

- `robot_task_tree`
- `move_group`
- `robot_state_publisher`
- `egm_bridge`
- `egm_moveit_executor`
- `egm_joint_jog_servo`
- `gripper_node`
- `gripper_joint_state_publisher`
- `web_command_bridge`
- `voice_command_parser`

It does not start GPU vision, STT, LLM, Gazebo, RViz, or Next.js.

## Backend On Jetson

The Jetson backend is the preferred boundary for laptop AI inputs:

```bash
cd ~/Brazo-Robotico/web_control_hub/backend
cp jetson.env.example .env
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash
source .venv/bin/activate
python -m app.main
```

Useful endpoints for the RTX laptop:

```txt
POST /voice/text
POST /robot/command
POST /teleop/gripper
POST /perception/detection
POST /perception/detections
GET  /health
GET  /robot/nodes
```

Prefer HTTP/WebSocket into the Jetson backend for robot inputs instead of
publishing directly to the Jetson ROS graph from the laptop.

## Optional Launch Arguments

```bash
ros2 launch robot_task_manager jetson_control_stack.launch.py \
  controller_ip:=192.168.125.1 \
  gripper_host:=192.168.125.1 \
  launch_gamepad:=false \
  launch_joy_node:=false
```

Enable object cloud bridging only if the RTX laptop publishes
`robot_interfaces/DetectedObjectCloudArray` over ROS:

```bash
ros2 launch robot_task_manager jetson_control_stack.launch.py \
  launch_object_cloud_bridge:=true
```
