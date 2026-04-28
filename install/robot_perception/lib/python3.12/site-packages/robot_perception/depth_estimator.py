#!/usr/bin/env python3
"""
depth_estimator_node — robot_perception
========================================
Se subscribe a /perception/detections (publicado por yolo_node) y a
/perception/depth, y para cada DetectedObject calcula su posición 3D
usando los intrínsecos calibrados de la cámara.

Publica el mismo array pero con los campos x, y, z, depth_valid rellenos.

Topics suscritos:
    /perception/detections   (robot_interfaces/DetectedObjectArray)  ← de yolo_node
    /perception/depth        (sensor_msgs/Image)

Topics publicados:
    /perception/detections_3d  (robot_interfaces/DetectedObjectArray)

Parámetros:
    fx, fy, cx, cy, distortion — intrínsecos calibrados (mismos que yolo_node)
    depth_scale   — factor raw → metros (0.001 para Astra Pro en mm)
    depth_radius  — radio de parche para promediar depth (px)
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from message_filters import ApproximateTimeSynchronizer, Subscriber
from cv_bridge import CvBridge

from robot_interfaces.msg import DetectedObject, DetectedObjectArray


class DepthEstimatorNode(Node):

    def __init__(self):
        super().__init__('depth_estimator_node')

        # ── Parámetros ───────────────────────────────────────────────────
        self.declare_parameter('fx', 699.67550943)
        self.declare_parameter('fy', 698.43830325)
        self.declare_parameter('cx', 353.68978922)
        self.declare_parameter('cy', 228.14941822)
        self.declare_parameter(
            'distortion',
            [0.36707075, -0.10014484, -0.01481674, 0.03724342, 10.61119071]
        )
        self.declare_parameter('depth_scale',  0.001)
        self.declare_parameter('depth_radius', 3)

        fx   = self.get_parameter('fx').value
        fy   = self.get_parameter('fy').value
        cx_  = self.get_parameter('cx').value
        cy_  = self.get_parameter('cy').value
        dist = self.get_parameter('distortion').value

        self.depth_scale  = self.get_parameter('depth_scale').value
        self.depth_radius = self.get_parameter('depth_radius').value

        # ── Intrínsecos ──────────────────────────────────────────────────
        # Usamos la new_camera_matrix óptima (post-undistort) para la
        # proyección inversa. Se inicializa en el primer depth frame.
        self.camera_matrix = np.array([
            [fx,  0.0, cx_],
            [0.0, fy,  cy_],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        self.dist_coeffs       = np.array(dist, dtype=np.float64)
        self.new_camera_matrix = None
        self.roi               = None

        self.bridge = CvBridge()

        # ── Sincronización detections + depth ────────────────────────────
        self.det_sub   = Subscriber(self, DetectedObjectArray, '/perception/detections')
        self.depth_sub = Subscriber(self, Image,               '/perception/depth')

        self.sync = ApproximateTimeSynchronizer(
            [self.det_sub, self.depth_sub],
            queue_size=10,
            slop=0.05
        )
        self.sync.registerCallback(self.callback)

        # ── Publisher ────────────────────────────────────────────────────
        self.det3d_pub = self.create_publisher(
            DetectedObjectArray, '/perception/detections_3d', 10
        )

        self.get_logger().info(
            f'DepthEstimatorNode listo — '
            f'depth_scale={self.depth_scale} | depth_radius={self.depth_radius}'
        )

    # ────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────

    def _init_camera(self, h: int, w: int) -> None:
        """Calcula new_camera_matrix óptima una sola vez con el tamaño real."""
        self.new_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), alpha=0.0
        )
        self.get_logger().info(
            f'Camera matrix óptima calculada para {w}x{h}'
        )

    def _get_depth_at(
        self, depth_image: np.ndarray, u: int, v: int
    ) -> tuple[float, bool]:
        """
        Promedia los píxeles válidos en un parche de radio depth_radius
        alrededor de (u, v).
        Retorna (profundidad_metros, es_valido).
        """
        r = self.depth_radius
        h, w = depth_image.shape[:2]

        u0 = max(0, u - r);  u1 = min(w, u + r + 1)
        v0 = max(0, v - r);  v1 = min(h, v + r + 1)

        patch = depth_image[v0:v1, u0:u1].astype(np.float32)
        valid = patch[(patch > 0) & np.isfinite(patch)]

        if valid.size == 0:
            return 0.0, False

        return float(np.median(valid)) * self.depth_scale, True

    def _pixel_to_3d(
        self, u: float, v: float, z: float
    ) -> tuple[float, float, float]:
        """
        Proyección inversa pinhole usando la new_camera_matrix (post-undistort).
        Retorna (X, Y, Z) en metros en el frame de la cámara.
        """
        fx = self.new_camera_matrix[0, 0]
        fy = self.new_camera_matrix[1, 1]
        cx = self.new_camera_matrix[0, 2]
        cy = self.new_camera_matrix[1, 2]

        return (u - cx) * z / fx, (v - cy) * z / fy, z

    def _mask_depth_centroid(
        self,
        depth_image: np.ndarray,
        det: DetectedObject
    ) -> tuple[float, bool]:
        """
        Si hay máscara de segmentación disponible, calcula la profundidad
        mediana SOLO sobre los píxeles dentro de la máscara.
        Más preciso que usar solo el centro del bbox.
        Hace fallback al centro del bbox si la máscara no tiene depth válido.
        """
        if not det.mask or det.mask_width == 0 or det.mask_height == 0:
            return self._get_depth_at(
                depth_image, int(det.center_u), int(det.center_v)
            )

        # Reconstruye máscara 2D
        mask = np.array(det.mask, dtype=np.float32).reshape(
            det.mask_height, det.mask_width
        )

        # Redimensiona al tamaño del depth image
        dh, dw = depth_image.shape[:2]
        mask_resized = cv2.resize(mask, (dw, dh), interpolation=cv2.INTER_NEAREST)

        # Profundidades dentro de la máscara
        binary_mask = mask_resized > 0.5
        depth_vals  = depth_image[binary_mask].astype(np.float32)
        valid       = depth_vals[(depth_vals > 0) & np.isfinite(depth_vals)]

        if valid.size == 0:
            # Fallback al centro del bbox
            return self._get_depth_at(
                depth_image, int(det.center_u), int(det.center_v)
            )

        return float(np.median(valid)) * self.depth_scale, True

    # ────────────────────────────────────────────────────────────────────
    # Callback principal
    # ────────────────────────────────────────────────────────────────────

    def callback(
        self,
        det_msg:   DetectedObjectArray,
        depth_msg: Image
    ) -> None:

        depth_image = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')

        # Aviso si el dtype es inesperado
        if depth_image.dtype not in (np.uint16, np.float32):
            self.get_logger().warn(
                f'dtype de depth inesperado: {depth_image.dtype}. '
                'Esperado uint16 (mm) o float32 (m).',
                throttle_duration_sec=5.0
            )

        # Inicializa la matriz óptima con el tamaño real del depth
        if self.new_camera_matrix is None:
            h, w = depth_image.shape[:2]
            self._init_camera(h, w)

        # ── Construye el nuevo array con 3D relleno ──────────────────────
        out_array        = DetectedObjectArray()
        out_array.header = det_msg.header

        for det in det_msg.objects:
            # Usa la máscara si existe, sino el centro del bbox
            depth_m, valid = self._mask_depth_centroid(depth_image, det)

            px, py, pz = 0.0, 0.0, 0.0
            if valid:
                px, py, pz = self._pixel_to_3d(det.center_u, det.center_v, depth_m)

            # Copia todo del det original y rellena los campos 3D
            det_3d             = DetectedObject()
            det_3d.header      = det.header
            det_3d.class_id    = det.class_id
            det_3d.label       = det.label
            det_3d.confidence  = det.confidence
            det_3d.bbox_x1     = det.bbox_x1
            det_3d.bbox_y1     = det.bbox_y1
            det_3d.bbox_x2     = det.bbox_x2
            det_3d.bbox_y2     = det.bbox_y2
            det_3d.center_u    = det.center_u
            det_3d.center_v    = det.center_v
            det_3d.mask        = det.mask
            det_3d.mask_width  = det.mask_width
            det_3d.mask_height = det.mask_height
            det_3d.x           = px
            det_3d.y           = py
            det_3d.z           = pz
            det_3d.depth_valid = valid

            out_array.objects.append(det_3d)

            self.get_logger().debug(
                f'[{det.label}] 3D=({px:.3f}, {py:.3f}, {pz:.3f})m  '
                f'depth_valid={valid}  mask_used={bool(det.mask)}'
            )

        self.det3d_pub.publish(out_array)


def main(args=None):
    rclpy.init(args=args)
    node = DepthEstimatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()