"""
Simple /joint_states listener.

Prints the 7 joint positions in both radians (what's on the wire)
and degrees (what the datasheet and RobotStudio use), at a
throttled rate so the terminal stays readable.
"""

import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


PRINT_EVERY_N = 25  # 250 Hz / 25 = ~10 prints per second


class JointStateListenerNode(Node):

    def __init__(self):
        super().__init__('joint_listener')
        self.sub = self.create_subscription(
            JointState, 'joint_states', self._on_state, 10)
        self._count = 0
        self._t0 = time.time()

    def _on_state(self, msg: JointState):
        self._count += 1
        if self._count % PRINT_EVERY_N != 0:
            return
        rate_hz = self._count / max(time.time() - self._t0, 1e-6)
        pos_rad = list(msg.position)
        pos_deg = [math.degrees(p) for p in pos_rad]
        deg_str = "[" + ", ".join(
            f"{v:+7.2f}" for v in pos_deg) + "]"
        self.get_logger().info(
            f"q (deg) = {deg_str}   avg rate = {rate_hz:5.1f} Hz")


def main(args=None):
    rclpy.init(args=args)
    node = JointStateListenerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
