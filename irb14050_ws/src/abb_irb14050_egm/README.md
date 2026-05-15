# abb_irb14050_egm

ROS2 bridge between your ABB IRB 14050 (7-DOF, over EGM on an IRC5
controller) and the ROS2 graph. A direct port of the existing
`EGM_Toolbox/EGM_controller.py` with the same safety posture
(joint limits, max-speed cap, 250 Hz TX) but split so that:

- **`egm_bridge`** is the only node that holds the UDP socket and
  keeps the mandatory 250 Hz TX loop alive.
- **`joint_commander`** is a human CLI (same verbs as the original:
  `j N DELTA`, `go ...`, `rel ...`, `home`) that publishes to
  `/joint_command` instead of talking UDP.
- **`joint_listener`** is a small subscriber that prints
  `/joint_states`.

## Topics

| direction | topic            | type                    | notes                          |
|-----------|------------------|-------------------------|--------------------------------|
| pub       | `/joint_states`  | `sensor_msgs/JointState`| 7 joints, **radians**, EGM order (J1..J6 then J7 elbow) |
| sub       | `/joint_command` | `sensor_msgs/JointState`| 7 positions, **radians**, EGM order |

Units on the ROS side are radians (ROS convention, plays nice with
URDF and MoveIt2 later). The bridge converts to degrees only at the
UDP boundary.

## Install into your workspace

```bash
cd ~/simulacion_ws/src
# drop the package here (copy the folder)
cd ~/simulacion_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install --packages-select abb_irb14050_egm
source install/setup.bash
```

## Run

Same hardware checklist as the original toolbox:

1. FlexPendant in Manual Reduced Speed.
2. Speed override at 25% or less.
3. Clear space around the robot.
4. Enabling device pressed.
5. **Start the ROS bridge first**, then start the RAPID program
   `egm_joint_irb14050.mod`.

In three terminals (all sourced):

```bash
# T1: the bridge (holds the UDP session)
ros2 launch abb_irb14050_egm egm_bridge.launch.py

# T2: watch positions
ros2 run abb_irb14050_egm joint_listener
# ...or just:
ros2 topic echo /joint_states

# T3: send commands interactively (same CLI as the old toolbox)
ros2 run abb_irb14050_egm joint_commander
# cmd> j 1 50
# cmd> go 0 -30 0 10 0 0 0
# cmd> rel 0 0 0 0 0 0 5
```

You can also drive it without the CLI, from any other node or from
the shell:

```bash
ros2 topic pub --once /joint_command sensor_msgs/msg/JointState \
  "{name: [joint_1,joint_2,joint_3,joint_4,joint_5,joint_6,joint_7],
    position: [0.0, -0.5, 0.0, 0.2, 0.0, 0.0, 0.0]}"
```

(Remember: positions are in **radians** on the ROS side.)

## Parameters

Exposed on `egm_bridge`:

| name              | default           | meaning                                 |
|-------------------|-------------------|-----------------------------------------|
| `egm_rx_port`     | `6511`            | UDP port this host listens on           |
| `egm_tx_ip`       | `192.168.125.1`   | IRC5 IP (must match `UC_DEVICE`)        |
| `egm_tx_port`     | `6510`            | IRC5's UDP port                         |
| `send_rate_hz`    | `250.0`           | TX rate, should match EGM `Samplerate`  |
| `max_speed_deg_s` | `5.0`             | cap on slew rate for `q_target`         |
| `joint_names`     | `[joint_1..7]`    | names published in `JointState.name`    |

## How sim-to-real will work later

This package is the **real-robot** path. The `ros2_control`
hardware interface abstraction means that once you have a URDF and
a `JointPositionController` (or MoveIt2 + a controller) driving
`/joint_command`, the same command pipeline works against Gazebo
(with `gz_ros2_control`) or against this bridge. You don't need to
rewrite the commander or the planner.

## Gotchas

- **The bridge must be launched before RAPID.** Same as the old
  toolbox — if RAPID starts first it sees no UDP peer and times out.
- **Max speed cap is a soft one**; the EGM `\PosCorrGain:=0.1` in
  `egm_joint_irb14050.mod` is the real safety. Raise both together
  when you trust the setup.
- **EGM vs pendant joint order.** On the FlexPendant the IRB 14050
  numbers axes `J1, J2, J7, J3, J4, J5, J6`. On the EGM wire (and
  therefore on `/joint_states` and `/joint_command`) the order is
  `J1, J2, J3, J4, J5, J6, J7` with J7 last.
