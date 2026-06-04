#!/usr/bin/env python3
"""Capture RealSense RGB frames for YOLO dataset collection."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class DatasetCaptureNode(Node):
    """Preview an RGB image topic and save a frame on left mouse click."""

    def __init__(self):
        super().__init__("dataset_capture_node")

        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("output_dir", "~/robot_yolo_dataset/realsense_435i/images")
        self.declare_parameter("filename_prefix", "realsense_435i")
        self.declare_parameter("window_name", "YOLO dataset capture")
        self.declare_parameter("jpg_quality", 95)
        self.declare_parameter("preview_width", 960)

        self.image_topic = str(self.get_parameter("image_topic").value)
        self.output_dir = Path(str(self.get_parameter("output_dir").value)).expanduser()
        self.filename_prefix = str(self.get_parameter("filename_prefix").value)
        self.window_name = str(self.get_parameter("window_name").value)
        self.jpg_quality = int(self.get_parameter("jpg_quality").value)
        self.preview_width = int(self.get_parameter("preview_width").value)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.bridge = CvBridge()
        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_stamp = None
        self._save_count = 0
        self._last_saved_path: Path | None = None
        self._capture_requested = False

        self.create_subscription(Image, self.image_topic, self._on_image, 10)
        self.create_timer(1.0 / 30.0, self._show_preview)

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self._on_mouse)

        self.get_logger().info(
            "Dataset capture ready. "
            f"Topic={self.image_topic} | output_dir={self.output_dir}. "
            "Left-click the preview window to save an image."
        )

    def _on_image(self, msg: Image) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:  # noqa: BLE001 - keep capture node alive.
            self.get_logger().warn(f"Could not convert image: {exc}")
            return

        with self._lock:
            self._latest_frame = frame.copy()
            self._latest_stamp = msg.header.stamp

    def _on_mouse(self, event, _x, _y, _flags, _userdata) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            with self._lock:
                self._capture_requested = True

    def _show_preview(self) -> None:
        with self._lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()
            capture_requested = self._capture_requested
            self._capture_requested = False

        if frame is None:
            return

        if capture_requested:
            self._save_frame(frame)

        preview = self._preview_frame(frame)
        cv2.imshow(self.window_name, preview)
        cv2.waitKey(1)

    def _preview_frame(self, frame):
        preview = frame
        if self.preview_width > 0 and frame.shape[1] > self.preview_width:
            scale = self.preview_width / frame.shape[1]
            height = max(1, int(frame.shape[0] * scale))
            preview = cv2.resize(frame, (self.preview_width, height), interpolation=cv2.INTER_AREA)

        preview = preview.copy()
        status = f"saved: {self._save_count} | click to capture"
        cv2.putText(
            preview,
            status,
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        if self._last_saved_path is not None:
            cv2.putText(
                preview,
                self._last_saved_path.name,
                (12, 58),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
        return preview

    def _save_frame(self, frame) -> None:
        self._save_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.filename_prefix}_{timestamp}_{self._save_count:05d}.jpg"
        path = self.output_dir / filename

        ok = cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpg_quality])
        if not ok:
            self.get_logger().error(f"Could not save image: {path}")
            return

        self._last_saved_path = path
        self.get_logger().info(f"Saved image {self._save_count}: {path}")

    def destroy_node(self) -> bool:
        cv2.destroyWindow(self.window_name)
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DatasetCaptureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
