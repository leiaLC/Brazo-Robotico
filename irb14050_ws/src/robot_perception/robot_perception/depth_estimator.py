#!/usr/bin/env python3
"""
depth_estimator_node — robot_perception
========================================
Combina RGB + Depth de la Orbbec Astra Pro, corre YOLO sobre el frame
undistorsionado y publica DetectedObjectArray con posición 3D de cada objeto.

Intrínsecos cargados desde parámetros ROS2 (no depende de CameraInfo topic).

Topics suscritos:
  /perception/rgb          (sensor_msgs/Image)
  /perception/depth        (sensor_msgs/Image)

Topics publicados:
  /perception/detections       (robot_interfaces/DetectedObjectArray)
  /perception/yolo/debug_image (sensor_msgs/Image)

Parámetros (ver config/yolo_params.yaml):
  model_path, confidence, device,
  fx, fy, cx, cy, distortion,
  depth_scale, depth_radius
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from message_filters import ApproximateTimeSynchronizer, Subscriber
from cv_bridge import CvBridge
from ultralytics import YOLO

from robot_interfaces.msg import DetectedObject, DetectedObjectArray


class DepthEstimatorNode(Node):

    def __init__(self):
        super().__init__('depth_estimator_node')

        # ── Parámetros YOLO ──────────────────────────────────────────────
        self.declare_parameter('model_path',  'yolov8n.pt')
        self.declare_parameter('confidence',  0.5)
        self.declare_parameter('device',      'cpu')

        # ── Parámetros cámara ────────────────────────────────────────────
        self.declare_parameter('fx', 699.67550943)
        self.declare_parameter('fy', 698.43830325)
        self.declare_parameter('cx', 353.68978922)
        self.declare_parameter('cy', 228.14941822)
        self.declare_parameter(
            'distortion',
            [0.36707075, -0.10014484, -0.01481674, 0.03724342, 10.61119071]
        )

        # ── Parámetros depth ─────────────────────────────────────────────
        # depth_scale: factor para convertir unidades raw → metros
        #   Astra Pro publica uint16 en mm  → scale = 0.001
        #   Si el encoding es 32FC1 ya viene en metros → scale = 1.0
        self.declare_parameter('depth_scale',  0.001)
        # depth_radius: radio en píxeles para el parche de promediado
        self.declare_parameter('depth_radius', 3)

        # ── Leer parámetros ──────────────────────────────────────────────
        model_path  = self.get_parameter('model_path').value
        confidence  = self.get_parameter('confidence').value
        device      = self.get_parameter('device').value

        fx   = self.get_parameter('fx').value
        fy   = self.get_parameter('fy').value
        cx   = self.get_parameter('cx').value
        cy   = self.get_parameter('cy').value
        dist = self.get_parameter('distortion').value

        self.depth_scale  = self.get_parameter('depth_scale').value
        self.depth_radius = self.get_parameter('depth_radius').value
        self.conf         = confidence

        # ── Matriz intrínseca y coeficientes de distorsión ───────────────
        self.camera_matrix = np.array([
            [fx,  0.0, cx],
            [0.0, fy,  cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        self.dist_coeffs = np.array(dist, dtype=np.float64)

        # Precalcula la nueva matriz óptima para undistort (alpha=0 → sin bordes negros)
        # Se inicializa en None y se calcula al recibir el primer frame
        self.new_camera_matrix = None
        self.roi               = None

        # ── YOLO ─────────────────────────────────────────────────────────
        self.model = YOLO(model_path)
        self.model.to(device)

        # ── CvBridge ─────────────────────────────────────────────────────
        self.bridge = CvBridge()

        # ── Subscribers sincronizados ────────────────────────────────────
        self.rgb_sub   = Subscriber(self, Image, '/perception/rgb')
        self.depth_sub = Subscriber(self, Image, '/perception/depth')

        self.sync = ApproximateTimeSynchronizer(
            [self.rgb_sub, self.depth_sub],
            queue_size=10,
            slop=0.05          # 50 ms de tolerancia entre frames
        )
        self.sync.registerCallback(self.callback)

        # ── Publishers ───────────────────────────────────────────────────
        self.det_pub = self.create_publisher(
            DetectedObjectArray,
            '/perception/detections',
            10
        )
        self.debug_pub = self.create_publisher(
            Image,
            '/perception/yolo/debug_image',
            10
        )

        self.get_logger().info(
            f'DepthEstimatorNode listo — '
            f'modelo: {model_path} | device: {device} | '
            f'depth_scale: {self.depth_scale} | depth_radius: {self.depth_radius}'
        )
        self.get_logger().info(
            f'Intrínsecos — fx={fx:.4f} fy={fy:.4f} cx={cx:.4f} cy={cy:.4f}'
        )

    # ────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────

    def _init_undistort(self, h: int, w: int) -> None:
        """Calcula la nueva matriz de cámara óptima una sola vez."""
        self.new_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix,
            self.dist_coeffs,
            (w, h),
            alpha=0.0           # recorta bordes negros completamente
        )
        x, y, rw, rh = self.roi
        self.get_logger().info(
            f'Undistort inicializado — ROI: x={x} y={y} w={rw} h={rh}'
        )

    def _undistort_rgb(self, frame: np.ndarray) -> np.ndarray:
        """Aplica undistort al frame RGB usando los intrínsecos calibrados."""
        undistorted = cv2.undistort(
            frame,
            self.camera_matrix,
            self.dist_coeffs,
            None,
            self.new_camera_matrix
        )
        x, y, rw, rh = self.roi
        return undistorted[y:y+rh, x:x+rw]

    def _get_depth_at(
        self, depth_image: np.ndarray, u: int, v: int
    ) -> tuple[float, bool]:
        """
        Extrae la profundidad en el punto (u, v) promediando un parche de
        radio depth_radius. Filtra ceros y NaNs (píxeles sin dato de la Astra).

        Retorna:
            (profundidad_en_metros, depth_valido)
        """
        r = self.depth_radius
        h, w = depth_image.shape[:2]

        u_min = max(0, u - r)
        u_max = min(w, u + r + 1)
        v_min = max(0, v - r)
        v_max = min(h, v + r + 1)

        patch = depth_image[v_min:v_max, u_min:u_max].astype(np.float32)

        # Filtra píxeles inválidos: cero y NaN
        valid_mask = (patch > 0) & np.isfinite(patch)
        valid      = patch[valid_mask]

        if valid.size == 0:
            return 0.0, False

        # Mediana es más robusta que media ante ruido de bordes
        depth_m = float(np.median(valid)) * self.depth_scale
        return depth_m, True

    def _pixel_to_3d(
        self, u: float, v: float, z: float
    ) -> tuple[float, float, float]:
        """
        Proyección inversa pinhole.
        Frame de coordenadas: X→derecha, Y→abajo, Z→profundidad (frente a cámara).

        Args:
            u: columna en píxeles
            v: fila en píxeles
            z: profundidad en metros

        Retorna:
            (X, Y, Z) en metros en el frame de la cámara
        """
        fx = self.new_camera_matrix[0, 0]
        fy = self.new_camera_matrix[1, 1]
        cx = self.new_camera_matrix[0, 2]
        cy = self.new_camera_matrix[1, 2]

        x = (u - cx) * z / fx
        y = (v - cy) * z / fy
        return x, y, z

    # ────────────────────────────────────────────────────────────────────
    # Callback principal
    # ────────────────────────────────────────────────────────────────────

    def callback(self, rgb_msg: Image, depth_msg: Image) -> None:
        # ── Conversión ROS → numpy ───────────────────────────────────────
        frame       = self.bridge.imgmsg_to_cv2(rgb_msg,   desired_encoding='bgr8')
        depth_image = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')

        # ── Verifica encoding del depth ──────────────────────────────────
        # Astra Pro con driver orbbec_ros → 16UC1 (mm)
        # Si ves profundidades absurdas, revisa aquí
        if depth_image.dtype == np.float32:
            # Ya viene en metros, ignorar depth_scale
            depth_image = depth_image
        elif depth_image.dtype == np.uint16:
            # mm → la conversión se hace en _get_depth_at con depth_scale
            pass
        else:
            self.get_logger().warn(
                f'Encoding de depth inesperado: {depth_image.dtype}',
                throttle_duration_sec=5.0
            )

        # ── Inicializar undistort en el primer frame ─────────────────────
        if self.new_camera_matrix is None:
            h, w = frame.shape[:2]
            self._init_undistort(h, w)

        # ── Undistort RGB ────────────────────────────────────────────────
        frame_undist = self._undistort_rgb(frame)

        # ── Inferencia YOLO ──────────────────────────────────────────────
        results = self.model(frame_undist, conf=self.conf, verbose=False)

        # ── Construye DetectedObjectArray ────────────────────────────────
        det_array        = DetectedObjectArray()
        det_array.header = rgb_msg.header

        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            label  = self.model.names[cls_id]
            conf   = float(box.conf[0])

            # Centro del bounding box
            u_center = (x1 + x2) / 2.0
            v_center = (y1 + y2) / 2.0

            # Profundidad en el centro (con parche de promediado)
            depth_m, depth_valid = self._get_depth_at(
                depth_image, int(u_center), int(v_center)
            )

            # Posición 3D
            px, py, pz = 0.0, 0.0, 0.0
            if depth_valid:
                px, py, pz = self._pixel_to_3d(u_center, v_center, depth_m)

            # Arma el mensaje
            det             = DetectedObject()
            det.header      = rgb_msg.header
            det.class_id    = cls_id
            det.label       = label
            det.confidence  = conf
            det.bbox_x1     = float(x1)
            det.bbox_y1     = float(y1)
            det.bbox_x2     = float(x2)
            det.bbox_y2     = float(y2)
            det.center_u    = float(u_center)
            det.center_v    = float(v_center)
            det.x           = px
            det.y           = py
            det.z           = pz
            det.depth_valid = depth_valid

            det_array.objects.append(det)

            self.get_logger().debug(
                f'[{label}] conf={conf:.2f} '
                f'bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) '
                f'3D=({px:.3f}, {py:.3f}, {pz:.3f})m  '
                f'depth_valid={depth_valid}'
            )

        # ── Publica detecciones ──────────────────────────────────────────
        self.det_pub.publish(det_array)

        # ── Publica imagen de debug anotada ──────────────────────────────
        annotated        = results[0].plot()
        debug_msg        = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        debug_msg.header = rgb_msg.header
        self.debug_pub.publish(debug_msg)


# ────────────────────────────────────────────────────────────────────────
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