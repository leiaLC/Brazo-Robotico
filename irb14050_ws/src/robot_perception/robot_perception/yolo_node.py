#!/usr/bin/env python3
"""
yolo_node — robot_perception
==============================
Corre YOLOv8-seg sobre el frame RGB undistorsionado y publica
DetectedObjectArray con bbox 2D + máscara de segmentación.

NO calcula profundidad — eso es responsabilidad de depth_estimator_node.

Topics suscritos:
    /perception/rgb              (sensor_msgs/Image)

Topics publicados:
    /perception/detections       (robot_interfaces/DetectedObjectArray)
    /perception/yolo/debug_image (sensor_msgs/Image)
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

from robot_interfaces.msg import DetectedObject, DetectedObjectArray


class YoloNode(Node):

    def __init__(self):
        super().__init__('yolo_node')

        # ── Parámetros ───────────────────────────────────────────────────
        self.declare_parameter('model_path', 'yolov8n-seg.pt')
        self.declare_parameter('confidence', 0.5)
        self.declare_parameter('device',     'cpu')

        self.declare_parameter('fx', 699.67550943)
        self.declare_parameter('fy', 698.43830325)
        self.declare_parameter('cx', 353.68978922)
        self.declare_parameter('cy', 228.14941822)
        self.declare_parameter(
            'distortion',
            [0.36707075, -0.10014484, -0.01481674, 0.03724342, 10.61119071]
        )

        model_path = self.get_parameter('model_path').value
        self.conf  = self.get_parameter('confidence').value
        device     = self.get_parameter('device').value

        fx   = self.get_parameter('fx').value
        fy   = self.get_parameter('fy').value
        cx_  = self.get_parameter('cx').value
        cy_  = self.get_parameter('cy').value
        dist = self.get_parameter('distortion').value

        # ── Matrices de cámara ───────────────────────────────────────────
        self.camera_matrix = np.array([
            [fx,  0.0, cx_],
            [0.0, fy,  cy_],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        self.dist_coeffs       = np.array(dist, dtype=np.float64)
        self.new_camera_matrix = None
        self.roi               = None

        # ── YOLO ─────────────────────────────────────────────────────────
        self.model = YOLO(model_path)
        self.model.to(device)

        if 'seg' not in model_path:
            self.get_logger().warn(
                f'El modelo "{model_path}" no parece ser -seg. '
                'Usa yolov8n-seg.pt, yolov8s-seg.pt, etc.'
            )

        self.bridge = CvBridge()

        # ── Subscriber directo — sin sincronizador ───────────────────────
        self.create_subscription(Image, '/perception/rgb', self.callback, 10)

        # ── Publishers ───────────────────────────────────────────────────
        self.det_pub   = self.create_publisher(DetectedObjectArray, '/perception/detections',       10)
        self.debug_pub = self.create_publisher(Image,               '/perception/yolo/debug_image', 10)

        self.get_logger().info(
            f'YoloNode listo — modelo: {model_path} | conf: {self.conf} | device: {device}'
        )

    # ────────────────────────────────────────────────────────────────────

    def _init_undistort(self, h: int, w: int) -> None:
        self.new_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), alpha=0.0
        )
        x, y, rw, rh = self.roi
        self.get_logger().info(f'Undistort listo — ROI: x={x} y={y} w={rw} h={rh}')

    def _undistort(self, frame: np.ndarray) -> np.ndarray:
        undist = cv2.undistort(
            frame, self.camera_matrix, self.dist_coeffs, None, self.new_camera_matrix
        )
        x, y, rw, rh = self.roi
        return undist[y:y+rh, x:x+rw]

    # ────────────────────────────────────────────────────────────────────

    def callback(self, rgb_msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(rgb_msg, desired_encoding='bgr8')

        if self.new_camera_matrix is None:
            self._init_undistort(*frame.shape[:2])

        frame = self._undistort(frame)

        results = self.model(frame, conf=self.conf, verbose=False)
        result  = results[0]

        det_array        = DetectedObjectArray()
        det_array.header = rgb_msg.header

        boxes = result.boxes
        masks = result.masks

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            label  = self.model.names[cls_id]
            conf   = float(box.conf[0])

            det            = DetectedObject()
            det.header     = rgb_msg.header
            det.class_id   = cls_id
            det.label      = label
            det.confidence = conf
            det.bbox_x1    = float(x1)
            det.bbox_y1    = float(y1)
            det.bbox_x2    = float(x2)
            det.bbox_y2    = float(y2)
            det.center_u   = (x1 + x2) / 2.0
            det.center_v   = (y1 + y2) / 2.0

            # 3D vacío — lo rellena depth_estimator_node
            det.x           = 0.0
            det.y           = 0.0
            det.z           = 0.0
            det.depth_valid = False

            # Máscara de segmentación
            if masks is not None and i < len(masks):
                mask_np         = masks.data[i].cpu().numpy().astype(np.float32)
                det.mask_height = mask_np.shape[0]
                det.mask_width  = mask_np.shape[1]
                det.mask        = mask_np.flatten().tolist()
            else:
                det.mask_height = 0
                det.mask_width  = 0
                det.mask        = []

            det_array.objects.append(det)

        self.det_pub.publish(det_array)

        annotated        = result.plot(masks=True)
        debug_msg        = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        debug_msg.header = rgb_msg.header
        self.debug_pub.publish(debug_msg)


def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()