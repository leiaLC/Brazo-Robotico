#!/usr/bin/env python3
"""
gripper_node.py
ROS2 node for SmartGripper control via RWS IO signals.

Topics:
  /gripper/command  (std_msgs/String, in)
      Accepts: "open" | "close" | "standby"
  /gripper/state    (std_msgs/String, out)
      Periodic snapshot of gripper status (cmd/position/speed/etc.)

Parameters:
  host             (str, default '192.168.125.1') - OmniCore IP
  user             (str, default 'Default User')
  password         (str, default 'robotics')
  publish_rate_hz  (double, default 2.0)

Runs independently of the EGM bridge. EGM (UDP) controls the arm, this
node (HTTPS/RWS) controls the gripper. Both can run simultaneously.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# Same package — gripper_rws.py lives alongside this file under
# src/abb_irb14050_egm/abb_irb14050_egm/
from abb_irb14050_egm.gripper_rws import SmartGripperIO


class GripperNode(Node):
    def __init__(self):
        super().__init__('gripper_node')

        # Parameters
        self.declare_parameter('host', '192.168.125.1')
        self.declare_parameter('user', 'Default User')
        self.declare_parameter('password', 'robotics')
        self.declare_parameter('publish_rate_hz', 2.0)

        host = self.get_parameter('host').get_parameter_value().string_value
        user = self.get_parameter('user').get_parameter_value().string_value
        passwd = self.get_parameter('password').get_parameter_value().string_value
        rate = self.get_parameter('publish_rate_hz').get_parameter_value().double_value

        # RWS client
        self.gripper = SmartGripperIO(host=host, user=user, password=passwd)

        # Subscriber: commands
        self.cmd_sub = self.create_subscription(
            String, '/gripper/command', self._on_command, 10
        )

        # Publisher: state
        self.state_pub = self.create_publisher(String, '/gripper/state', 10)
        self.state_timer = self.create_timer(
            max(0.1, 1.0 / rate), self._publish_state
        )

        self.get_logger().info(
            f"Gripper node up. RWS host={host}. "
            f"Publishing /gripper/state at {rate:.1f} Hz. "
            f"Commands: ros2 topic pub --once /gripper/command "
            f"std_msgs/String \"data: open\""
        )

    # --- callbacks --------------------------------------------------

    def _on_command(self, msg: String):
        cmd = msg.data.strip().lower()
        if cmd == 'open':
            ok = self.gripper.open()
            self.get_logger().info(f"OPEN -> {ok}")
        elif cmd == 'close':
            ok = self.gripper.close()
            self.get_logger().info(f"CLOSE -> {ok}")
        elif cmd == 'standby':
            ok = self.gripper.standby()
            self.get_logger().info(f"STANDBY -> {ok}")
        else:
            self.get_logger().warn(
                f"Unknown gripper command '{msg.data}'. "
                f"Use 'open' | 'close' | 'standby'."
            )

    def _publish_state(self):
        s = self.gripper.status()
        # If RWS read failed, all values will be None — log once and skip
        if s.get('cmd') is None:
            self.get_logger().warn(
                "Gripper status read failed (RWS unreachable?)",
                throttle_duration_sec=5.0,
            )
            return
        out = String()
        out.data = (
            f"cmd={s['cmd']}, position={s['position']}, "
            f"speed={s['speed']}, error={s['error']}, "
            f"calibrated={s['calibrated']}, "
            f"pressure_1={s['pressure_1']}"
        )
        self.state_pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = GripperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
