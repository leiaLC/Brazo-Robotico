"""
waypoint_player_node.py

Replays a YAML file of saved joint poses by publishing to
/joint_command and waiting for /joint_states to converge before
sending the next waypoint.

Requires the egm_bridge to be running and the EGM RAPID program to
be active (FlexPendant in Auto). It does NOT talk to RWS — it only
consumes /joint_states and publishes /joint_command, so it works
identically in simulation later (Gazebo + gz_ros2_control), as
long as whatever is on the other side publishes the same topics.

CLI:
    list                      - list saved poses
    play <n>               - send one pose and wait for arrival
    play_all                  - send all poses, alphabetical order
    play_seq <n1> <n2> ... - send an explicit sequence
    tol <deg>                 - set convergence tolerance (deg)
    dwell <s>                 - set dwell time at each waypoint (s)
    q                         - print last known pose (deg)
    help, quit

Parameters:
    waypoints_file      (str,   default "~/irb14050_waypoints.yaml")
    tolerance_deg       (float, default 1.0)
    dwell_s             (float, default 0.5)
    per_move_timeout_s  (float, default 120.0)
    joint_names         (str[], default joint_1..joint_7)

Convergence criterion:
    max_i |q_current[i] - q_goal[i]| <= tolerance_deg

The bridge caps slew rate at max_speed_deg_s (default 5 deg/s), so
a full 180 deg swing takes ~36 s. Default per_move_timeout_s of
120 s is intentionally generous; tighten it once you trust the
setup.
"""

import math
import os
import threading
import time
from typing import Dict, List, Optional

import yaml

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


HELP = """
Commands:
  list                        - list saved poses
  play <n>                 - send one pose and wait for arrival
  play_all                    - send all poses in alphabetical order
  play_seq <n1> <n2> ...   - send an explicit sequence
  tol <deg>                   - set convergence tolerance (deg)
  dwell <s>                   - set dwell time at each waypoint (s)
  q                           - print last known pose (deg)
  help                        - show this
  quit                        - exit
"""


