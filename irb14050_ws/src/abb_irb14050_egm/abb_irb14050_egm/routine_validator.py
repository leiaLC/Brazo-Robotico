#!/usr/bin/env python3
"""
routine_validator.py
====================

Checks every pose in a teach-and-replay YAML routine for collision /
joint-limit validity using MoveIt's /check_state_validity service.

No planning. No execution. Just asks MoveIt "is this configuration
itself a valid robot state?" for each pose in the file, and reports
which poses fail along with the specific link pair flagged in
collision.

Intended use:
    Run after a routine fails in routine_player_moveit.py to identify
    which exact poses need re-teaching, so you don't have to re-teach
    the whole routine.

Prerequisites at runtime:
    - move_group is running (from moveit_real.launch.py).
    - egm_bridge is running (so /joint_states is being published).
    - The gripper-state filler is running, OR you accept the default
      gripper_joint_l/r = 0.025 baked into this script.

Usage:
    source ~/Brazo_Robotico_Bueno/install/setup.bash
    python3 routine_validator.py <path/to/routine.yaml>
"""

import math
import sys
from pathlib import Path

import yaml
import rclpy
from rclpy.node import Node

from moveit_msgs.srv import GetStateValidity
from moveit_msgs.msg import RobotState
from sensor_msgs.msg import JointState


JOINT_NAMES = [f"joint_{i}" for i in range(1, 8)]
GRIPPER_JOINTS = ["gripper_joint_l", "gripper_joint_r"]
GRIPPER_OPEN_M = 0.025
GROUP = "irb14050_arm"
SERVICE = "/check_state_validity"

# YAML stores joints in EGM wire order [J1..J7]; URDF defines joint_1..7
# in FP chain order [J1, J2, J7, J3, J4, J5, J6]. URDF joint_3 = EGM J7
# (the elbow). The remap below converts YAML order to URDF order.
YAML_INDEX_PER_URDF_SLOT = [0, 1, 6, 2, 3, 4, 5]


def egm_to_urdf(values_egm):
    return [values_egm[i] for i in YAML_INDEX_PER_URDF_SLOT]


class RoutineValidator(Node):
    def __init__(self, routine_path):
        super().__init__("routine_validator")

        with open(routine_path) as f:
            self.routine = yaml.safe_load(f)

        self.client = self.create_client(GetStateValidity, SERVICE)
        self.get_logger().info(f"Waiting for {SERVICE} ...")
        if not self.client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError(
                f"{SERVICE} not available. Is move_group running?"
            )
        self.get_logger().info(f"{SERVICE} ready.")

    def validate(self):
        steps = self.routine.get("steps", [])
        report = []
        for i, step in enumerate(steps, start=1):
            if step.get("type") != "pose":
                continue
            joints_deg = step["joints_deg"]                  # YAML/EGM order
            joints_deg_urdf = egm_to_urdf(joints_deg)        # URDF/FP order
            joints_rad_urdf = [math.radians(v) for v in joints_deg_urdf]
            valid, contacts = self._check(joints_rad_urdf)
            report.append({
                "step": i,
                "joints_deg": joints_deg,
                "valid": valid,
                "contacts": contacts,
            })
        self._print_report(report)
        return report

    def _check(self, joints_rad):
        req = GetStateValidity.Request()
        req.group_name = GROUP

        rs = RobotState()
        rs.is_diff = True
        rs.joint_state = JointState()
        rs.joint_state.name = list(JOINT_NAMES) + list(GRIPPER_JOINTS)
        rs.joint_state.position = list(joints_rad) + [GRIPPER_OPEN_M,
                                                       GRIPPER_OPEN_M]
        req.robot_state = rs

        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        res = future.result()
        if res is None:
            return False, ["<no response from service>"]

        contacts = [
            f"{c.contact_body_1} <-> {c.contact_body_2}"
            for c in res.contacts
        ]
        return res.valid, contacts

    def _print_report(self, report):
        log = self.get_logger().info
        log("")
        log("=" * 56)
        log(f"  Validation Report — {self.routine.get('name', '<unnamed>')}")
        log("=" * 56)

        for r in report:
            tag = "OK  " if r["valid"] else "FAIL"
            log(f"Step {r['step']:2d} [pose] {tag}: {r['joints_deg']}")
            if not r["valid"]:
                if r["contacts"]:
                    for c in r["contacts"]:
                        log(f"             collision: {c}")
                else:
                    log("             (no contacts reported — possibly "
                        "joint limit or other constraint)")

        n_total = len(report)
        n_ok = sum(1 for r in report if r["valid"])
        n_fail = n_total - n_ok
        log("")
        log(f"Summary: {n_ok}/{n_total} valid, {n_fail} failing")

        if n_fail > 0:
            log("")
            log("Poses that need re-teaching (or small perturbation):")
            for r in report:
                if not r["valid"]:
                    log(f"  Step {r['step']:2d}: {r['joints_deg']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: routine_validator.py <path/to/routine.yaml>",
              file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.is_file():
        print(f"Routine not found: {path}", file=sys.stderr)
        sys.exit(1)

    rclpy.init()
    node = RoutineValidator(str(path))
    try:
        node.validate()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f"Fatal: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
