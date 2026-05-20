#!/usr/bin/env python3
"""
task_manager_node — robot_task_manager  (v5)
=============================================
Basado en v4 (funcionamiento correcto).

Cambio principal vs v4:
    Path constraint de orientación ELIMINADO del approach y drop libre.
    En su lugar, todos los movimientos POST-GRASP son cartesianos:

        approach  → OMPL libre     (sin objeto, orientación libre)
        descent   → cartesiano     (waypoint ya lleva orientación top-down)
        grip      → gripper close
        retreat   → cartesiano     (orientación fija, objeto en mano)
        drop      → cartesiano     (orientación fija, objeto en mano)
                    con fallback a OMPL si fraction < 0.9
        open      → gripper open

    Esto garantiza que tool0 apunte hacia abajo cuando hay objeto en el
    gripper, sin depender de path constraints que el planner OMPL rechaza.

Topics suscritos:
    /perception/object_clouds   (robot_interfaces/DetectedObjectCloudArray)

Topics publicados:
    /task_manager/status        (std_msgs/String)
    /gripper/command            (std_msgs/String)  → gripper_node

Servicios:
    /task_manager/set_target    (robot_interfaces/srv/SetTarget)
        label = "bottle" | "" (cualquier) | "STOP" (cancela)
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, Pose, Quaternion

# TF2
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_pose

# MoveIt2
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from moveit_msgs.msg import (
    MotionPlanRequest,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
    MoveItErrorCodes,
)
from moveit_msgs.srv import GetPositionIK, GetCartesianPath
from shape_msgs.msg import SolidPrimitive

from robot_interfaces.msg import DetectedObjectCloud, DetectedObjectCloudArray
from robot_interfaces.srv import SetTarget


# ── Estados ───────────────────────────────────────────────────────────────────
class State:
    IDLE       = 'IDLE'
    SEARCHING  = 'SEARCHING'
    PLANNING   = 'PLANNING'
    EXECUTING  = 'EXECUTING'
    GRASPING   = 'GRASPING'
    GRIPPING   = 'GRIPPING'
    RETREATING = 'RETREATING'
    DROPPING   = 'DROPPING'
    SUCCESS    = 'SUCCESS'
    FAILED     = 'FAILED'


class TaskManagerNode(Node):

    def __init__(self):
        super().__init__('task_manager_node')

        # ── Parámetros ───────────────────────────────────────────────────
        self.declare_parameter('planning_group',    'irb14050_arm')
        self.declare_parameter('base_frame',        'base_link')
        self.declare_parameter('ee_frame',          'tool0')
        self.declare_parameter('target_label',      '')
        self.declare_parameter('approach_offset_z', 0.10)
        self.declare_parameter('grasp_offset_z',    0.01)
        self.declare_parameter('retreat_offset_z',  0.15)
        self.declare_parameter('planning_time',     5.0)
        self.declare_parameter('velocity_scale',    0.15)
        self.declare_parameter('gripper_wait',      1.0)
        self.declare_parameter('watchdog_timeout',  120.0)
        self.declare_parameter('drop_x',            -0.3)
        self.declare_parameter('drop_y',            0.0)
        self.declare_parameter('drop_z',           0.20)

        self.planning_group    = self.get_parameter('planning_group').value
        self.base_frame        = self.get_parameter('base_frame').value
        self.ee_frame          = self.get_parameter('ee_frame').value
        self.target_label      = self.get_parameter('target_label').value
        self.approach_offset_z = self.get_parameter('approach_offset_z').value
        self.grasp_offset_z    = self.get_parameter('grasp_offset_z').value
        self.retreat_offset_z  = self.get_parameter('retreat_offset_z').value
        self.planning_time     = self.get_parameter('planning_time').value
        self.velocity_scale    = self.get_parameter('velocity_scale').value
        self.gripper_wait      = self.get_parameter('gripper_wait').value
        self.watchdog_timeout  = self.get_parameter('watchdog_timeout').value
        self.drop_x            = self.get_parameter('drop_x').value
        self.drop_y            = self.get_parameter('drop_y').value
        self.drop_z            = self.get_parameter('drop_z').value

        # ── Estado interno ────────────────────────────────────────────────
        self.state                  = State.IDLE
        self.current_goal_handle    = None
        self.current_grasp_pose     = None
        self._pending_done_callback = None
        self._grip_timer            = None
        self._drop_timer            = None
        self.watchdog_timer         = None

        # ── TF2 ──────────────────────────────────────────────────────────
        self.tf_buffer   = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ── Action clients ────────────────────────────────────────────────
        self.move_group_client = ActionClient(self, MoveGroup, '/move_action')
        self.execute_client    = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

        self.get_logger().info('Esperando move_group y execute_trajectory...')
        self.move_group_client.wait_for_server()
        self.execute_client.wait_for_server()
        self.get_logger().info('Action servers conectados')

        # ── Service clients ───────────────────────────────────────────────
        self.ik_client        = self.create_client(GetPositionIK,    '/compute_ik')
        self.cartesian_client = self.create_client(GetCartesianPath, '/compute_cartesian_path')

        # ── Publisher gripper ─────────────────────────────────────────────
        self.gripper_pub = self.create_publisher(String, '/gripper/command', 10)

        # ── Subscriber percepción ─────────────────────────────────────────
        self.create_subscription(
            DetectedObjectCloudArray,
            '/perception/object_clouds',
            self._detections_callback,
            10
        )

        # ── Servicio set_target ───────────────────────────────────────────
        self.create_service(
            SetTarget,
            '/task_manager/set_target',
            self._set_target_callback
        )

        # ── Publisher status ──────────────────────────────────────────────
        self.status_pub = self.create_publisher(String, '/task_manager/status', 10)
        self.create_timer(1.0, self._publish_status)

        self._gripper_command('open')

        self.get_logger().info(
            f'TaskManagerNode listo — '
            f'group: {self.planning_group} | '
            f'target: "{self.target_label or "cualquier objeto"}"'
        )

    # ────────────────────────────────────────────────────────────────────
    # Servicio set_target
    # ────────────────────────────────────────────────────────────────────

    def _set_target_callback(self, request, response):
        if request.label == 'STOP':
            if self.current_goal_handle is not None:
                self.current_goal_handle.cancel_goal_async()
                self.get_logger().warn('Movimiento cancelado por STOP')
            self._gripper_command('open')
            self._reset_to_idle()
            response.success = True
            response.message = 'Movimiento cancelado'
            return response

        self.target_label = request.label
        self.state        = State.SEARCHING
        response.success  = True
        response.message  = f'Target seteado a: "{self.target_label or "cualquier objeto"}"'
        self.get_logger().info(response.message)
        return response

    # ────────────────────────────────────────────────────────────────────
    # Callback percepción
    # ────────────────────────────────────────────────────────────────────

    def _detections_callback(self, msg: DetectedObjectCloudArray) -> None:
        if self.state != State.SEARCHING:
            return

        if not msg.objects:
            return

        candidates = []
        for obj in msg.objects:
            if self.target_label and obj.label != self.target_label:
                continue
            if not obj.centroid_valid:
                continue
            pose_base = self._transform_to_base_link(obj)
            if pose_base is not None:
                candidates.append((obj, pose_base))

        if not candidates:
            self.get_logger().debug(
                f'No se encontró "{self.target_label}"',
                throttle_duration_sec=2.0
            )
            return

        # Selección por distancia euclidiana XY en base_link
        obj, pose_base = min(
            candidates,
            key=lambda item: math.sqrt(
                item[1].pose.position.x ** 2 +
                item[1].pose.position.y ** 2
            )
        )

        self.get_logger().info(
            f'Target: [{obj.label}] en base_link '
            f'({pose_base.pose.position.x:.3f}, '
            f'{pose_base.pose.position.y:.3f}, '
            f'{pose_base.pose.position.z:.3f})m'
        )

        approach_pose           = self._compute_approach_pose(pose_base)
        self.current_grasp_pose = self._compute_grasp_descent_pose(pose_base)

        self.state = State.PLANNING
        self._start_watchdog()

        # Approach con OMPL libre — sin path constraint
        self._send_move_goal(approach_pose, done_callback=self._on_approach_done)

    # ────────────────────────────────────────────────────────────────────
    # TF2
    # ────────────────────────────────────────────────────────────────────

    def _transform_to_base_link(self, obj: DetectedObjectCloud) -> PoseStamped | None:
        pose_cam                    = PoseStamped()
        pose_cam.header.frame_id    = obj.header.frame_id
        pose_cam.header.stamp       = obj.header.stamp
        pose_cam.pose.position.x    = float(obj.centroid_x)
        pose_cam.pose.position.y    = float(obj.centroid_y)
        pose_cam.pose.position.z    = float(obj.centroid_z)
        pose_cam.pose.orientation.w = 1.0

        try:
            transform = self.tf_buffer.lookup_transform(
                self.base_frame,
                pose_cam.header.frame_id,
                pose_cam.header.stamp,
                timeout=Duration(seconds=1.0)
            )
            result                  = PoseStamped()
            result.header.frame_id  = self.base_frame
            result.header.stamp     = pose_cam.header.stamp
            result.pose             = do_transform_pose(pose_cam.pose, transform)
            return result

        except TransformException as e:
            self.get_logger().error(f'TF lookup falló: {e}')
            return None

    # ────────────────────────────────────────────────────────────────────
    # Orientación top-down
    # ────────────────────────────────────────────────────────────────────

    def _top_down_orientation(self) -> Quaternion:
        """
        Orientación top-down para ABB tool0.
        VERIFICAR en RViz antes de mover el robot real.
        """
        q   = Quaternion()
        q.x = 1.0
        q.y = 0.0
        q.z = 0.0
        q.w = 0.0
        return q

    # ────────────────────────────────────────────────────────────────────
    # Poses del pipeline
    # ────────────────────────────────────────────────────────────────────

    def _compute_approach_pose(self, pose_base: PoseStamped) -> PoseStamped:
        """Approach — sobre el objeto. OMPL puede elegir la orientación libremente."""
        p                  = PoseStamped()
        p.header           = pose_base.header
        p.pose.position.x  = pose_base.pose.position.x
        p.pose.position.y  = pose_base.pose.position.y
        p.pose.position.z  = pose_base.pose.position.z + self.approach_offset_z
        p.pose.orientation = self._top_down_orientation()
        return p

    def _compute_grasp_descent_pose(self, pose_base: PoseStamped) -> PoseStamped:
        """Pose de contacto con el objeto — usada en cartesiano."""
        p                  = PoseStamped()
        p.header           = pose_base.header
        p.pose.position.x  = pose_base.pose.position.x
        p.pose.position.y  = pose_base.pose.position.y
        p.pose.position.z  = pose_base.pose.position.z + self.grasp_offset_z
        p.pose.orientation = self._top_down_orientation()
        return p

    def _compute_retreat_pose(self) -> PoseStamped | None:
        """Retiro — sube retreat_offset_z desde la pose de grasp."""
        if self.current_grasp_pose is None:
            return None
        p                  = PoseStamped()
        p.header           = self.current_grasp_pose.header
        p.pose.position.x  = self.current_grasp_pose.pose.position.x
        p.pose.position.y  = self.current_grasp_pose.pose.position.y
        p.pose.position.z  = self.current_grasp_pose.pose.position.z + self.retreat_offset_z
        p.pose.orientation = self._top_down_orientation()
        return p

    def _compute_drop_pose(self) -> PoseStamped:
        """Drop zone — posición fija en yaml."""
        p                  = PoseStamped()
        p.header.frame_id  = self.base_frame
        p.header.stamp     = self.get_clock().now().to_msg()
        p.pose.position.x  = self.drop_x
        p.pose.position.y  = self.drop_y
        p.pose.position.z  = self.drop_z
        p.pose.orientation = self._top_down_orientation()
        return p

    # ────────────────────────────────────────────────────────────────────
    # Gripper
    # ────────────────────────────────────────────────────────────────────

    def _gripper_command(self, cmd: str) -> None:
        """cmd: 'open' | 'close' | 'standby'"""
        msg      = String()
        msg.data = cmd
        self.gripper_pub.publish(msg)
        self.get_logger().info(f'Gripper: {cmd}')

    # ────────────────────────────────────────────────────────────────────
    # Pipeline pick & place
    # ────────────────────────────────────────────────────────────────────

    def _on_approach_done(self, success: bool) -> None:
        """Llegó al approach — baja en línea recta (cartesiano)."""
        if not success:
            self.get_logger().error('Approach falló')
            self._reset_to_idle()
            return

        self.get_logger().info('Approach OK → bajando al objeto (cartesiano)')
        self.state = State.GRASPING
        self._start_watchdog()

        if self.current_grasp_pose is None:
            self._reset_to_idle()
            return

        self._execute_cartesian(
            self.current_grasp_pose,
            done_callback=self._on_grasp_done
        )

    def _on_grasp_done(self, success: bool) -> None:
        """En pose de grasp — cierra el gripper."""
        if not success:
            self.get_logger().error('Descenso al objeto falló')
            self._reset_to_idle()
            return

        self.get_logger().info('En pose de grasp → cerrando gripper')
        self.state = State.GRIPPING
        self._gripper_command('close')

        self._grip_timer = self.create_timer(self.gripper_wait, self._after_grip)

    def _after_grip(self) -> None:
        if self._grip_timer is not None:
            self._grip_timer.cancel()
            self._grip_timer = None

        self.get_logger().info('Gripper cerrado → retirando (cartesiano)')
        self.state = State.RETREATING
        self._start_watchdog()

        retreat_pose = self._compute_retreat_pose()
        if retreat_pose is None:
            self._reset_to_idle()
            return

        self._execute_cartesian(retreat_pose, done_callback=self._on_retreat_done)

    def _on_retreat_done(self, success: bool) -> None:
        """Retirado — va a drop zone en cartesiano con fallback a OMPL."""
        if not success:
            self.get_logger().error('Retiro falló — abriendo gripper por seguridad')
            self._gripper_command('open')
            self._reset_to_idle()
            return

        self.get_logger().info('Retiro OK → yendo a drop zone (cartesiano)')
        self.state = State.DROPPING
        self._start_watchdog()

        # Intenta cartesiano primero — mantiene orientación con objeto en mano
        # Si fraction < 0.9 cae a OMPL con goal constraint de orientación
        self._execute_cartesian(
            self._compute_drop_pose(),
            done_callback=self._on_drop_done,
            fallback_to_ompl=True
        )

    def _on_drop_done(self, success: bool) -> None:
        """En drop zone — abre el gripper."""
        if not success:
            self.get_logger().error('No llegó a drop zone — abriendo gripper aquí')

        self.get_logger().info('Drop zone → abriendo gripper')
        self._gripper_command('open')

        self._drop_timer = self.create_timer(self.gripper_wait, self._finish_pick)

    def _finish_pick(self) -> None:
        if self._drop_timer is not None:
            self._drop_timer.cancel()
            self._drop_timer = None

        self.get_logger().info('✓ Pick & place completado')
        self.state = State.SUCCESS
        self._reset_to_idle()

    # ────────────────────────────────────────────────────────────────────
    # MoveIt2 — OMPL libre (solo para approach)
    # Sin path constraint — el planner elige la trayectoria libremente
    # ────────────────────────────────────────────────────────────────────

    def _send_move_goal(self, target_pose: PoseStamped, done_callback) -> None:
        goal_msg = MoveGroup.Goal()
        request  = MotionPlanRequest()

        request.group_name                       = self.planning_group
        request.num_planning_attempts            = 5
        request.allowed_planning_time            = self.planning_time
        request.max_velocity_scaling_factor      = self.velocity_scale
        request.max_acceleration_scaling_factor  = self.velocity_scale * 0.5

        request.workspace_parameters.header.frame_id = self.base_frame
        request.workspace_parameters.min_corner.x    = -0.6
        request.workspace_parameters.min_corner.y    = -0.6
        request.workspace_parameters.min_corner.z    = -0.2
        request.workspace_parameters.max_corner.x    =  0.6
        request.workspace_parameters.max_corner.y    =  0.6
        request.workspace_parameters.max_corner.z    =  0.8

        goal_constraints = Constraints()

        # Posición — esfera de 1cm
        pos_c                     = PositionConstraint()
        pos_c.header              = target_pose.header
        pos_c.link_name           = self.ee_frame
        pos_c.weight              = 1.0
        bv                        = BoundingVolume()
        sphere                    = SolidPrimitive()
        sphere.type               = SolidPrimitive.SPHERE
        sphere.dimensions         = [0.01]
        sphere_pose               = Pose()
        sphere_pose.position      = target_pose.pose.position
        sphere_pose.orientation.w = 1.0
        bv.primitives.append(sphere)
        bv.primitive_poses.append(sphere_pose)
        pos_c.constraint_region   = bv
        goal_constraints.position_constraints.append(pos_c)

        # Orientación en el goal (solo en el punto final, no en tránsito)
        ori_c                           = OrientationConstraint()
        ori_c.header                    = target_pose.header
        ori_c.link_name                 = self.ee_frame
        ori_c.orientation               = self._top_down_orientation()
        ori_c.absolute_x_axis_tolerance = 0.1
        ori_c.absolute_y_axis_tolerance = 0.1
        ori_c.absolute_z_axis_tolerance = 0.1
        ori_c.weight                    = 1.0
        goal_constraints.orientation_constraints.append(ori_c)

        request.goal_constraints.append(goal_constraints)

        # Sin path_constraints — OMPL libre para el approach
        goal_msg.request                          = request
        goal_msg.planning_options.plan_only       = False
        goal_msg.planning_options.replan          = True
        goal_msg.planning_options.replan_attempts = 3

        self._pending_done_callback = done_callback

        future = self.move_group_client.send_goal_async(goal_msg)
        future.add_done_callback(self._goal_response_callback)

    # ────────────────────────────────────────────────────────────────────
    # MoveIt2 — cartesiano (todos los movimientos post-grasp)
    # La orientación top-down se garantiza porque el waypoint ya la lleva
    # ────────────────────────────────────────────────────────────────────

    def _execute_cartesian(
        self,
        target_pose: PoseStamped,
        done_callback,
        fallback_to_ompl: bool = False
    ) -> None:
        """
        Movimiento en línea recta.
        Si fallback_to_ompl=True y fraction < 0.9, intenta con OMPL + goal
        constraint de orientación en vez de fallar directamente.
        Útil para la drop zone que puede no ser alcanzable en línea recta.
        """
        if not self.cartesian_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error('compute_cartesian_path no disponible')
            if fallback_to_ompl:
                self.get_logger().warn('Fallback a OMPL para drop zone')
                self._send_move_goal(target_pose, done_callback)
            else:
                done_callback(False)
            return

        req                  = GetCartesianPath.Request()
        req.header           = target_pose.header
        req.group_name       = self.planning_group
        req.link_name        = self.ee_frame
        req.waypoints        = [target_pose.pose]
        req.max_step         = 0.005
        req.jump_threshold   = 0.0
        req.avoid_collisions = True
        req.max_velocity_scaling_factor     = self.velocity_scale * 0.5
        req.max_acceleration_scaling_factor = self.velocity_scale * 0.25

        future = self.cartesian_client.call_async(req)
        future.add_done_callback(
            lambda f: self._on_cartesian_computed(
                f, done_callback, target_pose, fallback_to_ompl
            )
        )

    def _on_cartesian_computed(
        self,
        future,
        done_callback,
        target_pose: PoseStamped,
        fallback_to_ompl: bool
    ) -> None:
        result = future.result()

        if result is None:
            self.get_logger().error('compute_cartesian_path no respondió')
            if fallback_to_ompl:
                self.get_logger().warn('Fallback a OMPL (sin respuesta del servicio)')
                self._send_move_goal(target_pose, done_callback)
            else:
                done_callback(False)
            return

        if result.fraction < 0.9:
            self.get_logger().warn(
                f'Cartesian path incompleto fraction={result.fraction:.2f}'
            )
            if fallback_to_ompl:
                self.get_logger().warn(
                    f'fraction={result.fraction:.2f} < 0.9 → '
                    'fallback a OMPL para drop zone'
                )
                self._send_move_goal(target_pose, done_callback)
            else:
                self.get_logger().error(
                    'Cartesian path incompleto — posible colisión en el camino'
                )
                done_callback(False)
            return

        self.get_logger().info(
            f'Cartesian path OK fraction={result.fraction:.2f} '
            f'puntos={len(result.solution.joint_trajectory.points)}'
        )

        exec_goal            = ExecuteTrajectory.Goal()
        exec_goal.trajectory = result.solution

        self._pending_done_callback = done_callback

        exec_future = self.execute_client.send_goal_async(exec_goal)
        exec_future.add_done_callback(self._execute_goal_response_callback)

    def _execute_goal_response_callback(self, future) -> None:
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('ExecuteTrajectory rechazado')
            cb = self._pending_done_callback
            self._pending_done_callback = None
            if cb:
                cb(False)
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._execute_result_callback)

    def _execute_result_callback(self, future) -> None:
        self._cancel_watchdog()
        result  = future.result().result
        success = result.error_code.val == MoveItErrorCodes.SUCCESS

        if not success:
            self.get_logger().error(
                f'ExecuteTrajectory falló — error_code: {result.error_code.val}'
            )

        cb = self._pending_done_callback
        self._pending_done_callback = None
        if cb:
            cb(success)

    # ────────────────────────────────────────────────────────────────────
    # MoveGroup callbacks
    # ────────────────────────────────────────────────────────────────────

    def _goal_response_callback(self, future) -> None:
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Goal rechazado por move_group')
            cb = self._pending_done_callback
            self._pending_done_callback = None
            if cb:
                cb(False)
            return

        self.get_logger().info(f'Goal aceptado — estado: {self.state}')
        self.current_goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _result_callback(self, future) -> None:
        self._cancel_watchdog()
        result  = future.result().result
        success = result.error_code.val == MoveItErrorCodes.SUCCESS

        if success:
            self.get_logger().info(f'✓ Movimiento OK — estado: {self.state}')
        else:
            self.get_logger().error(
                f'✗ Movimiento falló — error_code: {result.error_code.val} '
                f'estado: {self.state}'
            )

        cb = self._pending_done_callback
        self._pending_done_callback = None
        if cb:
            cb(success)

    # ────────────────────────────────────────────────────────────────────
    # Watchdog
    # ────────────────────────────────────────────────────────────────────

    def _start_watchdog(self) -> None:
        self._cancel_watchdog()
        self.watchdog_timer = self.create_timer(
            self.watchdog_timeout, self._watchdog_timeout
        )

    def _cancel_watchdog(self) -> None:
        if self.watchdog_timer is not None:
            self.watchdog_timer.cancel()
            self.watchdog_timer = None

    def _watchdog_timeout(self) -> None:
        self.get_logger().error(
            f'Watchdog timeout ({self.watchdog_timeout}s) en estado {self.state} — abortando'
        )
        if self.current_goal_handle is not None:
            self.current_goal_handle.cancel_goal_async()
        self._gripper_command('open')
        self._reset_to_idle()

    # ────────────────────────────────────────────────────────────────────
    # Reset
    # ────────────────────────────────────────────────────────────────────

    def _reset_to_idle(self) -> None:
        self.get_logger().info(f'→ IDLE (venía de {self.state})')
        self._cancel_watchdog()

        if self._grip_timer is not None:
            self._grip_timer.cancel()
            self._grip_timer = None
        if self._drop_timer is not None:
            self._drop_timer.cancel()
            self._drop_timer = None

        self.state                  = State.IDLE
        self.current_goal_handle    = None
        self.current_grasp_pose     = None
        self._pending_done_callback = None

    # ────────────────────────────────────────────────────────────────────
    # Status
    # ────────────────────────────────────────────────────────────────────

    def _publish_status(self) -> None:
        msg      = String()
        msg.data = self.state
        self.status_pub.publish(msg)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)

    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    node     = TaskManagerNode()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()