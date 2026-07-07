#!/usr/bin/env python3
"""
yolo_snapshot_node - robot_perception
=====================================
Guarda fotos del ultimo frame publicado por yolo_node.

Topics suscritos:
    /perception/yolo/debug_image     (sensor_msgs/Image)

Servicios:
    /perception/yolo/take_snapshot   (std_srvs/Trigger)

Parametros:
    image_topic   - topico de imagen a capturar
    output_dir    - carpeta donde se guardan las fotos
    file_prefix   - prefijo del archivo generado
"""

from datetime import datetime
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger


class YoloSnapshotNode(Node):

    def __init__(self):
        super().__init__('yolo_snapshot_node')

        self.declare_parameter('image_topic', '/perception/yolo/debug_image')
        self.declare_parameter('output_dir', '~/yolo_snapshots')
        self.declare_parameter('file_prefix', 'yolo')

        self.image_topic = str(self.get_parameter('image_topic').value)
        output_dir = str(self.get_parameter('output_dir').value)
        self.output_dir = Path(output_dir).expanduser()
        self.file_prefix = str(self.get_parameter('file_prefix').value)

        self.bridge = CvBridge()
        self.last_image = None
        self.last_stamp = None

        self.create_subscription(
            Image,
            self.image_topic,
            self._image_callback,
            10,
        )

        self.create_service(
            Trigger,
            '/perception/yolo/take_snapshot',
            self._take_snapshot_callback,
        )

        self.get_logger().info(
            f'YoloSnapshotNode listo - escuchando {self.image_topic} | '
            f'guardando en {self.output_dir}'
        )

    def _image_callback(self, msg: Image) -> None:
        try:
            self.last_image = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8',
            )
            self.last_stamp = msg.header.stamp
        except CvBridgeError as exc:
            self.get_logger().error(f'No se pudo convertir imagen YOLO: {exc}')

    def _take_snapshot_callback(self, request, response):
        del request

        if self.last_image is None:
            response.success = False
            response.message = (
                f'Todavia no hay imagen en {self.image_topic}. '
                'Verifica que yolo_node este publicando.'
            )
            return response

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            response.success = False
            response.message = f'No se pudo crear {self.output_dir}: {exc}'
            return response

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        path = self.output_dir / f'{self.file_prefix}_{timestamp}.jpg'

        if not cv2.imwrite(str(path), self.last_image):
            response.success = False
            response.message = f'No se pudo guardar la foto en {path}'
            return response

        response.success = True
        response.message = str(path)
        self.get_logger().info(f'Foto YOLO guardada: {path}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = YoloSnapshotNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
