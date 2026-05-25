# Generic Gamepad Teleop

This package converts a ROS `sensor_msgs/Joy` stream into the robot task
manager command API used by the behavior tree.

## Launch

Standalone gamepad teleop:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch robot_xbox_teleop gamepad_teleop.launch.py
```

Full Gazebo system with the gamepad bridge and `joy_node`:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch robot_task_manager full_system_gazebo.launch.py launch_gamepad_joy:=true
```

If the controller appears as another Linux joystick device:

```bash
ros2 launch robot_xbox_teleop gamepad_teleop.launch.py joy_dev:=/dev/input/js1
```

## Mapping

The default mapping matches many Xbox-compatible generic controllers:

- `LB` / button `4`: deadman switch.
- Left stick vertical / axis `1`: linear X.
- Left stick horizontal / axis `0`: linear Y.
- Right stick vertical / axis `4`: linear Z.
- Right stick horizontal / axis `3`: angular Z.

To discover the mapping for a different controller, run the launch and echo
the raw Joy topic:

```bash
ros2 topic echo /joy
```

Then edit `config/gamepad.yaml` and update the `axis_*` and `*_button`
indexes. Optional buttons for `ESTOP`, `RESUME`, `CANCEL`, `open` gripper, and
`close` gripper are disabled by default with `-1`.

The bridge keeps publishing the behavior-tree-compatible command type
`XBOX_TELEOP` intentionally. That preserves the existing supervisor tree,
deadman safety gate, and priority arbitration.
