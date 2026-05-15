#!/usr/bin/env python3
"""
routine_player_moveit.py
========================

Reproduces a teach-and-replay YAML routine by routing every arm pose
through MoveIt's MoveGroup action (planning + collision check + time
parameterization), instead of publishing directly to /joint_command.

Pipeline per pose:
    YAML pose (degrees)
        -> JointConstraint goal on /move_action
        -> move_group plans a trajectory
        -> trajectory dispatched to /irb14050_arm_controller/follow_joint_trajectory
        -> egm_moveit_executor relays to /joint_command at the right rate
        -> egm_bridge streams the UDP packets to the IRC5

Gripper and wait steps behave identically to the original routine_player
(publish to /gripper/command, then time.sleep).

Pre-requisites at runtime:
    1. egm_bridge running    (real robot or sim hardware interface)
    2. moveit_real.launch.py running (move_group + egm_moveit_executor + RViz)
    3. Manual verification:  one small Plan & Execute from RViz worked.

Usage:
    source ~/Brazo_Robotico_Bueno/install/setup.bash
    python3 routine_player_moveit.py <path/to/routine.yaml>

Optional CLI flags:
    --group <name>         Planning group in SRDF. Default: irb14050_arm
    --vel <0..1>           Max velocity scaling factor. Default: 0.3
    --acc <0..1>           Max acceleration scaling factor. Default: 0.3
    --dwell <seconds>      Sleep after each gripper command. Default: 2.0
    --plan-time <seconds>  Allowed planning time per pose. Default: 5.0
"""

import argparse
import math
import sys
import time
from pathlib import Path

import yaml
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
)


JOINT_NAMES = [f"joint_{i}" for i in range(1, 8)]
DEFAULT_GROUP = "irb14050_arm"
MOVE_ACTION = "/move_action"
GRIPPER_TOPIC = "/gripper/command"

# Remap from YAML/EGM wire order to URDF/FP mechanical chain order.
# The YAML stores values in EGM wire order [J1, J2, J3, J4, J5, J6, J7].
# The URDF defines joint_1..joint_7 in the FP chain order [J1, J2, J7,
# J3, J4, J5, J6] — i.e. URDF joint_3 is the elbow (EGM J7), not EGM J3.
#
# To compute the value for URDF joint_(slot+1), look up
# yaml_values[YAML_INDEX_PER_FP_SLOT[slot]].
#
# URDF slot 1 (joint_1) ← yaml[0] = EGM J1
# URDF slot 2 (joint_2) ← yaml[1] = EGM J2
# URDF slot 3 (joint_3) ← yaml[6] = EGM J7   (elbow)
# URDF slot 4 (joint_4) ← yaml[2] = EGM J3
# URDF slot 5 (joint_5) ← yaml[3] = EGM J4
# URDF slot 6 (joint_6) ← yaml[4] = EGM J5
# URDF slot 7 (joint_7) ← yaml[5] = EGM J6
YAML_INDEX_PER_URDF_SLOT = [0, 1, 6, 2, 3, 4, 5]


def egm_to_urdf(values_egm):
    """Reorder a 7-element list from EGM wire order to URDF/FP order."""
    return [values_egm[i] for i in YAML_INDEX_PER_URDF_SLOT]


# Standard MoveIt error code values (moveit_msgs/msg/MoveItErrorCodes)
MOVEIT_SUCCESS = 1


