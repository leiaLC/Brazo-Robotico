#!/usr/bin/env python3
"""Bridge robot_interfaces/DetectedObjectCloudArray to robot_task_msgs/Detection3D."""

from __future__ import annotations

import re

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from robot_task_msgs.msg import Detection3D

try:
    from robot_interfaces.msg import DetectedObjectCloudArray
except ImportError:  # pragma: no cover - only available when ABB workspace is sourced.
    DetectedObjectCloudArray = None


COLOR_WORDS = {
    "blue": "blue",
    "azul": "blue",
    "red": "red",
    "rojo": "red",
    "roja": "red",
    "green": "green",
    "verde": "green",
    "yellow": "yellow",
    "amarillo": "yellow",
    "amarilla": "yellow",
    "pink": "pink",
    "rosa": "pink",
    "rosado": "pink",
    "rosada": "pink",
}

CLASS_ALIASES = {
    "cubo": "cube",
    "cube": "cube",
    "cilindro": "cylinder",
    "cylinder": "cylinder",
    "hexagono": "hexagon",
    "hexágono": "hexagon",
    "hexagon": "hexagon",
    "toroide": "toroid",
    "toroid": "toroid",
    "manzana": "apple",
    "apple": "apple",
    "mano": "hand",
    "hand": "hand",
    "left": "hand",
    "right": "hand",
}


class ObjectCloudBridge(Node):
    """Convert the team's pointcloud detections into this tree's Detection3D API."""

    def __init__(self) -> None:
        super().__init__("object_cloud_bridge")
        if DetectedObjectCloudArray is None:
            raise RuntimeError(
                "robot_interfaces is not available. Source/build the ABB workspace "
                "before launching object_cloud_bridge."
            )

        self.declare_parameter("input_topic", "/perception/object_clouds")
        self.declare_parameter("output_topic", "/perception/detections_3d")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("input_is_base_frame", False)
        self.declare_parameter("publish_centroid_tf", True)
        self.declare_parameter("centroid_tf_prefix", "object_centroid")
        self.declare_parameter("centroid_tf_use_label", False)

        input_topic = str(self.get_parameter("input_topic").value)
        output_topic = str(self.get_parameter("output_topic").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.input_is_base_frame = bool(self.get_parameter("input_is_base_frame").value)
        self.publish_centroid_tf = bool(self.get_parameter("publish_centroid_tf").value)
        self.centroid_tf_prefix = str(self.get_parameter("centroid_tf_prefix").value)
        self.centroid_tf_use_label = bool(self.get_parameter("centroid_tf_use_label").value)

        self.pub = self.create_publisher(Detection3D, output_topic, 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.sub = self.create_subscription(
            DetectedObjectCloudArray,
            input_topic,
            self._callback,
            10,
        )
        self.get_logger().info(f"Bridging {input_topic} -> {output_topic}")

    def _callback(self, msg) -> None:
        valid_objects = [obj for obj in msg.objects if obj.centroid_valid]
        object_count = len(valid_objects)

        for index, obj in enumerate(valid_objects):
            detection = Detection3D()
            detection.header = obj.header
            detection.class_name, detection.color = self._split_label(obj.label)
            detection.confidence = float(obj.confidence)
            detection.bbox_x = int(obj.bbox_x1)
            detection.bbox_y = int(obj.bbox_y1)
            detection.bbox_width = max(0, int(obj.bbox_x2 - obj.bbox_x1))
            detection.bbox_height = max(0, int(obj.bbox_y2 - obj.bbox_y1))
            detection.pose_camera = self._pose_from_centroid(obj.header, obj)
            detection.has_valid_depth = True

            if self.input_is_base_frame or obj.header.frame_id == self.base_frame:
                detection.pose_base = self._pose_from_centroid(obj.header, obj)
                detection.pose_base.header.frame_id = self.base_frame

            self.pub.publish(detection)
            self._publish_centroid_tf(obj, index, object_count)

    def _pose_from_centroid(self, header, obj) -> PoseStamped:
        pose = PoseStamped()
        pose.header = header
        pose.pose.position.x = float(obj.centroid_x)
        pose.pose.position.y = float(obj.centroid_y)
        pose.pose.position.z = float(obj.centroid_z)
        pose.pose.orientation.w = 1.0
        return pose

    def _publish_centroid_tf(self, obj, index: int, object_count: int) -> None:
        if not self.publish_centroid_tf:
            return

        parent_frame = obj.header.frame_id.strip()
        if not parent_frame:
            self.get_logger().warn(
                "Skipping centroid TF because detection header.frame_id is empty",
                throttle_duration_sec=2.0,
            )
            return

        transform = TransformStamped()
        transform.header = obj.header
        transform.header.frame_id = parent_frame
        transform.child_frame_id = self._centroid_child_frame(obj.label, index, object_count)
        transform.transform.translation.x = float(obj.centroid_x)
        transform.transform.translation.y = float(obj.centroid_y)
        transform.transform.translation.z = float(obj.centroid_z)
        transform.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(transform)

    def _centroid_child_frame(self, label: str, index: int, object_count: int) -> str:
        frame = self._sanitize_frame_id(self.centroid_tf_prefix) or "object_centroid"

        if self.centroid_tf_use_label:
            label_frame = self._sanitize_frame_id(label)
            if label_frame:
                frame = f"{frame}_{label_frame}"

        if object_count > 1:
            frame = f"{frame}_{index}"

        return frame

    @staticmethod
    def _sanitize_frame_id(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_").lower()

    @staticmethod
    def _split_label(label: str) -> tuple[str, str]:
        tokens = re.split(r"[\s_-]+", label.lower().strip())
        color = ""
        class_name = label.lower().strip()
        for token in tokens:
            if token in COLOR_WORDS:
                color = COLOR_WORDS[token]
            if token in CLASS_ALIASES:
                class_name = CLASS_ALIASES[token]
        return class_name, color


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ObjectCloudBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
