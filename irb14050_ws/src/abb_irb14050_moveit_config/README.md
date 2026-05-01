# abb_irb14050_moveit_config — Configuración MoveIt2 para el ABB IRB 14050

Configuración generada con el **MoveIt Setup Assistant** sobre el URDF de `abb_irb14050_description`. Soporta tres backends de hardware (mock para testing, Gazebo para simulación dinámica, robot real vía EGM) que se seleccionan con un solo argumento al lanzar.

## Modos de operación (`sim_mode`)

El switch vive en `config/abb_irb14050.ros2_control.xacro` y `config/abb_irb14050.urdf.xacro`, parametrizados con el argumento `sim_mode`:

| `sim_mode` | Plugin de hardware | Para qué |
|---|---|---|
| `mock` (default) | `mock_components/GenericSystem` | Test rápido en RViz, sin física |
| `gazebo` | `gz_ros2_control/GazeboSimSystem` | Simulación dinámica (ver `abb_irb14050_gazebo`) |
| `real` | EGM action server externo | Robot físico vía OmniCore (ver `abb_irb14050_egm`) |

El modo `real` no usa `ros2_control` directamente. El `move_group` de MoveIt habla con `egm_moveit_executor` (action server) que a su vez maneja el bridge UDP. Por eso `moveit_real.launch.py` no levanta `ros2_control_node` ni controllers — solo `move_group`, RViz, el bridge y el executor.

## Prerrequisitos

- ROS 2 Jazzy + MoveIt 2:

  ```bash
  sudo apt install ros-jazzy-moveit
  ```

- `abb_irb14050_description` compilado en el mismo workspace (URDF + meshes).

Adicionales según el modo:

- **mock**: nada extra.
- **gazebo**: el paquete `abb_irb14050_gazebo` y sus dependencias (`ros-jazzy-ros-gz-sim`, `ros-jazzy-ros-gz-bridge`, `ros-jazzy-gz-ros2-control`).
- **real**: el paquete `abb_irb14050_egm` compilado, el OmniCore C30 con el programa RAPID `egm_joint_irb14050.mod` cargado y en RUN, y la red configurada para que el OmniCore pueda alcanzar el host del bridge.

## Estructura

### Config (`config/`)

| Archivo | Función |
|---|---|
| `abb_irb14050.urdf.xacro` | Wrapper que incluye el URDF + el bloque `ros2_control` + (si `sim_mode=gazebo`) el plugin de Gazebo. |
| `abb_irb14050.ros2_control.xacro` | Hardware interface seleccionado por `sim_mode`. |
| `abb_irb14050.srdf` | Grupos de planificación, end-effectors, matriz de colisiones desactivadas. |
| `joint_limits.yaml` | **Velocidades reducidas a 0.5 rad/s por defecto** (~28°/s). Esto es seguro para robot real y agradable en Gazebo, pero ralentiza dramáticamente la demo de mock. Si quieres velocidades agresivas para validación rápida, cambia `max_velocity` a los valores nominales (~π rad/s para joints 1-4, ~6.98 rad/s para 5-7). |
| `kinematics.yaml` | Solver de IK (KDL). |
| `moveit_controllers.yaml` | Mapeo entre grupos de planificación y controllers `ros2_control`. Incluye un bloque `trajectory_execution` con tolerancias permisivas (`allowed_execution_duration_scaling: 5.0`) para que MoveIt no aborte trayectorias por el slew rate del bridge EGM. |
| `ros2_controllers.yaml` | Definición de `joint_state_broadcaster` + `joint_trajectory_controller`. |
| `pilz_cartesian_limits.yaml` | Límites para el planificador industrial Pilz. |
| `initial_positions.yaml` | Pose inicial al arrancar. |
| `moveit.rviz` | Layout RViz pre-armado. |

### Launch (`launch/`)

