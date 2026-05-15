"""
Interactive joint commander node.

Same CLI as the original EGMController (j N DELTA, go J1..J7, rel,
home, q, etc.) but instead of talking UDP to the IRC5, it
subscribes to /joint_states to learn the current pose and
publishes to /joint_command so the egm_bridge can move the robot.

User input stays in degrees (to match the original toolbox muscle
memory). Conversion to radians happens right before publishing.
"""

import math
import threading
import time
from typing import List, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


HELP = """
Commands:
  q                              - show last known joint positions
  go J1 J2 J3 J4 J5 J6 J7        - publish absolute target (deg)
  rel dJ1 dJ2 ... dJ7            - publish relative deltas (deg)
  j N DELTA                      - nudge joint N (1..7) by DELTA deg
  home                           - publish all-zeros target (deg)
  help                           - show this
  quit                           - exit
"""


class JointCommanderNode(Node):

    def __init__(self):
        super().__init__('joint_commander')

        self.declare_parameter(
            'joint_names',
            ['joint_1', 'joint_2', 'joint_3', 'joint_4',
             'joint_5', 'joint_6', 'joint_7'])
        self.joint_names = list(
            self.get_parameter('joint_names').value)

        self._lock = threading.Lock()
        self._q_current_rad: Optional[List[float]] = None

        self.pub = self.create_publisher(
            JointState, 'joint_command', 10)
        self.sub = self.create_subscription(
            JointState, 'joint_states', self._on_state, 10)

    def _on_state(self, msg: JointState):
        if len(msg.position) != 7:
            return
        with self._lock:
            self._q_current_rad = list(msg.position)

    def current_deg(self) -> Optional[List[float]]:
        with self._lock:
            if self._q_current_rad is None:
                return None
            return [math.degrees(p) for p in self._q_current_rad]

    def send_target_deg(self, q_deg: List[float]):
        if len(q_deg) != 7:
            raise ValueError("target must have 7 values")
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [math.radians(v) for v in q_deg]
        self.pub.publish(msg)
        self.get_logger().info(
            "Published target (deg): "
            + "[" + ", ".join(f"{v:+7.2f}" for v in q_deg) + "]")


def cli(node: JointCommanderNode):
    print(HELP)
    print("Waiting for first /joint_states message...")
    # NOTE: rclpy.spin(node) is already running in a background
    # thread (see main()). We must NOT call spin_once here — that
    # would create a second executor on the same node and rclpy
    # raises "Executor is already spinning". Just poll the shared
    # state passively.
    while rclpy.ok() and node.current_deg() is None:
        time.sleep(0.1)
    print("Connected. Type 'help' for commands.")

    while rclpy.ok():
        try:
            line = input("cmd> ").strip()
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
            elif cmd == "q":
                cur = node.current_deg()
                print("current (deg): "
                      + "[" + ", ".join(f"{v:+7.2f}" for v in cur)
                      + "]")
            elif cmd == "go":
                target = [float(x) for x in parts[1:8]]
                node.send_target_deg(target)
            elif cmd == "rel":
                deltas = [float(x) for x in parts[1:8]]
                cur = node.current_deg()
                if cur is None:
                    print("no current state yet")
                    continue
                target = [c + d for c, d in zip(cur, deltas)]
                node.send_target_deg(target)
            elif cmd == "j":
                n = int(parts[1])
                delta = float(parts[2])
                if not (1 <= n <= 7):
                    print("joint index must be 1..7")
                    continue
                cur = node.current_deg()
                if cur is None:
                    print("no current state yet")
                    continue
                target = list(cur)
                target[n - 1] += delta
                node.send_target_deg(target)
            elif cmd == "home":
                confirm = input(
                    "Publish all-zeros target? [yes/NO] ")
                if confirm.strip().lower() == "yes":
                    node.send_target_deg([0.0] * 7)
            else:
                print(f"unknown command: {cmd}")
        except Exception as e:
            print(f"[error] {e}")


def main(args=None):
    rclpy.init(args=args)
    node = JointCommanderNode()

    # Spin in a background thread so /joint_states keeps arriving
    # while we block on input().
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