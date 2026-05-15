"""
egm_moveit_executor.py

Action server que conecta MoveIt 2 con el egm_bridge.

Expone:
    /irb14050_arm_controller/follow_joint_trajectory
        (control_msgs/action/FollowJointTrajectory)

Suscribe:
    /joint_states (sensor_msgs/JointState)
        - publicado por egm_bridge con la pose REAL del robot

Publica:
    /joint_command (sensor_msgs/JointState)
        - el bridge se encarga de interpolar suavemente hacia ese
          target a su tasa interna de 250 Hz

Diseño:
    Cuando MoveIt manda una trayectoria con N waypoints, este nodo
    los publica uno a uno respetando el `time_from_start` de cada
    punto. El bridge interpola entre waypoints (no este nodo), lo
    cual aprovecha la lógica de slew rate y límites que ya tiene
    el bridge.

    Al final, espera a que la pose real converja al último
    waypoint dentro de una tolerancia (POSITION_TOLERANCE_RAD)
    antes de marcar el goal como SUCCEEDED.

Importante:
    El controlador no funciona como un PID estricto: el bridge ya
    es responsable de la dinámica del seguimiento. Este executor
    solo cadencia los setpoints. Si MoveIt pide aceleraciones que
    el bridge no puede sostener (por su MAX_SPEED_DEG_S interno),
    el bridge limitará la velocidad y el seguimiento ira "atrás",
    pero la trayectoria seguirá siendo válida (solo más lenta).
"""

import math
import time
from threading import Lock

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from sensor_msgs.msg import JointState
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


# --- Tunables -------------------------------------------------------

EXPECTED_JOINTS = [
    'joint_1', 'joint_2', 'joint_3',
    'joint_4', 'joint_5', 'joint_6',
    'joint_7',
]

# Tolerancia para considerar que el robot llegó al último waypoint.
# 1° ≈ 0.017 rad. Pongo 2° de margen porque el bridge tiene su
# propio slew rate y a veces el "settle" tarda un tick extra.
POSITION_TOLERANCE_RAD = math.radians(3.0)

# Timeout para que el robot termine de converger al último
# waypoint después de haber publicado el último setpoint.
SETTLE_TIMEOUT_S = 8.0

# Tasa de cadencia interna. Cada tick comprueba si toca publicar
# el siguiente waypoint y si toca enviar feedback al cliente.
TICK_HZ = 50.0


# --- Nodo -----------------------------------------------------------

