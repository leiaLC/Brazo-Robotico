"""
moveit_real.launch.py

Lanza el flujo completo de MoveIt 2 conectado al egm_bridge real.

Diferencias con demo.launch.py:
    - NO arranca ros2_control_node ni mock_components
    - SI arranca egm_bridge (publica /joint_states del robot real)
    - SI arranca egm_moveit_executor (action server FollowJointTrajectory)

Resultado:
    MoveIt planifica como en demo.launch, pero al ejecutar manda la
    trayectoria al egm_moveit_executor, que a su vez hace ticks de
    /joint_command al bridge, que finalmente habla EGM con el robot.

Uso:
    ros2 launch abb_irb14050_moveit_config moveit_real.launch.py

Pre-requisito:
    El robot real (o un simulador EGM compatible) tiene que estar
    corriendo en la otra punta del cable Ethernet ANTES de lanzar
    esto, o el bridge no enganchará.

    Para validar SIN robot, en una terminal aparte:
        python3 fake_joint_states.py
    Esto le hace creer al executor que existe un robot publicando
    /joint_states. NO comprueba que /joint_command vaya a ningún
    sitio, pero permite probar que MoveIt 2 -> executor funciona
    end-to-end. (Ver instrucciones del README.)
"""

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node

from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    # MoveIt config: lee URDF + SRDF + yamls del paquete generado
    # por el Setup Assistant.
    moveit_config = (
        MoveItConfigsBuilder(
            'abb_irb14050',
            package_name='abb_irb14050_moveit_config',
        )
        .robot_description(
            file_path=os.path.join(
                get_package_share_directory(
                    'abb_irb14050_description'),
                'urdf', 'abb_irb14050.urdf',
            )
        )
        .to_moveit_configs()
    )

    # --- robot_state_publisher: publica TF a partir de URDF + /joint_states ---
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            moveit_config.robot_description,
            # Match QoS con lo que publica el bridge
            {
                'qos_overrides': {
                    '/joint_states': {
                        'subscription': {
                            'reliability': 'reliable',
                            'durability': 'volatile',
                            'history': 'keep_last',
                            'depth': 10,
                        }
                    }
                }
            },
        ],
    )

    # --- move_group: el cerebro de MoveIt ---
    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        name='move_group',
        output='screen',
        parameters=[
            moveit_config.to_dict(),
            # Sin ros2_control_node: forzamos que MoveIt no espere
            # un /controller_manager activo
            {'use_sim_time': False},
        ],
    )

    # --- RViz preconfigurado para MoveIt ---
    rviz_config = os.path.join(
        get_package_share_directory('abb_irb14050_moveit_config'),
        'config', 'moveit.rviz',
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    # --- egm_bridge: el bridge real al robot via UDP/EGM ---
    egm_bridge = Node(
        package='abb_irb14050_egm',
        executable='egm_bridge',
        name='egm_bridge',
        output='screen',
    )

    # --- egm_moveit_executor: action server que enlaza MoveIt al bridge ---
    egm_executor = Node(
        package='abb_irb14050_egm',
        executable='egm_moveit_executor',
        name='egm_moveit_executor',
        output='screen',
    )

    return LaunchDescription([
        rsp,
        move_group,
        rviz,
        egm_bridge,
        egm_executor,
    ])
