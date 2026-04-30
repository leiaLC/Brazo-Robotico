# abb_irb14050_moveit_config — Configuración MoveIt2 para el ABB IRB 14050

Configuración generada con el **MoveIt Setup Assistant** sobre el URDF del paquete `abb_irb14050_description`. Permite planificar trayectorias para el IRB 14050 (7 DOF) en RViz, con OMPL como planificador por defecto y soporte de colisión usando los meshes coarse.

## Prerrequisitos

- ROS2 Jazzy con MoveIt2 instalado:

  ```bash
  sudo apt install ros-jazzy-moveit
  ```

- El paquete `abb_irb14050_description` compilado en el mismo workspace (esta rama lo trae).

## Archivos

### Config (`config/`)

| Archivo | Función |
|---|---|
| `abb_irb14050.urdf.xacro` | Wrapper que incluye el URDF del robot + el bloque `ros2_control`. Es lo que MoveIt termina cargando como descripción del robot. |
| `abb_irb14050.ros2_control.xacro` | Hardware interface para `ros2_control`. **Por defecto usa `mock_components/GenericSystem`** (controlador falso para pruebas en RViz). Este archivo es el switch sim-to-real: cambiar el plugin aquí permite saltar a Gazebo o al robot físico. |
| `abb_irb14050.srdf` | SRDF (Semantic Robot Description Format): grupos de planificación, end-effectors, joints virtuales, y la matriz de colisiones desactivadas (links que MoveIt sabe que nunca chocan). |
| `joint_limits.yaml` | Límites de velocidad y aceleración por articulación. |
| `kinematics.yaml` | Solver de IK (KDL por defecto). |
| `moveit_controllers.yaml` | Mapeo entre los grupos de planificación de MoveIt y los controladores de `ros2_control`. |
| `ros2_controllers.yaml` | Definición de los controladores: `joint_state_broadcaster` + `joint_trajectory_controller`. |
| `pilz_cartesian_limits.yaml` | Límites para el planificador industrial Pilz. |
| `initial_positions.yaml` | Pose inicial del robot al arrancar. |
| `moveit.rviz` | Layout de RViz pre-configurado: RobotModel, panel MotionPlanning, markers de MoveIt. |

### Launch (`launch/`)

| Archivo | Función |
|---|---|
| `demo.launch.py` | **Launch principal.** Levanta todo: `robot_state_publisher`, `move_group`, controllers (mock), RViz con la config de MoveIt. Es lo que corres para probar planificación. |
| `move_group.launch.py` | Solo el nodo `move_group` (el cerebro de MoveIt). |
| `moveit_rviz.launch.py` | Solo RViz con la configuración MoveIt. |
| `rsp.launch.py` | Solo `robot_state_publisher`. |
| `spawn_controllers.launch.py` | Spawnea los controllers de `ros2_control`. |
| `static_virtual_joint_tfs.launch.py` | TFs estáticos para joints virtuales (mundo → base). |
| `setup_assistant.launch.py` | Reabre el MoveIt Setup Assistant con esta configuración cargada (para editarla gráficamente). |
| `warehouse_db.launch.py` | DB MongoDB para guardar poses/trayectorias. Opcional. |

## Build

```bash
cd ~/brazo_robotico_ws/src
git clone -b moveit https://github.com/leiaLC/Brazo-Robotico.git

cd ~/brazo_robotico_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install \
    --packages-select abb_irb14050_description abb_irb14050_moveit_config
source install/setup.bash
```

Si rosdep se queja de algún paquete de MoveIt, instala el meta-paquete: `sudo apt install ros-jazzy-moveit`.

## Uso — demo de planificación

```bash
ros2 launch abb_irb14050_moveit_config demo.launch.py
```

Esto abre RViz con:
- El robot en su pose inicial.
- El panel **MotionPlanning** activo a la izquierda.

En el panel:

1. Pestaña **Planning**.
2. Mueve la bola interactiva en RViz (drag) o ajusta el goal state con sliders.
3. **Plan** → MoveIt busca una trayectoria.
4. **Execute** → el controlador mock ejecuta la trayectoria (el modelo del robot se mueve en RViz).

Como el hardware interface es `mock_components`, **NO se mueve nada físico**. Sirve para validar planificación, márgenes de colisión y poses de trabajo antes de tocar el robot real.

## Estado actual y próximos pasos

Esta rama solo tiene la **simulación con mock controller**. Lo que falta:

- **Conectar con Gazebo** para simulación dinámica (cambiar el plugin en `abb_irb14050.ros2_control.xacro` por `gz_ros2_control/GazeboSimSystem`).
- **Conectar con el robot real** vía el bridge EGM (de la rama `conexion`). Esto implica escribir un `hardware_interface` propio que traduzca entre los topics `/joint_states` y `/joint_command` del bridge y la API de `ros2_control`, o usar el plugin oficial de `abb_ros2` cuando esté disponible para el OmniCore.

La integración real es trabajo pendiente — esta rama deja la base de planificación lista para que se conecte con cualquiera de los dos backends arriba.
