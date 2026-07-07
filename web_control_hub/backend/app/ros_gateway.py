import math
import json
import threading
import time
from dataclasses import dataclass
from typing import Callable

try:
    import cv2
    import numpy as np
    import rclpy
    from cv_bridge import CvBridge
    from geometry_msgs.msg import Twist
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from sensor_msgs.msg import CompressedImage, Image, JointState
    from std_msgs.msg import Empty, String
    from robot_task_msgs.msg import RobotCommand, RobotStatus
except ImportError as exc:  # pragma: no cover - useful when edited outside ROS2 env
    cv2 = None
    np = None
    rclpy = None
    CvBridge = None
    Twist = None
    Node = object
    JointState = None
    Image = None
    CompressedImage = None
    Empty = None
    String = None
    RobotCommand = None
    RobotStatus = None
    ExternalShutdownException = Exception
    ROS_IMPORT_ERROR = exc
else:
    ROS_IMPORT_ERROR = None

from app.config import Settings


@dataclass
class JointSnapshot:
    names: list[str]
    positions_rad: list[float]
    count: int


class RosGateway:
    def __init__(self, settings: Settings):
        if ROS_IMPORT_ERROR is not None:
            raise RuntimeError(
                "ROS2 Python modules are not available. Run this backend in a sourced ROS2 "
                "environment and create the venv with --system-site-packages."
            ) from ROS_IMPORT_ERROR

        self.settings = settings
        self.node: Node | None = None
        self.task_command_pub = None
        self.sequence_pub = None
        self.teleop_twist_pub = None
        self.voice_text_pub = None
        self.voice_start_pub = None
        self._spin_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._teleop_enabled = False
        self._snapshot: JointSnapshot | None = None
        self._latest_jpeg: bytes | None = None
        self._latest_task_status: dict | None = None
        self._latest_jetson_metrics: dict | None = None
        self._latest_jetson_metrics_received_at: float | None = None
        self._latest_voice_status: dict = {"status": "unknown"}
        self._voice_events: list[dict] = []
        self._state_callbacks: list[Callable[[JointSnapshot], None]] = []
        self._task_status_callbacks: list[Callable[[dict], None]] = []
        self._voice_status_callbacks: list[Callable[[dict], None]] = []
        self._voice_event_callbacks: list[Callable[[dict], None]] = []
        self._bridge = CvBridge() if CvBridge is not None else None

    def start(self) -> None:
        if not rclpy.ok():
            rclpy.init()

        self.node = rclpy.create_node("yumi_web_gateway")
        self.task_command_pub = self.node.create_publisher(RobotCommand, self.settings.command_topic, 10)
        self.sequence_pub = self.node.create_publisher(String, self.settings.sequence_topic, 10)
        self.teleop_twist_pub = self.node.create_publisher(Twist, self.settings.teleop_twist_topic, 10)
        self.voice_text_pub = self.node.create_publisher(String, self.settings.voice_text_topic, 10)
        self.voice_start_pub = self.node.create_publisher(Empty, self.settings.voice_start_topic, 10)
        self.node.create_subscription(JointState, self.settings.state_topic, self._on_joint_state, 10)
        self.node.create_subscription(RobotStatus, "/robot_task/status", self._on_task_status, 10)
        self.node.create_subscription(String, self.settings.jetson_metrics_topic, self._on_jetson_metrics, 10)
        self.node.create_subscription(String, self.settings.voice_status_topic, self._on_voice_status, 10)
        self.node.create_subscription(String, self.settings.voice_events_topic, self._on_voice_event, 10)

        image_msg_type = CompressedImage if self.settings.image_is_compressed else Image
        self.node.create_subscription(image_msg_type, self.settings.image_topic, self._on_image, 10)

        self._spin_thread = threading.Thread(target=self._spin, args=(self.node,), daemon=True)
        self._spin_thread.start()

    def stop(self) -> None:
        if self.node is not None:
            self.node.destroy_node()
            self.node = None
        if rclpy.ok():
            rclpy.shutdown()
        if self._spin_thread is not None:
            self._spin_thread.join(timeout=2.0)
            self._spin_thread = None

    def _spin(self, node: Node) -> None:
        try:
            rclpy.spin(node)
        except ExternalShutdownException:
            pass

    def enable_teleop(self) -> None:
        with self._lock:
            self._teleop_enabled = True

    def disable_teleop(self) -> None:
        with self._lock:
            self._teleop_enabled = False

    def is_teleop_enabled(self) -> bool:
        with self._lock:
            return self._teleop_enabled

    def get_snapshot(self) -> JointSnapshot | None:
        with self._lock:
            return self._snapshot

    def get_latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg

    def get_latest_task_status(self) -> dict | None:
        with self._lock:
            return self._latest_task_status

    def get_latest_jetson_metrics(self, max_age_sec: float) -> dict | None:
        with self._lock:
            if self._latest_jetson_metrics is None or self._latest_jetson_metrics_received_at is None:
                return None
            if time.monotonic() - self._latest_jetson_metrics_received_at > max_age_sec:
                return None
            return dict(self._latest_jetson_metrics)

    def get_latest_voice_status(self) -> dict:
        with self._lock:
            return dict(self._latest_voice_status)

    def get_voice_events(self) -> list[dict]:
        with self._lock:
            return list(self._voice_events)

    def get_required_node_statuses(self) -> list[dict]:
        if self.node is None:
            raise RuntimeError("ROS gateway is not started")

        discovered_nodes = {
            self._fully_qualified_node_name(name, namespace)
            for name, namespace in self.node.get_node_names_and_namespaces()
        }

        return [
            {
                "name": configured_name,
                "active": self._is_node_active(configured_name, discovered_nodes),
            }
            for configured_name in self.settings.required_ros_nodes
        ]

    def add_state_callback(self, callback: Callable[[JointSnapshot], None]) -> None:
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[JointSnapshot], None]) -> None:
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def add_task_status_callback(self, callback: Callable[[dict], None]) -> None:
        self._task_status_callbacks.append(callback)

    def remove_task_status_callback(self, callback: Callable[[dict], None]) -> None:
        if callback in self._task_status_callbacks:
            self._task_status_callbacks.remove(callback)

    def add_voice_status_callback(self, callback: Callable[[dict], None]) -> None:
        self._voice_status_callbacks.append(callback)

    def remove_voice_status_callback(self, callback: Callable[[dict], None]) -> None:
        if callback in self._voice_status_callbacks:
            self._voice_status_callbacks.remove(callback)

    def add_voice_event_callback(self, callback: Callable[[dict], None]) -> None:
        self._voice_event_callbacks.append(callback)

    def remove_voice_event_callback(self, callback: Callable[[dict], None]) -> None:
        if callback in self._voice_event_callbacks:
            self._voice_event_callbacks.remove(callback)

    def publish_joint_target_deg(self, positions_deg: list[float]) -> None:
        self._validate_target(positions_deg)

        with self._lock:
            enabled = self._teleop_enabled

        if not enabled:
            raise PermissionError("teleoperation is disabled")

        if self.task_command_pub is None or self.node is None:
            raise RuntimeError("ROS gateway is not started")

        command = self._base_robot_command()
        command.command_type = "MOVE_JOINT"
        command.joint_values = [float(value) for value in positions_deg]
        command.relative = False
        command.priority = 94.0
        self.task_command_pub.publish(command)

    def publish_teleop_twist(self, linear: tuple[float, float, float], angular: tuple[float, float, float]) -> None:
        with self._lock:
            enabled = self._teleop_enabled

        if not enabled:
            raise PermissionError("teleoperation is disabled")

        if self.teleop_twist_pub is None or self.node is None:
            raise RuntimeError("ROS gateway is not started")

        twist = Twist()
        twist.linear.x, twist.linear.y, twist.linear.z = linear
        twist.angular.x, twist.angular.y, twist.angular.z = angular
        self.teleop_twist_pub.publish(twist)

    def publish_gripper_sequence(self, command: str) -> None:
        with self._lock:
            enabled = self._teleop_enabled

        if not enabled:
            raise PermissionError("teleoperation is disabled")

        normalized = command.strip().lower()
        if normalized not in {"open", "close"}:
            raise ValueError("gripper command must be 'open' or 'close'")

        self.publish_sequence(f"{normalized}_gripper")

    def publish_sequence(self, sequence_id: str) -> None:
        if self.sequence_pub is None:
            raise RuntimeError("ROS gateway is not started")
        msg = String()
        msg.data = sequence_id.strip()
        if not msg.data:
            raise ValueError("sequence_id cannot be empty")
        self.sequence_pub.publish(msg)

    def publish_voice_text(self, text: str) -> None:
        if self.voice_text_pub is None:
            raise RuntimeError("ROS gateway is not started")
        msg = String()
        msg.data = text.strip()
        if not msg.data:
            raise ValueError("text cannot be empty")
        self.voice_text_pub.publish(msg)

    def publish_voice_start(self) -> None:
        if self.voice_start_pub is None:
            raise RuntimeError("ROS gateway is not started")
        self.voice_start_pub.publish(Empty())

    def publish_task_command(self, command_type: str) -> None:
        if self.task_command_pub is None or self.node is None:
            raise RuntimeError("ROS gateway is not started")
        command = self._base_robot_command()
        command.command_type = command_type
        command.priority = 100.0 if command_type in {"CANCEL", "ESTOP"} else 90.0
        self.task_command_pub.publish(command)

    def _validate_target(self, positions_deg: list[float]) -> None:
        if len(positions_deg) != 7:
            raise ValueError("expected exactly 7 joint values")

        for index, value in enumerate(positions_deg):
            lower, upper = self.settings.joint_limits_deg[index]
            if value < lower or value > upper:
                raise ValueError(
                    f"joint {index + 1} out of limits: {value:.2f} deg not in [{lower}, {upper}]"
                )

    @staticmethod
    def _fully_qualified_node_name(name: str, namespace: str) -> str:
        return f"/{namespace.strip('/')}/{name}".replace("//", "/")

    @staticmethod
    def _is_node_active(configured_name: str, discovered_nodes: set[str]) -> bool:
        normalized_name = f"/{configured_name.strip('/')}"
        if configured_name.startswith("/"):
            return normalized_name in discovered_nodes

        return any(
            node_name.rsplit("/", maxsplit=1)[-1] == configured_name
            for node_name in discovered_nodes
        )

    def _base_robot_command(self):
        command = RobotCommand()
        command.header.stamp = self.node.get_clock().now().to_msg()
        command.header.frame_id = "yumi_web_gateway"
        command.source = "web"
        return command

    def _on_joint_state(self, msg: JointState) -> None:
        positions_by_name = {
            name: position for name, position in zip(msg.name, msg.position)
        }
        if not positions_by_name:
            return
        try:
            positions = [positions_by_name[name] for name in self.settings.joint_names]
        except KeyError:
            return

        with self._lock:
            count = 1 if self._snapshot is None else self._snapshot.count + 1
            snapshot = JointSnapshot(
                names=self.settings.joint_names,
                positions_rad=list(positions),
                count=count,
            )
            self._snapshot = snapshot

        for callback in list(self._state_callbacks):
            callback(snapshot)

    def _on_task_status(self, msg) -> None:
        status = {
            "mode": msg.mode,
            "current_task": msg.current_task,
            "message": msg.message,
            "robot_ready": msg.robot_ready,
            "arm_busy": msg.arm_busy,
            "estop_active": msg.estop_active,
            "teleop_active": msg.teleop_active,
            "progress": float(msg.progress),
            "error_code": msg.error_code,
        }
        with self._lock:
            self._latest_task_status = status

        for callback in list(self._task_status_callbacks):
            callback(status)

    def _on_jetson_metrics(self, msg: String) -> None:
        try:
            metrics = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if not isinstance(metrics, dict):
            return

        metrics.setdefault("source", "ros2")
        with self._lock:
            self._latest_jetson_metrics = metrics
            self._latest_jetson_metrics_received_at = time.monotonic()

    def _on_voice_status(self, msg: String) -> None:
        status = {"status": msg.data}
        with self._lock:
            self._latest_voice_status = status

        for callback in list(self._voice_status_callbacks):
            callback(status)

    def _on_voice_event(self, msg: String) -> None:
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            event = {"type": "message", "text": msg.data, "confidence": None}

        with self._lock:
            self._voice_events.append(event)
            self._voice_events = self._voice_events[-25:]

        for callback in list(self._voice_event_callbacks):
            callback(event)

    def _on_image(self, msg) -> None:
        if cv2 is None:
            return

        try:
            if self.settings.image_is_compressed:
                data = np.frombuffer(msg.data, dtype=np.uint8)
                frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            else:
                if self._bridge is None:
                    return
                frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if not ok:
                return

            with self._lock:
                self._latest_jpeg = encoded.tobytes()
        except Exception:
            # Keep the gateway alive even when a camera frame has an unexpected encoding.
            return
