#!/usr/bin/env python3
"""
depth_estimator_node — robot_perception
========================================
Se subscribe independientemente a /perception/detections y /perception/depth.
Guarda el último depth recibido y lo usa cada vez que llegan detecciones.

No hay sincronizador — asumimos que RGB y Depth llegan a la misma frecuencia
desde el mismo driver, por lo que el desfase es despreciable.

Topics suscritos:
    /perception/detections     (robot_interfaces/DetectedObjectArray)
    /perception/depth          (sensor_msgs/Image)

Topics publicados:
    /perception/detections_3d  (robot_interfaces/DetectedObjectArray)
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
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
        self.declare_parameter('depth_scale',  0.001)  # escala para convertir a metros
        self.declare_parameter('depth_radius', 7)

        fx   = self.get_parameter('fx').value
        fy   = self.get_parameter('fy').value
        cx_  = self.get_parameter('cx').value
        cy_  = self.get_parameter('cy').value
        dist = self.get_parameter('distortion').value

        self.depth_scale  = self.get_parameter('depth_scale').value
        self.depth_radius = self.get_parameter('depth_radius').value

        # ── Intrínsecos ──────────────────────────────────────────────────
        self.camera_matrix = np.array([
            [fx,  0.0, cx_],
            [0.0, fy,  cy_],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        self.dist_coeffs       = np.array(dist, dtype=np.float64)
        self.new_camera_matrix = None   # se inicializa al primer depth frame

        self.bridge = CvBridge()

        # Último depth recibido — se actualiza en cada depth callback
        self.last_depth: np.ndarray | None = None

        # ── Subscribers independientes ───────────────────────────────────
        self.create_subscription(
            Image,
            '/camera/depth/image_raw',
            self.depth_callback,
            10
        )
        self.create_subscription(
            DetectedObjectArray,
            '/perception/detections',
            self.detections_callback,
            10
        )

        # ── Publisher ────────────────────────────────────────────────────
        self.det3d_pub = self.create_publisher(
            DetectedObjectArray, '/perception/detections_3d', 10
        )

        self.get_logger().info(
            f'DepthEstimatorNode listo — '
            f'depth_scale={self.depth_scale} | depth_radius={self.depth_radius}'
        )

    # ────────────────────────────────────────────────────────────────────
    # Depth callback — solo guarda el último frame
    # ────────────────────────────────────────────────────────────────────

    def depth_callback(self, depth_msg: Image) -> None:
        depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')

        # Inicializa la camera matrix óptima una sola vez
        if self.new_camera_matrix is None:
            h, w = depth.shape[:2]
            self.new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix, self.dist_coeffs, (w, h), alpha=0.0
            )
            self.get_logger().info(f'Camera matrix óptima lista para {w}x{h}')

        self.last_depth = depth

    # ────────────────────────────────────────────────────────────────────
    # Detections callback — usa el último depth guardado
    # ────────────────────────────────────────────────────────────────────

    def detections_callback(self, det_msg: DetectedObjectArray) -> None:
        if self.last_depth is None:
            self.get_logger().warn(
                'Aún no hay depth disponible', throttle_duration_sec=2.0
            )
            return

        if self.new_camera_matrix is None:
            self.get_logger().warn(
                'Camera matrix no inicializada', throttle_duration_sec=2.0
            )
            return

        out_array        = DetectedObjectArray()
        out_array.header = det_msg.header

        for det in det_msg.objects:
            depth_m, valid = self._get_depth(det)

            px, py, pz = 0.0, 0.0, 0.0
            if valid:
                px, py, pz = self._pixel_to_3d(det.center_u, det.center_v, depth_m)

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

    # ────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────

    def _get_depth(self, det: DetectedObject) -> tuple[float, bool]:
        """
        Si hay máscara usa la mediana sobre todos sus píxeles válidos.
        Si no hay máscara (o no tiene depth válido) usa un parche centrado.
        """
        if det.mask and det.mask_width > 0 and det.mask_height > 0:
            return self._depth_from_mask(det)
        return self._depth_from_patch(int(det.center_u), int(det.center_v))

    def _depth_from_mask(self, det: DetectedObject) -> tuple[float, bool]:
        """Mediana de depth dentro de la máscara de segmentación."""
        mask = np.array(det.mask, dtype=np.float32).reshape(
            det.mask_height, det.mask_width
        )
        dh, dw = self.last_depth.shape[:2]
        mask_resized = cv2.resize(mask, (dw, dh), interpolation=cv2.INTER_NEAREST)

        valid_pixels = self.last_depth[mask_resized > 0.5].astype(np.float32)
        valid_pixels = valid_pixels[(valid_pixels > 0) & np.isfinite(valid_pixels)]

        if valid_pixels.size == 0:
            # Fallback al parche central
            return self._depth_from_patch(int(det.center_u), int(det.center_v))

        return float(np.median(valid_pixels)) * self.depth_scale, True

    def _depth_from_patch(self, u: int, v: int) -> tuple[float, bool]:
        """Mediana de depth en un parche de radio depth_radius alrededor de (u,v)."""
        r = self.depth_radius
        h, w = self.last_depth.shape[:2]

        u0 = max(0, u - r);  u1 = min(w, u + r + 1)
        v0 = max(0, v - r);  v1 = min(h, v + r + 1)

        patch = self.last_depth[v0:v1, u0:u1].astype(np.float32)
        valid = patch[(patch > 0) & np.isfinite(patch)]

        if valid.size == 0:
            return 0.0, False

        return float(np.median(valid)) * self.depth_scale, True

    def _pixel_to_3d(self, u: float, v: float, z: float) -> tuple[float, float, float]:
        """Proyección inversa pinhole. Retorna (X, Y, Z) en metros."""
        fx = self.new_camera_matrix[0, 0]
        fy = self.new_camera_matrix[1, 1]
        cx = self.new_camera_matrix[0, 2]
        cy = self.new_camera_matrix[1, 2]
        return (u - cx) * z / fx, (v - cy) * z / fy, z


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