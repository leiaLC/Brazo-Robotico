#!/usr/bin/env python3
"""
yolo_node — robot_perception
==============================
Corre YOLOv8-seg sobre el frame RGB de la RealSense D415 y publica
DetectedObjectArray con bbox 2D + máscara de segmentación.

La D415 publica imagen ya rectificada — no se necesita undistort.
La profundidad 3D la calcula pointcloud_node.

Topics suscritos:
    /camera/camera/color/image_raw   (sensor_msgs/Image)

Topics publicados:
    /perception/detections           (robot_interfaces/DetectedObjectArray)
    /perception/yolo/debug_image     (sensor_msgs/Image)

Parámetros:
    model_path  — ruta al modelo .pt o .engine (debe ser -seg)
    confidence  — umbral de confianza (default 0.5)
    device      — 'cpu' o 'cuda:0'
"""

import rclpy
import cv2
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

        model_path = self.get_parameter('model_path').value
        self.conf  = self.get_parameter('confidence').value
        device     = self.get_parameter('device').value

        # ── YOLO ─────────────────────────────────────────────────────────
        self.model = YOLO(model_path)
        self.model.to(device)

        if 'seg' not in model_path:
            self.get_logger().warn(
                f'El modelo "{model_path}" no parece ser -seg. '
                'Usa yolov8n-seg.pt, yolov8s-seg.pt, etc.'
            )

        self.bridge = CvBridge()

        # ── Subscriber ───────────────────────────────────────────────────
        # La D415 publica imagen rectificada directamente — sin undistort
        self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.callback,
            10
        )

        # ── Publishers ───────────────────────────────────────────────────
        self.det_pub = self.create_publisher(
            DetectedObjectArray, '/perception/detections', 10
        )
        self.debug_pub = self.create_publisher(
            Image, '/perception/yolo/debug_image', 10
        )

        self.get_logger().info(
            f'YoloNode listo — '
            f'modelo: {model_path} | conf: {self.conf} | device: {device}'
        )

    # ────────────────────────────────────────────────────────────────────

    def callback(self, rgb_msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(rgb_msg, desired_encoding='bgr8')

        # ── Inferencia ───────────────────────────────────────────────────
        results = self.model(frame, conf=self.conf, verbose=False)
        result  = results[0]

        # ── Construye DetectedObjectArray ────────────────────────────────
        det_array        = DetectedObjectArray()
        det_array.header = rgb_msg.header
        orig_h, orig_w = frame.shape[:2]  # para debug visual con máscaras

        boxes = result.boxes
        masks = result.masks  # None si no hay detecciones

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            det            = DetectedObject()
            det.header     = rgb_msg.header
            det.class_id   = int(box.cls[0])
            det.label      = self.model.names[det.class_id]
            det.confidence = float(box.conf[0])
            det.bbox_x1    = float(x1)
            det.bbox_y1    = float(y1)
            det.bbox_x2    = float(x2)
            det.bbox_y2    = float(y2)
            det.center_u   = (x1 + x2) / 2.0
            det.center_v   = (y1 + y2) / 2.0

            # ── Máscara de segmentación ───────────────────────────────────
            if masks is not None and i < len(masks):
                mask_np         = masks.data[i].cpu().numpy().astype('float32')
                det.mask_height = mask_np.shape[0]
                det.mask_width  = mask_np.shape[1]
                det.mask        = mask_np.flatten().tolist()
            else:
                det.mask_height = 0
                det.mask_width  = 0
                det.mask        = []

            det_array.objects.append(det)

        # ── Publica ───────────────────────────────────────────────────────
        self.det_pub.publish(det_array)

        # Debug visual con máscaras superpuestas

        annotated = result.plot(masks=True)
        annotated = cv2.resize(annotated, (orig_w, orig_h))   # ← fix zoom

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