class RoutinePlayerMoveIt(Node):
    def __init__(self, routine_path, group, vel_scale, acc_scale,
                 dwell, plan_time):
        super().__init__("routine_player_moveit")

        with open(routine_path) as f:
            self.routine = yaml.safe_load(f)

        self.group = group
        self.vel_scale = vel_scale
        self.acc_scale = acc_scale
        self.dwell = dwell
        self.plan_time = plan_time

        self.move_client = ActionClient(self, MoveGroup, MOVE_ACTION)
        self.gripper_pub = self.create_publisher(String, GRIPPER_TOPIC, 10)

        steps = self.routine.get("steps", [])
        self.get_logger().info(
            f"Loaded routine '{self.routine.get('name', '<unnamed>')}' "
            f"with {len(steps)} steps"
        )
        self.get_logger().info(
            f"group='{group}'  vel_scale={vel_scale}  acc_scale={acc_scale}  "
            f"plan_time={plan_time}s  gripper_dwell={dwell}s"
        )

    def wait_for_servers(self, timeout_sec=15.0):
        self.get_logger().info(f"Waiting for {MOVE_ACTION} server...")
        if not self.move_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError(
                f"{MOVE_ACTION} not available. "
                "Is move_group running (moveit_real.launch.py)?"
            )
        self.get_logger().info("MoveGroup ready.")

    def play(self):
        steps = self.routine.get("steps", [])
        for i, step in enumerate(steps, start=1):
            kind = step.get("type")
            header = f"Step {i}/{len(steps)} ({kind})"

            if kind == "pose":
                joints_deg = step["joints_deg"]
                if len(joints_deg) != 7:
                    self.get_logger().error(
                        f"{header}: expected 7 joints, got {len(joints_deg)}"
                    )
                    return False
                self.get_logger().info(
                    f"{header}: yaml(egm)_deg={['%.2f' % v for v in joints_deg]}"
                )
                # YAML is in EGM wire order; URDF needs FP/mechanical order
                joints_deg_urdf = egm_to_urdf(joints_deg)
                joints_rad_urdf = [math.radians(v) for v in joints_deg_urdf]
                if not self._send_pose_goal(joints_rad_urdf):
                    self.get_logger().error(f"{header}: FAILED, aborting routine.")
                    return False
                self.get_logger().info(f"{header}: SUCCESS")

            elif kind == "gripper":
                action = step.get("action", "")
                msg = String()
                msg.data = action
                self.gripper_pub.publish(msg)
                self.get_logger().info(f"{header}: published '{action}', "
                                       f"dwelling {self.dwell}s")
                time.sleep(self.dwell)

            elif kind == "wait":
                secs = float(step.get("seconds", 0.0))
                self.get_logger().info(f"{header}: sleeping {secs}s")
                time.sleep(secs)

            else:
                self.get_logger().warn(f"{header}: unknown type, skipping.")

        self.get_logger().info("Routine complete.")
        return True

    def _send_pose_goal(self, joints_rad):
        goal = MoveGroup.Goal()
        req = MotionPlanRequest()
        req.group_name = self.group
        req.num_planning_attempts = 10
        req.allowed_planning_time = self.plan_time
        req.max_velocity_scaling_factor = self.vel_scale
        req.max_acceleration_scaling_factor = self.acc_scale

        constraints = Constraints()
        for name, val in zip(JOINT_NAMES, joints_rad):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = val
            jc.tolerance_above = 0.01   # rad (~0.57 deg)
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        req.goal_constraints.append(constraints)

        # CRITICAL: tell move_group to use the current robot state as start,
        # not the empty default. Without is_diff=True, move_group interprets
        # empty start_state/planning_scene as "replace current with empty",
        # then OMPL aborts in microseconds with FAILURE because there's no
        # valid state to plan from.
        req.start_state.is_diff = True

        goal.request = req
        goal.planning_options = PlanningOptions()
        goal.planning_options.plan_only = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True

        send_future = self.move_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        handle = send_future.result()
        if handle is None or not handle.accepted:
            self.get_logger().error("  Goal rejected by move_group.")
            return False

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        res = result_future.result()
        if res is None:
            self.get_logger().error("  No result returned by move_group.")
            return False

        code = res.result.error_code.val
        if code == MOVEIT_SUCCESS:
            return True
        self.get_logger().error(f"  MoveIt error code: {code}")
        return False


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("routine", help="Path to routine YAML")
    p.add_argument("--group", default=DEFAULT_GROUP,
                   help=f"Planning group name (default: {DEFAULT_GROUP})")
    p.add_argument("--vel", type=float, default=0.3,
                   help="max_velocity_scaling_factor in [0, 1] (default: 0.3)")
    p.add_argument("--acc", type=float, default=0.3,
                   help="max_acceleration_scaling_factor in [0, 1] (default: 0.3)")
    p.add_argument("--dwell", type=float, default=2.0,
                   help="seconds to sleep after each gripper command (default: 2.0)")
    p.add_argument("--plan-time", type=float, default=5.0,
                   help="allowed_planning_time per pose (default: 5.0)")
    return p.parse_args()


def main():
    args = parse_args()
    routine_path = Path(args.routine).expanduser().resolve()
    if not routine_path.is_file():
        print(f"Routine not found: {routine_path}", file=sys.stderr)
        sys.exit(1)

    rclpy.init()
    node = RoutinePlayerMoveIt(
        routine_path=str(routine_path),
        group=args.group,
        vel_scale=args.vel,
        acc_scale=args.acc,
        dwell=args.dwell,
        plan_time=args.plan_time,
    )
    ok = False
    try:
        node.wait_for_servers()
        ok = node.play()
    except KeyboardInterrupt:
        node.get_logger().warn("Interrupted by user. Robot may stop mid-trajectory.")
    except Exception as e:
        node.get_logger().error(f"Fatal: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
