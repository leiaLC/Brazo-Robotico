#!/usr/bin/env python3
"""
moveit_sequence_player.py

Reproduce una secuencia de pasos definida en YAML usando MoveIt2.
Cada paso es uno de:
    - {type: pose, joints_deg: [j1, j2, ..., j7]}
    - {type: gripper, action: open|close|standby}

Funciona contra Gazebo (sim) sin cambios. En modo real, los pasos de gripper
se publican al topic /gripper/command (std_msgs/String) en lugar de planearse
con MoveIt — útil cuando el gripper físico se controla vía RWS y no por
ros2_control.

Uso:
    ros2 run abb_irb14050_egm moveit_sequence_player \\
        --ros-args -p yaml_path:=/ruta/al/pick_demo.yaml -p sim_mode:=true
"""

import math
import time
import yaml
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
)
from std_msgs.msg import String


# ---- Configuración del robot (debe coincidir con el SRDF) ---------------
ARM_GROUP = 'irb14050_arm'
ARM_JOINTS = [f'joint_{i}' for i in range(1, 8)]

GRIPPER_GROUP = 'gripper'
GRIPPER_JOINTS = ['gripper_joint_l', 'gripper_joint_r']

# Valores de las poses nombradas del SRDF — si los cambias allá, cámbialos aquí
GRIPPER_NAMED_POSES = {
    'open':  {'gripper_joint_l': 0.025, 'gripper_joint_r': 0.025},
    'close': {'gripper_joint_l': 0.0,   'gripper_joint_r': 0.0},
}

# Mapeo "action" del YAML → pose nombrada (sim) / comando String (real)
GRIPPER_ACTION_TO_SIM_POSE = {
    'open':  'open',
    'close': 'close',
}
GRIPPER_ACTION_TO_REAL_CMD = {
    'open':    'OPEN',
    'close':   'CLOSE',
    'standby': 'STANDBY',
}

MOVEIT_SUCCESS = 1  # moveit_msgs/MoveItErrorCodes.SUCCESS


