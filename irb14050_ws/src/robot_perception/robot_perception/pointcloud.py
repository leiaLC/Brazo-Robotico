#!/usr/bin/env python3
"""
pointcloud_node — robot_perception
=====================================
Recibe la PointCloud2 del driver RealSense D415 y las detecciones de
yolo_node. Para cada objeto detectado filtra los puntos dentro de su
máscara de segmentación y calcula el centroide 3D y las dimensiones.

NO publica la nube del objeto — OctoMap se encarga de las colisiones.
Solo publica centroide + tamaño para que task_manager pueda planear el grasp.

Topics suscritos:
    /camera/depth/color/points   (sensor_msgs/PointCloud2)
    /camera/color/camera_info    (sensor_msgs/CameraInfo)
    /perception/detections       (robot_interfaces/DetectedObjectArray)

Topics publicados:
    /perception/object_clouds    (robot_interfaces/DetectedObjectCloudArray)
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, CameraInfo
from std_msgs.msg import Header
import sensor_msgs_py.point_cloud2 as pc2

from robot_interfaces.msg import (
    DetectedObject,
    DetectedObjectArray,
    DetectedObjectCloud,
    DetectedObjectCloudArray,
)


class PointCloudNode(Node):

    def __init__(self):
        super().__init__('pointcloud_node')

        # ── Parámetros ───────────────────────────────────────────────────
        self.declare_parameter('min_points',   10)
        self.declare_parameter('mask_erosion', 7)    # kernel de erosión en px

        self.min_points   = self.get_parameter('min_points').value
        self.mask_erosion = self.get_parameter('mask_erosion').value

        # ── Intrínsecos — se cargan del CameraInfo ───────────────────────
        self.fx: float | None = None
        self.fy: float | None = None
        self.cx: float | None = None
        self.cy: float | None = None
        self.img_w: int | None = None
        self.img_h: int | None = None

        # Última nube recibida
        self.last_cloud_xyz: np.ndarray | None = None   # (N, 3) float32

        # ── Subscriber CameraInfo — una sola vez ─────────────────────────
        self.info_sub = self.create_subscription(
            CameraInfo,
            '/camera/color/camera_info',
            self._camera_info_callback,
            1
        )

        # ── Subscribers principales ───────────────────────────────────────
        self.create_subscription(
            PointCloud2,
            '/camera/depth/color/points',
            self._cloud_callback,
            5
        )
        self.create_subscription(
            DetectedObjectArray,
            '/perception/detections',
            self._detections_callback,
            10
        )

        # ── Publisher ─────────────────────────────────────────────────────
        self.clouds_pub = self.create_publisher(
            DetectedObjectCloudArray, '/perception/object_clouds', 10
        )

        self.get_logger().info(
            f'PointCloudNode listo — min_points={self.min_points}'
        )

    # ────────────────────────────────────────────────────────────────────
    # CameraInfo
    # ────────────────────────────────────────────────────────────────────

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        if self.fx is not None:
            return
        k          = msg.k
        self.fx    = k[0]
        self.fy    = k[4]
        self.cx    = k[2]
        self.cy    = k[5]
        self.img_w = msg.width
        self.img_h = msg.height
        self.get_logger().info(
            f'Intrínsecos cargados — '
            f'fx={self.fx:.2f} fy={self.fy:.2f} '
            f'cx={self.cx:.2f} cy={self.cy:.2f}'
        )
        self.destroy_subscription(self.info_sub)

    # ────────────────────────────────────────────────────────────────────
    # Cloud callback — guarda el último frame
    # ────────────────────────────────────────────────────────────────────

    def _cloud_callback(self, msg: PointCloud2) -> None:
        cloud_arr = pc2.read_points_numpy(
            msg,
            field_names=('x', 'y', 'z'),
            skip_nans=True
        )
        if cloud_arr is not None and len(cloud_arr) > 0:
            self.last_cloud_xyz = cloud_arr.reshape(-1, 3).astype(np.float32)

    # ────────────────────────────────────────────────────────────────────
    # Detections callback
    # ────────────────────────────────────────────────────────────────────

    def _detections_callback(self, det_msg: DetectedObjectArray) -> None:
        if self.last_cloud_xyz is None:
            self.get_logger().warn('Sin nube todavía', throttle_duration_sec=2.0)
            return

        if self.fx is None:
            self.get_logger().warn('Sin intrínsecos todavía', throttle_duration_sec=2.0)
            return

        if not det_msg.objects:
            return

        # ── Proyecta TODOS los puntos al plano imagen de una vez ─────────
        xyz   = self.last_cloud_xyz         # (N, 3)
        z_v   = xyz[:, 2]
        valid = z_v > 0

        xyz_v = xyz[valid]
        z_v   = xyz_v[:, 2]

        u = (xyz_v[:, 0] * self.fx / z_v + self.cx)
        v = (xyz_v[:, 1] * self.fy / z_v + self.cy)

        out_array        = DetectedObjectCloudArray()
        out_array.header = det_msg.header

        for det in det_msg.objects:
            mask_2d = self._get_mask(det)
            if mask_2d is None:
                continue

            # ── Filtra puntos dentro de la máscara ───────────────────────
            u_int = np.round(u).astype(np.int32)
            v_int = np.round(v).astype(np.int32)

            in_bounds = (
                (u_int >= 0) & (u_int < self.img_w) &
                (v_int >= 0) & (v_int < self.img_h)
            )

            u_b   = u_int[in_bounds]
            v_b   = v_int[in_bounds]
            idx_b = np.where(in_bounds)[0]

            in_mask = mask_2d[v_b, u_b] > 0
            idx_obj = idx_b[in_mask]

            if len(idx_obj) < self.min_points:
                self.get_logger().debug(
                    f'[{det.label}] descartado — '
                    f'{len(idx_obj)} puntos < {self.min_points}'
                )
                continue

            obj_points = xyz_v[idx_obj]   # (M, 3)

            # ── Centroide ─────────────────────────────────────────────────
            centroid = obj_points.mean(axis=0)

            # ── Dimensiones del bounding box 3D ──────────────────────────
            # min/max en cada eje → tamaño del objeto
            min_xyz  = obj_points.min(axis=0)
            max_xyz  = obj_points.max(axis=0)
            size     = max_xyz - min_xyz   # (size_x, size_y, size_z)

            # ── Arma el mensaje ───────────────────────────────────────────
            obj_cloud                = DetectedObjectCloud()
            obj_cloud.header         = det_msg.header
            obj_cloud.class_id       = det.class_id
            obj_cloud.label          = det.label
            obj_cloud.confidence     = det.confidence
            obj_cloud.bbox_x1        = det.bbox_x1
            obj_cloud.bbox_y1        = det.bbox_y1
            obj_cloud.bbox_x2        = det.bbox_x2
            obj_cloud.bbox_y2        = det.bbox_y2
            obj_cloud.centroid_x     = float(centroid[0])
            obj_cloud.centroid_y     = float(centroid[1])
            obj_cloud.centroid_z     = float(centroid[2])
            obj_cloud.centroid_valid = True
            obj_cloud.size_x         = float(size[0])
            obj_cloud.size_y         = float(size[1])
            obj_cloud.size_z         = float(size[2])

            out_array.objects.append(obj_cloud)

            self.get_logger().info(
                f'[{det.label}] '
                f'centroide=({centroid[0]:.3f}, {centroid[1]:.3f}, {centroid[2]:.3f})m  '
                f'tamaño=({size[0]:.3f}, {size[1]:.3f}, {size[2]:.3f})m  '
                f'puntos={len(idx_obj)}'
            )

        if out_array.objects:
            self.clouds_pub.publish(out_array)

    # ────────────────────────────────────────────────────────────────────
    # Helper — máscara binaria al tamaño de la imagen
    # ────────────────────────────────────────────────────────────────────

    def _get_mask(self, det: DetectedObject) -> np.ndarray | None:
        """
        Retorna máscara binaria uint8 (img_h, img_w).
        Usa la máscara de segmentación si existe, sino el bbox.
        Erosiona para eliminar bordes ruidosos.
        """
        if self.img_w is None or self.img_h is None:
            return None

        if det.mask and det.mask_width > 0 and det.mask_height > 0:
            mask = np.array(det.mask, dtype=np.float32).reshape(
                det.mask_height, det.mask_width
            )
            mask   = cv2.resize(mask, (self.img_w, self.img_h),
                                interpolation=cv2.INTER_NEAREST)
            binary = (mask > 0.5).astype(np.uint8)

            if self.mask_erosion > 0:
                kernel = cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE,
                    (self.mask_erosion, self.mask_erosion)
                )
                binary = cv2.erode(binary, kernel)
        else:
            # Fallback al bbox
            binary = np.zeros((self.img_h, self.img_w), dtype=np.uint8)
            x1 = max(0, int(det.bbox_x1))
            y1 = max(0, int(det.bbox_y1))
            x2 = min(self.img_w, int(det.bbox_x2))
            y2 = min(self.img_h, int(det.bbox_y2))
            binary[y1:y2, x1:x2] = 1

        return binary


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()