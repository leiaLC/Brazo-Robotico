#!/usr/bin/env python3
"""
task_manager_node — robot_task_manager
========================================
Orquestador principal del sistema. Recibe objetos detectados por
percepción, selecciona el objetivo y envía goals a MoveIt2 a través
de MoveGroupInterface (move_group estándar).

Pipeline:
    /perception/object_clouds  →  task_manager  →  move_group
                                                        ↓
                                               egm_moveit_executor
                                                        ↓
                                                   Robot real

Estado actual:
    - Transformación camera → base_link: PLACEHOLDER (hardcodeado)
      TODO: reemplazar con tf2 cuando esté la calibración eye-in-hand

Topics suscritos:
    /perception/object_clouds   (robot_interfaces/DetectedObjectCloudArray)

Topics publicados:
    /task_manager/status        (std_msgs/String)  ← estado actual para debug

Servicios:
    /task_manager/set_target    (robot_interfaces/srv/SetTarget)
        Permite seleccionar qué label buscar (ej. "bottle")
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, Quaternion

# MoveIt2 — interfaz estándar via MoveGroup action
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest,
    WorkspaceParameters,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
)
from shape_msgs.msg import SolidPrimitive

from robot_interfaces.msg import DetectedObjectCloud, DetectedObjectCloudArray
from robot_interfaces.srv import SetTarget

import math
import numpy as np


# ── Estados del task manager ──────────────────────────────────────────────────
class State:
    IDLE        = 'IDLE'         # esperando comando
    SEARCHING   = 'SEARCHING'    # buscando objeto en las detecciones
    PLANNING    = 'PLANNING'     # enviando goal a MoveIt2
    EXECUTING   = 'EXECUTING'    # brazo en movimiento
    SUCCESS     = 'SUCCESS'      # grasp completado
    FAILED      = 'FAILED'       # algo salió mal


class TaskManagerNode(Node):

    def __init__(self):
        super().__init__('task_manager_node')

        # ── Parámetros ───────────────────────────────────────────────────
        self.declare_parameter('planning_group',    'irb14050_arm')
        self.declare_parameter('base_frame',        'base_link')
        self.declare_parameter('ee_frame',          'tool0')
        self.declare_parameter('target_label',      '')        # vacío = cualquier objeto
        self.declare_parameter('approach_offset_z', 0.10)     # 10cm sobre el objeto
        self.declare_parameter('planning_time',     5.0)       # segundos para planear
        self.declare_parameter('velocity_scale',    0.3)       # 0-1, velocidad del brazo

        self.planning_group    = self.get_parameter('planning_group').value
        self.base_frame        = self.get_parameter('base_frame').value
        self.ee_frame          = self.get_parameter('ee_frame').value
        self.target_label      = self.get_parameter('target_label').value
        self.approach_offset_z = self.get_parameter('approach_offset_z').value
        self.planning_time     = self.get_parameter('planning_time').value
        self.velocity_scale    = self.get_parameter('velocity_scale').value

        # ── Estado interno ────────────────────────────────────────────────
        self.state             = State.IDLE
        self.current_goal_handle = None

        # ── MoveGroup Action Client ───────────────────────────────────────
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.get_logger().info('Esperando move_group...')
        self.move_group_client.wait_for_server()
        self.get_logger().info('move_group conectado')

        # ── Subscriber percepción ────────────────────────────────────────
        self.create_subscription(
            DetectedObjectCloudArray,
            '/perception/object_clouds',
            self._detections_callback,
            10
        )

        # ── Servicio para cambiar el target label en runtime ─────────────
        self.create_service(
            SetTarget,
            '/task_manager/set_target',
            self._set_target_callback
        )

        # ── Publisher de estado ───────────────────────────────────────────
        self.status_pub = self.create_publisher(String, '/task_manager/status', 10)

        # Timer para publicar estado periódicamente
        self.create_timer(1.0, self._publish_status)

        self.get_logger().info(
            f'TaskManagerNode listo — '
            f'group: {self.planning_group} | '
            f'target: "{self.target_label or "cualquier objeto"}"'
        )

    # ────────────────────────────────────────────────────────────────────
    # Servicio — cambia el label objetivo en runtime
    # ────────────────────────────────────────────────────────────────────

    def _set_target_callback(self, request, response):
        self.target_label = request.label
        self.state        = State.SEARCHING
        response.success  = True
        response.message  = f'Target seteado a: "{self.target_label}"'
        self.get_logger().info(response.message)
        return response

    # ────────────────────────────────────────────────────────────────────
    # Callback de percepción
    # ────────────────────────────────────────────────────────────────────

    def _detections_callback(self, msg: DetectedObjectCloudArray) -> None:
        # Solo actúa si está en SEARCHING
        if self.state not in (State.SEARCHING, State.IDLE):
            return

        if not msg.objects:
            return

        # ── Selecciona el objeto objetivo ─────────────────────────────────
        target = self._select_target(msg.objects)

        if target is None:
            self.get_logger().debug(
                f'No se encontró "{self.target_label}" en las detecciones',
                throttle_duration_sec=2.0
            )
            return

        if not target.centroid_valid:
            self.get_logger().warn(f'Centroide inválido para {target.label}')
            return

        self.get_logger().info(
            f'Objetivo seleccionado: [{target.label}] '
            f'centroide=({target.centroid_x:.3f}, '
            f'{target.centroid_y:.3f}, '
            f'{target.centroid_z:.3f})m'
        )

        # ── Transforma al frame del robot ─────────────────────────────────
        pose_in_base = self._transform_to_base_link(target)

        if pose_in_base is None:
            self.get_logger().error('Falló la transformación de coordenadas')
            return

        # ── Calcula la grasp pose ─────────────────────────────────────────
        grasp_pose = self._compute_grasp_pose(pose_in_base, target)

        # ── Envía goal a MoveIt2 ──────────────────────────────────────────
        self.state = State.PLANNING
        self._send_move_goal(grasp_pose)

    # ────────────────────────────────────────────────────────────────────
    # Selección de objetivo
    # ────────────────────────────────────────────────────────────────────

    def _select_target(
        self, objects: list[DetectedObjectCloud]
    ) -> DetectedObjectCloud | None:
        """
        Selecciona el objeto objetivo de la lista de detecciones.
        Si target_label está seteado, busca ese label.
        Si no, toma el objeto más cercano (menor z).
        """
        candidates = objects

        if self.target_label:
            candidates = [o for o in objects if o.label == self.target_label]

        if not candidates:
            return None

        # Toma el más cercano
        return min(candidates, key=lambda o: o.centroid_z)

    # ────────────────────────────────────────────────────────────────────
    # Transformación de coordenadas
    # ────────────────────────────────────────────────────────────────────

    def _transform_to_base_link(
        self, obj: DetectedObjectCloud
    ) -> PoseStamped | None:
        """
        Transforma el centroide del frame de la cámara al frame base_link.

        TODO: Reemplazar con tf2 cuando esté disponible la calibración
              eye-in-hand. Ejemplo de cómo quedará:

              from tf2_ros import Buffer, TransformListener
              from tf2_geometry_msgs import do_transform_pose

              self.tf_buffer = Buffer()
              self.tf_listener = TransformListener(self.tf_buffer, self)

              transform = self.tf_buffer.lookup_transform(
                  self.base_frame,
                  obj.header.frame_id,
                  rclpy.time.Time()
              )
              return do_transform_pose(pose_in_camera, transform)

        Por ahora asume que la cámara está en una posición fija conocida
        respecto al robot (hardcodeada para testing).
        """

        # ── PLACEHOLDER — reemplazar con tf2 ──────────────────────────────
        # Transformación identidad — asume que la cámara está en el origen
        # ESTO ES SOLO PARA TESTING — no refleja la posición real
        pose = PoseStamped()
        pose.header.frame_id = self.base_frame
        pose.header.stamp    = self.get_clock().now().to_msg()
        pose.pose.position.x = float(obj.centroid_x)
        pose.pose.position.y = float(obj.centroid_y)
        pose.pose.position.z = float(obj.centroid_z)

        # Orientación neutra
        pose.pose.orientation.w = 1.0

        self.get_logger().warn(
            'USANDO TRANSFORMACIÓN PLACEHOLDER — calibrar eye-in-hand',
            throttle_duration_sec=10.0
        )

        return pose

    # ────────────────────────────────────────────────────────────────────
    # Grasp pose
    # ────────────────────────────────────────────────────────────────────

    def _compute_grasp_pose(
        self, pose: PoseStamped, obj: DetectedObjectCloud
    ) -> PoseStamped:
        """
        Calcula la pose del end-effector para agarrar el objeto.

        Estrategia actual: top-down approach
            - Posición: centroide del objeto + offset en Z (sobre el objeto)
            - Orientación: gripper apuntando hacia abajo

        TODO: Mejorar con:
            - Orientación basada en el eje principal del objeto (PCA de la nube)
            - Múltiples candidatos de grasp
            - Grasp planning library (GraspIt!, GPD, etc.)
        """
        grasp = PoseStamped()
        grasp.header = pose.header

        # Posición — sobre el centroide del objeto
        grasp.pose.position.x = pose.pose.position.x
        grasp.pose.position.y = pose.pose.position.y
        grasp.pose.position.z = pose.pose.position.z + self.approach_offset_z

        # Orientación — top-down (gripper apuntando hacia abajo en base_link)
        # Rotación de 180° en X → Z apunta hacia abajo
        grasp.pose.orientation = self._top_down_orientation()

        self.get_logger().info(
            f'Grasp pose calculada — '
            f'pos=({grasp.pose.position.x:.3f}, '
            f'{grasp.pose.position.y:.3f}, '
            f'{grasp.pose.position.z:.3f}) '
            f'offset_z={self.approach_offset_z}m'
        )

        return grasp

    def _top_down_orientation(self) -> Quaternion:
        """
        Quaternion para orientación top-down:
        el eje Z del gripper apunta hacia abajo (-Z world).
        Rotación de 180° alrededor del eje X.
        """
        q         = Quaternion()
        q.x       = 1.0
        q.y       = 0.0
        q.z       = 0.0
        q.w       = 0.0
        return q

    # ────────────────────────────────────────────────────────────────────
    # MoveIt2 — envía goal
    # ────────────────────────────────────────────────────────────────────

    def _send_move_goal(self, target_pose: PoseStamped) -> None:
        """
        Construye y envía un MotionPlanRequest a move_group.
        Equivalente a MoveGroupInterface::setPoseTarget() en C++.
        """
        goal_msg = MoveGroup.Goal()

        # ── MotionPlanRequest ─────────────────────────────────────────────
        request                         = MotionPlanRequest()
        request.group_name              = self.planning_group
        request.num_planning_attempts   = 5
        request.allowed_planning_time   = self.planning_time
        request.max_velocity_scaling_factor    = self.velocity_scale
        request.max_acceleration_scaling_factor = self.velocity_scale * 0.5

        # Workspace — área donde puede planear
        request.workspace_parameters.header.frame_id = self.base_frame
        request.workspace_parameters.min_corner.x = -1.5
        request.workspace_parameters.min_corner.y = -1.5
        request.workspace_parameters.min_corner.z = -0.5
        request.workspace_parameters.max_corner.x =  1.5
        request.workspace_parameters.max_corner.y =  1.5
        request.workspace_parameters.max_corner.z =  2.0

        # ── Goal constraint — pose del end-effector ───────────────────────
        constraints = Constraints()

        # Posición
        pos_constraint                    = PositionConstraint()
        pos_constraint.header             = target_pose.header
        pos_constraint.link_name          = self.ee_frame
        pos_constraint.target_point_offset.x = 0.0
        pos_constraint.target_point_offset.y = 0.0
        pos_constraint.target_point_offset.z = 0.0

        # Tolerancia de posición — esfera de 1cm
        bv                                = BoundingVolume()
        sphere                            = SolidPrimitive()
        sphere.type                       = SolidPrimitive.SPHERE
        sphere.dimensions                 = [0.01]   # radio 1cm
        from geometry_msgs.msg import Pose
        sphere_pose                       = Pose()
        sphere_pose.position              = target_pose.pose.position
        sphere_pose.orientation.w         = 1.0
        bv.primitives.append(sphere)
        bv.primitive_poses.append(sphere_pose)
        pos_constraint.constraint_region  = bv
        pos_constraint.weight             = 1.0
        constraints.position_constraints.append(pos_constraint)

        # Orientación
        ori_constraint                    = OrientationConstraint()
        ori_constraint.header             = target_pose.header
        ori_constraint.link_name          = self.ee_frame
        ori_constraint.orientation        = target_pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 0.1   # ~6 grados
        ori_constraint.absolute_y_axis_tolerance = 0.1
        ori_constraint.absolute_z_axis_tolerance = 0.1
        ori_constraint.weight             = 1.0
        constraints.orientation_constraints.append(ori_constraint)

        request.goal_constraints.append(constraints)
        goal_msg.request   = request
        goal_msg.planning_options.plan_only           = False   # planea Y ejecuta
        goal_msg.planning_options.replan              = True
        goal_msg.planning_options.replan_attempts     = 3

        # ── Envía ─────────────────────────────────────────────────────────
        self.get_logger().info('Enviando goal a move_group...')
        send_goal_future = self.move_group_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback
        )
        send_goal_future.add_done_callback(self._goal_response_callback)

    # ────────────────────────────────────────────────────────────────────
    # Callbacks de MoveIt2
    # ────────────────────────────────────────────────────────────────────

    def _goal_response_callback(self, future) -> None:
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Goal rechazado por move_group')
            self.state = State.FAILED
            return

        self.get_logger().info('Goal aceptado — ejecutando...')
        self.state            = State.EXECUTING
        self.current_goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _feedback_callback(self, feedback_msg) -> None:
        # move_group no da feedback muy útil pero lo loggeamos
        pass

    def _result_callback(self, future) -> None:
        result = future.result().result
        status = future.result().status

        # error_code.val == 1 → SUCCESS en MoveIt2
        if result.error_code.val == 1:
            self.get_logger().info('✓ Movimiento completado exitosamente')
            self.state = State.SUCCESS
        else:
            self.get_logger().error(
                f'✗ Movimiento falló — error_code: {result.error_code.val}'
            )
            self.state = State.FAILED

        # Vuelve a IDLE después de éxito o fallo
        # En una implementación real aquí iría la lógica de pick & place
        # (bajar, cerrar gripper, subir, ir a drop-off, abrir gripper)
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        self.get_logger().info(f'Estado final: {self.state} → volviendo a IDLE')
        self.state = State.IDLE

    # ────────────────────────────────────────────────────────────────────
    # Status publisher
    # ────────────────────────────────────────────────────────────────────

    def _publish_status(self) -> None:
        msg      = String()
        msg.data = self.state
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TaskManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()