#!/usr/bin/env python3
"""Mock YOLO + depth detector publishing Detection3D messages."""

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node

from robot_task_msgs.msg import Detection3D


def make_pose(frame_id: str, x: float, y: float, z: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.position.z = z
    pose.pose.orientation.w = 1.0
    return pose


class MockYoloDetector(Node):
    """Publish stable mock detections for integration testing."""

    def __init__(self) -> None:
        super().__init__("mock_yolo_detector")
        self.declare_parameter("mock_mode", True)
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("camera_frame", "camera_depth_frame")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("publish_hz", 2.0)

        self.mock_mode = bool(self.get_parameter("mock_mode").value)
        self.confidence_threshold = float(self.get_parameter("confidence_threshold").value)
        self.camera_frame = str(self.get_parameter("camera_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        publish_hz = max(0.1, float(self.get_parameter("publish_hz").value))

        self.pub = self.create_publisher(Detection3D, "/perception/detections_3d", 10)
        self.timer = self.create_timer(1.0 / publish_hz, self._publish_detections)
        self.get_logger().info("mock_yolo_detector publishing /perception/detections_3d")

    def _publish_detections(self) -> None:
        if not self.mock_mode:
            return
        stamp = self.get_clock().now().to_msg()
        for detection in self._detections(stamp):
            if detection.confidence >= self.confidence_threshold:
                self.pub.publish(detection)

    def _detections(self, stamp) -> list[Detection3D]:
        cube = Detection3D()
        cube.header.stamp = stamp
        cube.header.frame_id = self.camera_frame
        cube.class_name = "cube"
        cube.color = "blue"
        cube.confidence = 0.92
        cube.bbox_x = 120
        cube.bbox_y = 80
        cube.bbox_width = 70
        cube.bbox_height = 70
        cube.pose_camera = make_pose(self.camera_frame, 0.40, 0.10, 0.20)
        cube.pose_base = make_pose(self.base_frame, 0.40, 0.10, 0.20)
        cube.has_valid_depth = True

        bottle = Detection3D()
        bottle.header.stamp = stamp
        bottle.header.frame_id = self.camera_frame
        bottle.class_name = "bottle"
        bottle.color = "red"
        bottle.confidence = 0.88
        bottle.bbox_x = 260
        bottle.bbox_y = 95
        bottle.bbox_width = 45
        bottle.bbox_height = 110
        bottle.pose_camera = make_pose(self.camera_frame, 0.50, -0.10, 0.20)
        bottle.pose_base = make_pose(self.base_frame, 0.50, -0.10, 0.20)
        bottle.has_valid_depth = True
        return [cube, bottle]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockYoloDetector()
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
