#!/usr/bin/env python3
"""
routine_player.py
ROS2 node that plays back a recorded routine (arm poses + gripper actions).

Joint ordering note:
  - routine_teach.py reads via RWS in EGM wire order: [J1, J2, J3, J4, J5, J6, J7]
  - egm_bridge publishes /joint_states and subscribes /joint_command in FP
    display order: [J1, J2, J7, J3, J4, J5, J6] (with generic names
    joint_1..joint_7)
  - This player remaps from YAML order to FP order before publishing,
    and the /joint_states feedback already arrives in FP order, so the
    pose-reached check is direct.

Topics:
  pub /joint_command   (sensor_msgs/JointState, radians, FP display order)
  pub /gripper/command (std_msgs/String, 'open'|'close'|'standby')
  sub /joint_states    (sensor_msgs/JointState, FP display order)
"""

import math
import time
import yaml

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import JointState


JOINT_NAMES = ['joint_1', 'joint_2', 'joint_3', 'joint_4',
               'joint_5', 'joint_6', 'joint_7']

# Mapping from FP-display-order position index to EGM-wire-order index
# in the YAML/teach output. To get the value to publish at FP slot i,
# look up yaml_values[YAML_INDEX_PER_FP_SLOT[i]].
#
# FP slot 1 (joint_1) <- J1 EGM = yaml index 0
# FP slot 2 (joint_2) <- J2 EGM = yaml index 1
# FP slot 3 (joint_3) <- J7 EGM = yaml index 6
# FP slot 4 (joint_4) <- J3 EGM = yaml index 2
# FP slot 5 (joint_5) <- J4 EGM = yaml index 3
# FP slot 6 (joint_6) <- J5 EGM = yaml index 4
# FP slot 7 (joint_7) <- J6 EGM = yaml index 5
YAML_INDEX_PER_FP_SLOT = [0, 1, 6, 2, 3, 4, 5]


def egm_to_fp(values_egm):
    """Reorder a 7-element list from EGM wire order to FP display order."""
    return [values_egm[i] for i in YAML_INDEX_PER_FP_SLOT]