class MoveItSequencePlayer(Node):

    def __init__(self):
        super().__init__('moveit_sequence_player')

        # ---- Parámetros ---------------------------------------------------
        self.declare_parameter('yaml_path', '')
        self.declare_parameter('sim_mode', True)
        self.declare_parameter('planning_time_s', 5.0)
        self.declare_parameter('planning_attempts', 5)
        self.declare_parameter('velocity_scaling', 0.3)
        self.declare_parameter('acceleration_scaling', 0.3)
        self.declare_parameter('pause_between_steps_s', 0.3)
        self.declare_parameter('gripper_real_settle_s', 1.5)

        self.yaml_path = self.get_parameter('yaml_path').value
        self.sim_mode = bool(self.get_parameter('sim_mode').value)

        # ---- ROS interfaces ----------------------------------------------
        self.move_action_client = ActionClient(self, MoveGroup, '/move_action')
        self.gripper_pub = self.create_publisher(String, '/gripper/command', 10)

        self.get_logger().info(
            f"Sequence player listo (sim_mode={self.sim_mode}, "
            f"yaml='{self.yaml_path}')"
        )

    # ----------------------------------------------------------------------
    # Inicialización
    # ----------------------------------------------------------------------

    def wait_for_servers(self, timeout_s: float = 10.0) -> bool:
        self.get_logger().info('Esperando a /move_action...')
        ok = self.move_action_client.wait_for_server(timeout_sec=timeout_s)
        if not ok:
            self.get_logger().error('/move_action no disponible. ¿MoveIt arriba?')
            return False
        self.get_logger().info('OK, /move_action listo')
        return True

    # ----------------------------------------------------------------------
    # Reproducción de la secuencia
    # ----------------------------------------------------------------------

    def play(self) -> bool:
        if not self.yaml_path:
            self.get_logger().error('Parámetro yaml_path vacío')
            return False

        path = Path(self.yaml_path).expanduser()
        if not path.exists():
            self.get_logger().error(f'YAML no existe: {path}')
            return False

        with open(path) as f:
            data = yaml.safe_load(f)

        seq_name = data.get('name', '<sin nombre>')
        steps = data.get('steps', [])
        self.get_logger().info(
            f"Reproduciendo '{seq_name}' — {len(steps)} pasos"
        )

        pause = float(self.get_parameter('pause_between_steps_s').value)

        for i, step in enumerate(steps, start=1):
            stype = step.get('type')
            self.get_logger().info(f'[{i}/{len(steps)}] tipo={stype}')

            if stype == 'pose':
                joints_deg = step.get('joints_deg', [])
                if len(joints_deg) != 7:
                    self.get_logger().error(
                        f'  Pose con {len(joints_deg)} joints (esperaba 7)'
                    )
                    return False
                joints_rad = [math.radians(d) for d in joints_deg]
                ok = self._execute_arm_pose(joints_rad)

            elif stype == 'gripper':
                action = step.get('action', '').lower()
                ok = self._execute_gripper(action)

            else:
                self.get_logger().warn(f'  Tipo desconocido "{stype}", saltando')
                ok = True

            if not ok:
                self.get_logger().error(f'Paso {i} falló — abortando secuencia')
                return False

            time.sleep(pause)

        self.get_logger().info('Secuencia completada')
        return True

    # ----------------------------------------------------------------------
    # Ejecución de pasos individuales
    # ----------------------------------------------------------------------

    def _execute_arm_pose(self, joints_rad) -> bool:
        constraints = self._make_joint_constraints(ARM_JOINTS, joints_rad)
        return self._send_move_group_goal(ARM_GROUP, constraints)

    def _execute_gripper(self, action: str) -> bool:
        if self.sim_mode:
            if action not in GRIPPER_ACTION_TO_SIM_POSE:
                self.get_logger().warn(
                    f'  Acción gripper "{action}" no mapeada en sim — saltando'
                )
                return True
            pose_name = GRIPPER_ACTION_TO_SIM_POSE[action]
            pose_vals = GRIPPER_NAMED_POSES[pose_name]
            joint_vals = [pose_vals[j] for j in GRIPPER_JOINTS]
            constraints = self._make_joint_constraints(GRIPPER_JOINTS, joint_vals)
            self.get_logger().info(f'  Gripper → "{pose_name}" (sim, vía MoveIt)')
            return self._send_move_group_goal(GRIPPER_GROUP, constraints)

        # Modo real: publicar al topic del gripper_node RWS
        cmd = GRIPPER_ACTION_TO_REAL_CMD.get(action, action.upper())
        msg = String(data=cmd)
        self.gripper_pub.publish(msg)
        self.get_logger().info(f'  Gripper → "{cmd}" (real, vía /gripper/command)')
        time.sleep(float(self.get_parameter('gripper_real_settle_s').value))
        return True

    # ----------------------------------------------------------------------
    # Construcción y envío del goal a MoveIt
    # ----------------------------------------------------------------------

    def _make_joint_constraints(
        self, joint_names, joint_values, tolerance: float = 1e-3
    ) -> Constraints:
        c = Constraints()
        for name, val in zip(joint_names, joint_values):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = float(val)
            jc.tolerance_above = tolerance
            jc.tolerance_below = tolerance
            jc.weight = 1.0
            c.joint_constraints.append(jc)
        return c

    def _send_move_group_goal(self, group_name: str, goal_constraints: Constraints) -> bool:
        goal_msg = MoveGroup.Goal()

        req = MotionPlanRequest()
        req.group_name = group_name
        req.num_planning_attempts = int(self.get_parameter('planning_attempts').value)
        req.allowed_planning_time = float(self.get_parameter('planning_time_s').value)
        req.max_velocity_scaling_factor = float(self.get_parameter('velocity_scaling').value)
        req.max_acceleration_scaling_factor = float(self.get_parameter('acceleration_scaling').value)
        req.goal_constraints.append(goal_constraints)
        goal_msg.request = req

        opts = PlanningOptions()
        opts.plan_only = False
        opts.replan = False
        opts.look_around = False
        goal_msg.planning_options = opts

        # Enviar
        send_future = self.move_action_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_future)
        gh = send_future.result()
        if gh is None or not gh.accepted:
            self.get_logger().error(f'  Goal rechazado por MoveIt ({group_name})')
            return False

        # Esperar resultado
        result_future = gh.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result

        if result.error_code.val == MOVEIT_SUCCESS:
            self.get_logger().info(f'  OK ({group_name})')
            return True

        self.get_logger().error(
            f'  Fallo ({group_name}): error_code={result.error_code.val}'
        )
        return False


def main():
    rclpy.init()
    node = MoveItSequencePlayer()
    ok = False
    try:
        if node.wait_for_servers():
            ok = node.play()
    except KeyboardInterrupt:
        node.get_logger().warn('Interrumpido por usuario')
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    main()
