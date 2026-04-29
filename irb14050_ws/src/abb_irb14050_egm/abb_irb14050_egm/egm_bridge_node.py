"""
EGM bridge node for ABB IRB 14050 (7-DOF).

This node is the ONLY thing in the ROS2 graph that talks UDP to the
IRC5. Other ROS2 nodes should interact with the robot through the
topics it exposes:

    Publishes (sensor_msgs/JointState):
        /joint_states    - current joint positions at ~250 Hz
                           (positions in radians, EGM order:
                            J1..J6 then J7 elbow)

    Subscribes (sensor_msgs/JointState):
        /joint_command   - desired joint positions (radians).
                           Only the `position` field is used.
                           Must have 7 values, in the same EGM order
                           as /joint_states.

Internals:
    - RX thread unpacks EgmRobot feedback at ~250 Hz and updates
      self.q_current (deg, internal).
    - TX thread runs at 250 Hz. Each tick it nudges self.q_target
      toward self.q_goal at MAX_SPEED_DEG_S (the original safety
      cap), then packs q_target into EgmSensor and UDP-sends it.
      The TX thread MUST always be sending something, otherwise
      the IRC5 raises ERR_UDPUC_COMM and aborts EGM mode.
    - A /joint_command subscriber updates self.q_goal after a
      joint-limit check. Limits are YuMi (IRB 14000) values, which
      match the IRB 14050 mechanically.

Units:
    ROS side (topics, params): radians (ROS convention).
    EGM wire side:             degrees (what the IRC5 expects).
    Conversion happens only at the boundary.

Parameters:
    egm_rx_port    (int,   default 6511)
    egm_tx_ip      (str,   default "192.168.125.1")
    egm_tx_port    (int,   default 6510)
    send_rate_hz   (float, default 250.0)
    max_speed_deg_s (float, default 5.0)
    joint_names    (str[], default ["joint_1"..."joint_7"])

Typical run order (unchanged from the original toolbox):
    1. Start this node.
    2. Start the RAPID program (egm_joint_irb14050.mod).
"""

import math
import socket
import threading
import time
from typing import List, Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import JointState

from abb_irb14050_egm import egm_pb2


# ---- IRB 14050 joint limits (deg) -------------------------------
# IMPORTANT: these are in EGM WIRE ORDER, not FlexPendant order.
#
#   - On the EGM wire, `joints.joints` carries axis 1..6 in numeric
#     order, and `externalJoints.joints[0]` carries axis 7 (elbow).
#     So index i in this table corresponds to axis (i+1).
#
#   - On the FlexPendant, the IRB 14050 displays axes in PHYSICAL
#     chain order: 1, 2, 7, 3, 4, 5, 6. DO NOT use that order here.
#
# Values taken from the YuMi (IRB 14000) URDFs; the IRB 14050 is
# a single-arm derivative of the YuMi so the mechanical limits
# are the same.
JOINT_LIMITS_DEG = [
    (-168.5, 168.5),  # axis 1  (base rotation)
    (-143.5,  43.5),  # axis 2  (shoulder)
    (-123.5,  80.0),  # axis 3  (upper arm rotation)
    (-290.0, 290.0),  # axis 4
    ( -88.0, 138.0),  # axis 5
    (-229.0, 229.0),  # axis 6  (wrist twist)
    (-168.5, 168.5),  # axis 7  (elbow, external joint)
]