class WaypointPlayerNode(Node):

    def __init__(self):
        super().__init__('waypoint_player')

        self.declare_parameter(
            'waypoints_file',
            os.path.expanduser('~/irb14050_waypoints.yaml'))
        self.declare_parameter('tolerance_deg', 1.0)
        self.declare_parameter('dwell_s', 0.5)
        self.declare_parameter('per_move_timeout_s', 120.0)
        self.declare_parameter(
            'joint_names',
            ['joint_1', 'joint_2', 'joint_3', 'joint_4',
             'joint_5', 'joint_6', 'joint_7'])

        self.waypoints_file = os.path.expanduser(
            str(self.get_parameter('waypoints_file').value))
        self.tolerance_deg = float(
            self.get_parameter('tolerance_deg').value)
        self.dwell_s = float(self.get_parameter('dwell_s').value)
        self.per_move_timeout_s = float(
            self.get_parameter('per_move_timeout_s').value)
        self.joint_names = list(
            self.get_parameter('joint_names').value)

        self._waypoints: Dict[str, List[float]] = {}
        self._load_file()

        self._lock = threading.Lock()
        self._q_current_rad: Optional[List[float]] = None

        self.pub = self.create_publisher(
            JointState, 'joint_command', 10)
        self.sub = self.create_subscription(
            JointState, 'joint_states', self._on_state, 10)

        self.get_logger().info(
            f"waypoint_player ready.  "
            f"file: {self.waypoints_file}, "
            f"{len(self._waypoints)} waypoint(s) loaded, "
            f"tol={self.tolerance_deg:.2f} deg, "
            f"dwell={self.dwell_s:.2f} s")

    # ---------- file I/O ----------

    def _load_file(self):
        if not os.path.exists(self.waypoints_file):
            self._waypoints = {}
            return
        with open(self.waypoints_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        out: Dict[str, List[float]] = {}
        for name, entry in data.items():
            if isinstance(entry, list) and len(entry) == 7:
                out[name] = [float(v) for v in entry]
            elif isinstance(entry, dict) and 'positions_deg' in entry:
                q = entry['positions_deg']
                if len(q) == 7:
                    out[name] = [float(v) for v in q]
        self._waypoints = out

    # ---------- ROS ----------

    def _on_state(self, msg: JointState):
        if len(msg.position) != 7:
            return
        with self._lock:
            self._q_current_rad = list(msg.position)

    def _current_deg(self) -> Optional[List[float]]:
        with self._lock:
            if self._q_current_rad is None:
                return None
            return [math.degrees(p) for p in self._q_current_rad]

    def _publish_goal_deg(self, q_deg: List[float]):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [math.radians(v) for v in q_deg]
        self.pub.publish(msg)

    # ---------- playback ----------

    def play_one(self, name: str) -> bool:
        """
        Publish the named pose to /joint_command, then block until
        /joint_states is within tolerance of it. Returns True on
        success, False on timeout / missing name / no state yet.
        """
        if name not in self._waypoints:
            self.get_logger().error(f"no such waypoint: '{name}'")
            return False
        goal = self._waypoints[name]

        # Wait briefly for the first /joint_states so we have a
        # baseline; if the bridge is not up, fail fast.
        t0 = time.time()
        while self._current_deg() is None:
            if time.time() - t0 > 5.0:
                self.get_logger().error(
                    "no /joint_states received. "
                    "Is egm_bridge up and the RAPID EGM program "
                    "running?")
                return False
            time.sleep(0.05)

        self._publish_goal_deg(goal)
        self.get_logger().info(
            f"-> '{name}': goal " + self._fmt_q(goal))

        # Wait for convergence.
        t0 = time.time()
        diff = float("inf")
        while rclpy.ok():
            cur = self._current_deg()
            if cur is not None:
                diff = max(abs(c - g) for c, g in zip(cur, goal))
                if diff <= self.tolerance_deg:
                    self.get_logger().info(
                        f"   reached (max err {diff:.2f} deg, "
                        f"{time.time() - t0:.1f} s)")
                    time.sleep(self.dwell_s)
                    return True
            if time.time() - t0 > self.per_move_timeout_s:
                self.get_logger().warning(
                    f"   timeout at '{name}' "
                    f"(last err {diff:.2f} deg)")
                return False
            time.sleep(0.05)
        return False

    def play_sequence(self, names: List[str]) -> int:
        """Play a sequence. Returns count of successful waypoints."""
        ok = 0
        for nm in names:
            if not self.play_one(nm):
                self.get_logger().warning(
                    f"aborting sequence at '{nm}' "
                    f"({ok}/{len(names)} done)")
                return ok
            ok += 1
        self.get_logger().info(
            f"sequence done ({ok}/{len(names)} waypoints)")
        return ok

    # ---------- CLI helpers ----------

    def waypoint_names(self) -> List[str]:
        return sorted(self._waypoints.keys())

    def waypoint_str(self, name: str) -> str:
        if name not in self._waypoints:
            return f"(no such waypoint: '{name}')"
        return f"{name:16s}  " + self._fmt_q(self._waypoints[name])

    @staticmethod
    def _fmt_q(q):
        return "[" + ", ".join(f"{v:+7.2f}" for v in q) + "]"


def cli(node: WaypointPlayerNode):
    print(HELP)
    print("Reminder: egm_bridge must be running and the EGM RAPID "
          "program started before you 'play'.")
    while rclpy.ok():
        try:
            line = input("player> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        try:
            if cmd == "quit":
                break
            elif cmd == "help":
                print(HELP)
            elif cmd == "list":
                names = node.waypoint_names()
                if not names:
                    print("(no waypoints)")
                else:
                    for n in names:
                        print("  " + node.waypoint_str(n))
            elif cmd == "play":
                if len(parts) < 2:
                    print("usage: play <n>")
                    continue
                node.play_one(parts[1])
            elif cmd == "play_all":
                node.play_sequence(node.waypoint_names())
            elif cmd == "play_seq":
                if len(parts) < 2:
                    print("usage: play_seq <n1> <n2> ...")
                    continue
                node.play_sequence(parts[1:])
            elif cmd == "tol":
                node.tolerance_deg = float(parts[1])
                print(f"tolerance_deg = {node.tolerance_deg:.2f}")
            elif cmd == "dwell":
                node.dwell_s = float(parts[1])
                print(f"dwell_s = {node.dwell_s:.2f}")
            elif cmd == "q":
                cur = node._current_deg()
                if cur is None:
                    print("no /joint_states yet")
                else:
                    print("current (deg): " + node._fmt_q(cur))
            else:
                print(f"unknown command: {cmd}")
        except Exception as e:
            print(f"[error] {e}")


def main(args=None):
    rclpy.init(args=args)
    node = WaypointPlayerNode()
    spin_thread = threading.Thread(
        target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        cli(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
