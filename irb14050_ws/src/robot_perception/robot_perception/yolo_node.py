#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO
import numpy as np

# Si tienes robot_interfaces con Detection2D.msg propio, importa ahí
# from robot_interfaces.msg import DetectedObject, DetectedObjectArray

class YoloNode(Node):
    def __init__(self):
        super().__init__('yolo_node')

        # Parámetros configurables desde yaml
        self.declare_parameter('model_path', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.5)
        self.declare_parameter('device', 'cpu')  # 'cuda:0' si tienes GPU

        model_path = self.get_parameter('model_path').value
        self.conf = self.get_parameter('confidence').value
        device = self.get_parameter('device').value

        self.model = YOLO(model_path)
        self.model.to(device)
        self.bridge = CvBridge()

        # Sub al RGB sincronizado que viene del camera_node
        self.create_subscription(Image, '/perception/rgb', self.image_callback, 10)

        # Publica imagen anotada (para debug en RViz)
        self.debug_pub = self.create_publisher(Image, '/perception/yolo/debug_image', 10)

        # Publica detecciones — usa Vision2D estándar o tu msg custom
        # self.det_pub = self.create_publisher(DetectedObjectArray, '/perception/detections', 10)

        self.get_logger().info(f'YOLO node ready — model: {model_path}, device: {device}')

    def image_callback(self, msg: Image):
        # Convierte ROS Image → numpy
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        results = self.model(frame, conf=self.conf, verbose=False)

        # --- Publica imagen anotada para debug ---
        annotated = results[0].plot()
        debug_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        debug_msg.header = msg.header
        self.debug_pub.publish(debug_msg)

        # --- Publica detecciones estructuradas ---
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            self.get_logger().debug(f'{label} ({conf:.2f}) @ [{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]')
            # Aquí construyes y publicas tu msg custom

def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()