class EGMBridgeNode(Node):

    def __init__(self):
        super().__init__('egm_bridge')

        # ---- parameters ----
        self.declare_parameter('egm_rx_port', 6511)
        self.declare_parameter('egm_tx_ip', '192.168.125.1')
        self.declare_parameter('egm_tx_port', 6510)
        self.declare_parameter('send_rate_hz', 250.0)
        self.declare_parameter('max_speed_deg_s', 5.0)
        self.declare_parameter(
            'joint_names',
            ['joint_1', 'joint_2', 'joint_3', 'joint_4',
             'joint_5', 'joint_6', 'joint_7'])

        self.egm_rx_port = int(
            self.get_parameter('egm_rx_port').value)
        self.egm_tx_ip = str(
            self.get_parameter('egm_tx_ip').value)
        self.egm_tx_port = int(
            self.get_parameter('egm_tx_port').value)
        self.send_rate_hz = float(
            self.get_parameter('send_rate_hz').value)
        self.max_speed_deg_s = float(
            self.get_parameter('max_speed_deg_s').value)
        self.joint_names = list(
            self.get_parameter('joint_names').value)

        if len(self.joint_names) != 7:
            raise ValueError(
                "joint_names must have 7 entries "
                f"(got {len(self.joint_names)})")

        # ---- UDP socket ----
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM)
        self.sock.bind(("", self.egm_rx_port))
        self.sock.settimeout(1.0)

        # ---- shared state ----
        self._lock = threading.Lock()
        # q_current: latest feedback from IRC5 (deg, 7 values)
        self.q_current: Optional[List[float]] = None
        # q_target: what we are sending to IRC5 right now (deg)
        self.q_target: Optional[List[float]] = None
        # q_goal: the final target the user requested (deg)
        self.q_goal: Optional[List[float]] = None
        self.last_seqno = 0
        self._seqno_tx = 0

        # ---- ROS2 publisher / subscriber ----
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10)
        self.js_pub = self.create_publisher(
            JointState, 'joint_states', qos)
        self.cmd_sub = self.create_subscription(
            JointState, 'joint_command',
            self._on_command, qos)

        # ---- background threads ----
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._tx_thread: Optional[threading.Thread] = None

        self.get_logger().info(
            f"EGM bridge starting: RX :{self.egm_rx_port}, "
            f"TX {self.egm_tx_ip}:{self.egm_tx_port}, "
            f"{self.send_rate_hz:.0f} Hz, "
            f"max speed {self.max_speed_deg_s:.1f} deg/s")

    # ---------- lifecycle ----------

    def start(self):
        """Wait for first feedback packet, then start RX/TX threads."""
        self.get_logger().info(
            "Waiting for first EGM feedback packet "
            "(is the RAPID program running?)")
        self._wait_for_first_feedback()
        assert self.q_current is not None

        # Sanity-check that the initial pose is within limits. If
        # it isn't, warn loudly (we still seed from it so the TX
        # loop stays alive) but something is off — either the
        # pose is near a limit or the table is wrong.
        self._warn_if_out_of_limits(self.q_current)

        # Seed target and goal from current, so the robot "holds"
        # until a command comes in.
        with self._lock:
            self.q_target = list(self.q_current)
            self.q_goal = list(self.q_current)
        self.get_logger().info(
            f"Initial q (deg) = {self._fmt_q(self.q_current)}")

        self._running = True
        self._rx_thread = threading.Thread(
            target=self._rx_loop, daemon=True,
            name='egm_rx')
        self._tx_thread = threading.Thread(
            target=self._tx_loop, daemon=True,
            name='egm_tx')
        self._rx_thread.start()
        self._tx_thread.start()
        self.get_logger().info("EGM RX/TX threads running")

    def shutdown(self):
        self._running = False
        time.sleep(0.1)
        try:
            self.sock.close()
        except OSError:
            pass
        self.get_logger().info("EGM bridge stopped")

    # ---------- ROS callbacks ----------

    def _on_command(self, msg: JointState):
        """
        Handle /joint_command. Only msg.position is used.
        Expected: 7 values in EGM order (axes 1..6, then 7), radians.
        """
        if len(msg.position) != 7:
            self.get_logger().warning(
                f"Ignoring /joint_command: expected 7 positions, "
                f"got {len(msg.position)}")
            return

        # ROS -> internal: rad -> deg
        q_goal_deg = [math.degrees(p) for p in msg.position]

        try:
            self._check_limits(q_goal_deg)
        except ValueError as e:
            self.get_logger().warning(
                f"Ignoring /joint_command: {e}")
            return

        with self._lock:
            self.q_goal = q_goal_deg

        self.get_logger().info(
            f"New goal (deg): {self._fmt_q(q_goal_deg)}")

    # ---------- UDP threads ----------

    def _wait_for_first_feedback(self, timeout_s: float = 30.0):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            msg = egm_pb2.EgmRobot()
            try:
                msg.ParseFromString(data)
            except Exception as e:
                self.get_logger().warning(
                    f"Parse error on first packet: {e}")
                continue
            q = list(msg.feedBack.joints.joints)
            e = list(msg.feedBack.externalJoints.joints)
            if len(q) == 6 and len(e) >= 1:
                with self._lock:
                    self.q_current = q + [e[0]]
                    self.last_seqno = msg.header.seqno
                return
        raise TimeoutError(
            "No valid EGM feedback received. "
            "Is RAPID running? Is UC_DEVICE pointing at this host?")

    def _rx_loop(self):
        while self._running:
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            msg = egm_pb2.EgmRobot()
            try:
                msg.ParseFromString(data)
            except Exception as e:
                self.get_logger().warning(f"[rx] parse error: {e}")
                continue
            q = list(msg.feedBack.joints.joints)
            e = list(msg.feedBack.externalJoints.joints)
            if len(q) == 6 and len(e) >= 1:
                q_full = q + [e[0]]
                with self._lock:
                    self.q_current = q_full
                    self.last_seqno = msg.header.seqno
                self._publish_joint_state(q_full)

    def _tx_loop(self):
        """
        At 250 Hz, slew q_target toward q_goal at max_speed_deg_s
        and send q_target to the IRC5. Even when q_target == q_goal
        we keep sending, otherwise the IRC5 times out.
        """
        period = 1.0 / self.send_rate_hz
        step_per_tick = self.max_speed_deg_s / self.send_rate_hz
        next_t = time.time()

        while self._running:
            with self._lock:
                if (self.q_goal is not None
                        and self.q_target is not None):
                    delta = (np.asarray(self.q_goal)
                             - np.asarray(self.q_target))
                    max_abs = float(np.max(np.abs(delta)))
                    if max_abs > step_per_tick:
                        scale = step_per_tick / max_abs
                        self.q_target = (
                            np.asarray(self.q_target)
                            + delta * scale).tolist()
                    else:
                        # close enough, snap to goal
                        self.q_target = list(self.q_goal)
                q_to_send = (list(self.q_target)
                             if self.q_target else None)

            if q_to_send is not None:
                try:
                    self._send_target(q_to_send)
                except OSError:
                    # socket closed on shutdown
                    break

            next_t += period
            sleep_for = next_t - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                # fell behind; resync
                next_t = time.time()

    def _send_target(self, q_deg: List[float]):
        """Pack q (7 values, deg) into EgmSensor and UDP-send."""
        msg = egm_pb2.EgmSensor()

        self._seqno_tx += 1
        msg.header.mtype = egm_pb2.EgmHeader.MessageType.Value(
            "MSGTYPE_CORRECTION")
        msg.header.seqno = self._seqno_tx
        msg.header.tm = int(time.time() * 1000) & 0xFFFFFFFF

        # 6 arm joints
        msg.planned.joints.joints.extend(q_deg[:6])
        # 7th joint (elbow) as external joint
        msg.planned.externalJoints.joints.append(q_deg[6])

        self.sock.sendto(msg.SerializeToString(),
                         (self.egm_tx_ip, self.egm_tx_port))

    # ---------- helpers ----------

    def _publish_joint_state(self, q_deg: List[float]):
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = self.joint_names
        # internal -> ROS: deg -> rad
        js.position = [math.radians(v) for v in q_deg]
        self.js_pub.publish(js)

    def _check_limits(self, q_deg: List[float]):
        for i, (qv, (lo, hi)) in enumerate(
                zip(q_deg, JOINT_LIMITS_DEG)):
            if not (lo <= qv <= hi):
                raise ValueError(
                    f"axis {i+1} target {qv:.2f} deg outside "
                    f"limits [{lo:.1f}, {hi:.1f}]")

    def _warn_if_out_of_limits(self, q_deg: List[float]):
        for i, (qv, (lo, hi)) in enumerate(
                zip(q_deg, JOINT_LIMITS_DEG)):
            if not (lo <= qv <= hi):
                self.get_logger().warning(
                    f"Initial pose axis {i+1} = {qv:.2f} deg is "
                    f"outside configured limits [{lo:.1f}, "
                    f"{hi:.1f}]. Commands will be rejected until "
                    f"the robot moves back inside the range, or "
                    f"the limit table is fixed.")

    @staticmethod
    def _fmt_q(q):
        return "[" + ", ".join(f"{v:+7.2f}" for v in q) + "]"


def main(args=None):
    rclpy.init(args=args)
    node = EGMBridgeNode()
    try:
        node.start()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f"Fatal: {e}")
        raise
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()