| Archivo | Función |
|---|---|
| `demo.launch.py` | **Modo mock.** Levanta `robot_state_publisher` + `move_group` + controllers mock + RViz. Sin física, sin robot real. |
| `moveit_real.launch.py` | **Modo real.** Levanta `move_group` + RViz + `egm_bridge` + `egm_moveit_executor`. **Sin** `ros2_control_node` ni mock — el executor toma el lugar del controller. Para conectar al robot real vía OmniCore. |
| `move_group.launch.py` | Solo el nodo `move_group`. |
| `moveit_rviz.launch.py` | Solo RViz con la config de MoveIt. |
| `rsp.launch.py` | Solo `robot_state_publisher`. |
| `spawn_controllers.launch.py` | Spawnea los controllers de `ros2_control`. |
| `static_virtual_joint_tfs.launch.py` | TFs estáticos para joints virtuales. |
| `setup_assistant.launch.py` | Reabre el Setup Assistant con esta config cargada. |
| `warehouse_db.launch.py` | DB MongoDB opcional para guardar poses/trayectorias. |

(Para el modo Gazebo no hay launch propio aquí — está en `abb_irb14050_gazebo/launch/gazebo_moveit.launch.py`, que reusa este `urdf.xacro` con `sim_mode:=gazebo`.)

## Build

```bash
cd ~/brazo_robotico_ws/src
git clone -b feature/moveit-gazebo-support https://github.com/leiaLC/Brazo-Robotico.git

cd ~/brazo_robotico_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install \
    --packages-select abb_irb14050_description abb_irb14050_moveit_config
source install/setup.bash
```

Si vas a usar el modo `real`, agrega `abb_irb14050_egm` al `--packages-select`. Si vas a usar `gazebo`, agrega `abb_irb14050_gazebo`.

## Uso

### Modo mock (testing en RViz, sin física)

```bash
ros2 launch abb_irb14050_moveit_config demo.launch.py
```

Abre RViz con MotionPlanning. Plan + Execute mueve el modelo del robot, pero no hay simulación física. Útil para validar IK, márgenes de colisión y trayectorias antes de tocar Gazebo o el robot.

### Modo Gazebo (simulación dinámica)

```bash
ros2 launch abb_irb14050_gazebo gazebo_moveit.launch.py
```

Levanta Gazebo + el robot + MoveIt + RViz. Plan + Execute mueve el robot con física real. Ver el README de `abb_irb14050_gazebo` para detalles.

### Modo real (robot físico vía EGM)

**Antes de lanzar:**
1. FlexPendant en *Manual Reduced Speed*, override ≤ 25%.
2. Programa RAPID `egm_joint_irb14050.mod` cargado y en RUN.
3. OmniCore alcanzable desde el host (típico: `192.168.125.1`).
4. Espacio físico libre alrededor del robot.

```bash
ros2 launch abb_irb14050_moveit_config moveit_real.launch.py
```

Levanta `move_group` + RViz + `egm_bridge` + `egm_moveit_executor`. Plan + Execute en RViz envía la trayectoria al executor, que la traduce a `/joint_command` para el bridge, que la envía por EGM al OmniCore.

## Notas y troubleshooting

### Las velocidades son muy lentas

Es intencional: `joint_limits.yaml` está afinado para robot real, donde el cap del bridge EGM es 5°/s y MoveIt necesita pedir velocidades coherentes. Para validación visual rápida en mock, edita `max_velocity` en `joint_limits.yaml` y recompila.

### MoveIt aborta con "Trajectory execution time was longer than expected"

Esto ocurre si el bridge EGM aplica más slew del que MoveIt espera. La rama actual ya incluye márgenes generosos en `moveit_controllers.yaml` (`allowed_execution_duration_scaling: 5.0`, `allowed_goal_duration_margin: 5.0`) para mitigarlo. Si sigue pasando, sube esos valores o reduce el cap de slew en el bridge.

### Quiero cambiar entre modos sin reclonar nada

Los modos están en el mismo paquete; basta con elegir el launch correcto:
- `demo.launch.py` → mock
- `gazebo_moveit.launch.py` (del otro paquete) → gazebo
- `moveit_real.launch.py` → real

No es necesario recompilar entre modos.