class EgmMoveitExecutor(Node):

    def __init__(self):
        super().__init__('egm_moveit_executor')

        # Callback group reentrante: necesitamos que el subscriber
        # de joint_states siga leyendo MIENTRAS el action server
        # está ejecutando un goal.
        cb_group = ReentrantCallbackGroup()

        # --- Estado actual del robot, alimentado por joint_states ---
        self._latest_q = None  # dict[joint_name -> position (rad)]
        self._latest_q_lock = Lock()

        self.create_subscription(
            JointState, '/joint_states',
            self._on_joint_states, 10,
            callback_group=cb_group,
        )

        # --- Publisher al bridge ---
        self._cmd_pub = self.create_publisher(
            JointState, '/joint_command', 10,
        )

        # --- Action server que MoveIt llamará ---
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/irb14050_arm_controller/follow_joint_trajectory',
            execute_callback=self._execute_cb,
            goal_callback=self._on_goal,
            cancel_callback=self._on_cancel,
            callback_group=cb_group,
        )

        self.get_logger().info(
            'egm_moveit_executor ready. '
            'Action: /irb14050_arm_controller/follow_joint_trajectory'
        )

    # --- Callbacks de joint_states ---------------------------------

    def _on_joint_states(self, msg: JointState):
        """Guarda la última pose en un dict para acceso rápido."""
        with self._latest_q_lock:
            self._latest_q = {
                name: pos
                for name, pos in zip(msg.name, msg.position)
            }

    def _read_current_q(self):
        """Devuelve la pose actual ordenada según EXPECTED_JOINTS."""
        with self._latest_q_lock:
            if self._latest_q is None:
                return None
            try:
                return [self._latest_q[j] for j in EXPECTED_JOINTS]
            except KeyError:
                return None

    # --- Action server callbacks -----------------------------------

    def _on_goal(self, goal_request):
        """Acepta cualquier goal mientras tengamos joint_states."""
        if self._read_current_q() is None:
            self.get_logger().warn(
                'Rejecting goal: no joint_states received yet'
            )
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _on_cancel(self, _goal_handle):
        """Cancelación: la aceptamos siempre, el ejecutor verifica."""
        return CancelResponse.ACCEPT

    def _execute_cb(self, goal_handle: ServerGoalHandle):
        """
        Ejecuta una trayectoria FollowJointTrajectory.

        Pasos:
          1. Validar que los joints coinciden con los del bridge.
          2. Para cada punto, esperar a `time_from_start` y publicar.
          3. Esperar a que el robot converja al último punto.
          4. Marcar SUCCEEDED o ABORTED según el resultado.
        """
        trajectory = goal_handle.request.trajectory
        joint_order = list(trajectory.joint_names)
        points = list(trajectory.points)
        n_points = len(points)

        self.get_logger().info(
            f'Executing trajectory: {n_points} waypoints, '
            f'joints={joint_order}'
        )

        # --- Validación de joints ---
        if set(joint_order) != set(EXPECTED_JOINTS):
            self.get_logger().error(
                f'Joint name mismatch. Got {joint_order}, '
                f'expected {EXPECTED_JOINTS}'
            )
            goal_handle.abort()
            return self._make_result(
                FollowJointTrajectory.Result.INVALID_JOINTS,
                'joint name mismatch'
            )

        if n_points == 0:
            goal_handle.abort()
            return self._make_result(
                FollowJointTrajectory.Result.INVALID_GOAL,
                'empty trajectory'
            )

        # Mapeo del orden recibido al orden EXPECTED_JOINTS
        # (MoveIt puede mandar los joints en cualquier orden)
        index_map = [joint_order.index(j) for j in EXPECTED_JOINTS]

        # --- Ejecución de los waypoints ---
        start_time = time.monotonic()
        tick_dt = 1.0 / TICK_HZ
        next_idx = 0

        while next_idx < n_points:
            # Comprobar cancelación
            if goal_handle.is_cancel_requested:
                self.get_logger().info('Goal canceled by client')
                goal_handle.canceled()
                return self._make_result(
                    FollowJointTrajectory.Result.PATH_TOLERANCE_VIOLATED,
                    'canceled'
                )

            elapsed = time.monotonic() - start_time
            target_t = self._point_time_s(points[next_idx])

            if elapsed >= target_t:
                # Toca publicar este waypoint
                self._publish_waypoint(points[next_idx], index_map)
                next_idx += 1

                # Feedback opcional para el cliente
                self._send_feedback(
                    goal_handle, joint_order,
                    points[next_idx - 1],
                )

            time.sleep(tick_dt)

        # --- Esperar convergencia al último waypoint ---
        last_point = points[-1]
        target_q = [last_point.positions[i] for i in index_map]
        ok = self._wait_until_converged(target_q, goal_handle)

        if not ok:
            goal_handle.abort()
            return self._make_result(
                FollowJointTrajectory.Result.GOAL_TOLERANCE_VIOLATED,
                'did not converge within tolerance'
            )

        self.get_logger().info('Trajectory executed successfully')
        goal_handle.succeed()
        return self._make_result(
            FollowJointTrajectory.Result.SUCCESSFUL, 'ok'
        )

    # --- Helpers ---------------------------------------------------

    def _point_time_s(self, point: JointTrajectoryPoint) -> float:
        """time_from_start en segundos como float."""
        return point.time_from_start.sec + \
               point.time_from_start.nanosec * 1e-9

    def _publish_waypoint(self, point: JointTrajectoryPoint,
                          index_map):
        """Publica un waypoint a /joint_command."""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = EXPECTED_JOINTS
        msg.position = [point.positions[i] for i in index_map]
        self._cmd_pub.publish(msg)

    def _send_feedback(self, goal_handle, joint_order, point):
        """Envía feedback no-bloqueante al cliente del action."""
        fb = FollowJointTrajectory.Feedback()
        fb.joint_names = joint_order
        fb.desired = point  # el waypoint que acabamos de mandar
        # actual / error son opcionales, los dejamos vacíos por ahora
        goal_handle.publish_feedback(fb)

    def _wait_until_converged(self, target_q, goal_handle):
        """Espera a que la pose real esté dentro de tolerancia."""
        deadline = time.monotonic() + SETTLE_TIMEOUT_S
        tick_dt = 1.0 / TICK_HZ

        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested:
                return False

            current_q = self._read_current_q()
            if current_q is not None:
                err = max(
                    abs(c - t)
                    for c, t in zip(current_q, target_q)
                )
                if err < POSITION_TOLERANCE_RAD:
                    return True

            time.sleep(tick_dt)

        return False  # timeout

    @staticmethod
    def _make_result(error_code, msg):
        """Construye un FollowJointTrajectory.Result."""
        result = FollowJointTrajectory.Result()
        result.error_code = error_code
        result.error_string = msg
        return result


# --- Entry point ---------------------------------------------------

def main():
    rclpy.init()
    node = EgmMoveitExecutor()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