class RoutinePlayer(Node):

    IDLE = 0
    MOVING = 1
    WAITING = 2
    DONE = 3

    def __init__(self):
        super().__init__('routine_player')

        # ---- parameters ----
        self.declare_parameter('routine_file', '')
        self.declare_parameter('pose_tolerance_deg', 2.5)
        self.declare_parameter('max_joint_speed_deg_s', 5.0)
        self.declare_parameter('pose_timeout_buffer_s', 5.0)
        self.declare_parameter('min_pose_timeout_s', 4.0)
        self.declare_parameter('gripper_dwell_s', 2.0)
        self.declare_parameter('startup_delay_s', 1.5)

        rf = self.get_parameter('routine_file').get_parameter_value().string_value
        if not rf:
            self.get_logger().error("Parameter 'routine_file' is required.")
            rclpy.shutdown()
            return

        with open(rf) as f:
            self.routine = yaml.safe_load(f)

        self.tolerance_rad = math.radians(
            self.get_parameter('pose_tolerance_deg').get_parameter_value().double_value
        )
        self.max_speed_deg_s = self.get_parameter(
            'max_joint_speed_deg_s').get_parameter_value().double_value
        self.timeout_buffer_s = self.get_parameter(
            'pose_timeout_buffer_s').get_parameter_value().double_value
        self.min_timeout_s = self.get_parameter(
            'min_pose_timeout_s').get_parameter_value().double_value
        self.gripper_dwell_s = self.get_parameter(
            'gripper_dwell_s').get_parameter_value().double_value
        startup_delay = self.get_parameter(
            'startup_delay_s').get_parameter_value().double_value

        # ---- publishers / subscriber ----
        self.joint_pub = self.create_publisher(
            JointState, '/joint_command', 10)
        self.gripper_pub = self.create_publisher(
            String, '/gripper/command', 10)
        self.joint_sub = self.create_subscription(
            JointState, '/joint_states', self._on_joint_states, 10)

        # ---- state ----
        self.current_joints_fp = None   # /joint_states (FP order, radians)
        self.target_rad_fp = None       # current target (FP order, radians)
        self.steps = self.routine.get('steps', [])
        self.idx = 0
        self.state = self.IDLE
        self.deadline = 0.0
        self.start_time = time.time() + startup_delay

        name = self.routine.get('name', '(unnamed)')
        self.get_logger().info(
            f"Loaded '{name}' with {len(self.steps)} step(s). "
            f"tol={math.degrees(self.tolerance_rad):.1f} deg, "
            f"max_speed={self.max_speed_deg_s:.1f} deg/s. "
            f"Starting in {startup_delay:.1f}s..."
        )

        self.tick = self.create_timer(0.1, self._tick)

    # ---- subscriber ----------------------------------------------

    def _on_joint_states(self, msg: JointState):
        # Already in FP display order — no reordering needed
        self.current_joints_fp = list(msg.position)

    # ---- state machine tick --------------------------------------

    def _tick(self):
        now = time.time()
        if now < self.start_time:
            return

        if self.state == self.IDLE:
            self._begin_next_step()
        elif self.state == self.MOVING:
            self._tick_moving(now)
        elif self.state == self.WAITING:
            if now >= self.deadline:
                self.state = self.IDLE

    def _tick_moving(self, now):
        if self.current_joints_fp is None or len(self.current_joints_fp) < 7:
            if now >= self.deadline:
                self.get_logger().warn(
                    "    no usable /joint_states; advancing on timeout"
                )
                self.state = self.IDLE
            return

        errs = [abs(c - t) for c, t in
                zip(self.current_joints_fp[:7], self.target_rad_fp)]
        max_err = max(errs)

        if max_err < self.tolerance_rad:
            self.get_logger().info(
                f"    reached (max err {math.degrees(max_err):.2f} deg)"
            )
            self.state = self.IDLE
        elif now >= self.deadline:
            self.get_logger().warn(
                f"    pose timeout (max err {math.degrees(max_err):.2f} deg)"
            )
            self.state = self.IDLE

    # ---- step dispatch ------------------------------------------

    def _begin_next_step(self):
        if self.idx >= len(self.steps):
            self.get_logger().info("Routine complete.")
            self.state = self.DONE
            self.tick.cancel()
            return

        step = self.steps[self.idx]
        self.idx += 1
        stype = step.get('type')

        if stype == 'pose':
            # YAML is in EGM wire order [J1, J2, J3, J4, J5, J6, J7]
            joints_deg_egm = step['joints_deg']
            target_rad_egm = [math.radians(j) for j in joints_deg_egm]

            # Remap to FP order for the bridge
            self.target_rad_fp = egm_to_fp(target_rad_egm)
            joints_deg_fp = egm_to_fp(joints_deg_egm)

            # Compute dynamic timeout (from current pos to target, in FP order)
            timeout_s = self.min_timeout_s
            max_delta_deg = 0.0
            if (self.current_joints_fp is not None
                    and len(self.current_joints_fp) >= 7):
                deltas_deg = [
                    abs(math.degrees(c) - jd)
                    for c, jd in zip(self.current_joints_fp[:7], joints_deg_fp)
                ]
                max_delta_deg = max(deltas_deg)
                estimated_s = max_delta_deg / max(self.max_speed_deg_s, 0.1)
                timeout_s = max(self.min_timeout_s,
                                estimated_s + self.timeout_buffer_s)

            self.get_logger().info(
                f"Step {self.idx}/{len(self.steps)}: pose "
                f"(max delta {max_delta_deg:.1f} deg, "
                f"timeout {timeout_s:.1f}s)"
            )

            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = list(JOINT_NAMES)
            msg.position = list(self.target_rad_fp)
            self.joint_pub.publish(msg)

            self.deadline = time.time() + timeout_s
            self.state = self.MOVING

        elif stype == 'gripper':
            action = step['action']
            self.get_logger().info(
                f"Step {self.idx}/{len(self.steps)}: gripper {action}"
            )
            msg = String()
            msg.data = action
            self.gripper_pub.publish(msg)
            self.deadline = time.time() + self.gripper_dwell_s
            self.state = self.WAITING

        elif stype == 'wait':
            secs = float(step['seconds'])
            self.get_logger().info(
                f"Step {self.idx}/{len(self.steps)}: wait {secs}s"
            )
            self.deadline = time.time() + secs
            self.state = self.WAITING

        else:
            self.get_logger().warn(
                f"Step {self.idx}/{len(self.steps)}: "
                f"unknown type '{stype}', skipping"
            )
            self.state = self.IDLE


def main(args=None):
    rclpy.init(args=args)
    node = RoutinePlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
