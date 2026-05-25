# Behavior Tree, EGM y Hub Web

Esta rama integra el supervisor basado en `py_trees` dentro del workspace principal del proyecto. La rama no modifica `master` directamente.

## Paquetes Nuevos

```text
src/robot_task_msgs        Interfaces comunes
src/robot_task_manager     Arbol de decisiones central
src/robot_voice_interface  Parser de texto/voz a RobotCommand
src/robot_web_interface    Bridge web a RobotCommand
src/robot_xbox_teleop      Bridge Xbox a RobotCommand
src/robot_arm_control      Mocks de brazo/gripper/servo
```

`src/robot_perception` conserva la percepcion real del repo y agrega `mock_yolo_detector` para pruebas.

## Regla De Arquitectura

Las interfaces no controlan el robot directamente. Todo entra por:

```text
/robot_task/command
```

El nodo central:

```text
robot_task_tree
```

decide que rama del arbol ejecutar y es el unico que solicita movimiento a MoveIt/EGM.

## Lanzar Sistema Real ABB

```bash
cd ~/Brazo-Robotico/irb14050_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch robot_task_manager full_system_abb.launch.py \
  with_viewer:=true \
  launch_object_cloud_bridge:=false \
  controller_ip:=192.168.125.1
```

## Ver Arbol Graficamente

El launch anterior abre `py-trees-tree-viewer` cuando `with_viewer:=true`. Tambien se puede abrir manualmente:

```bash
py-trees-tree-viewer
```

## Comandos De Prueba

```bash
ros2 topic pub --once /voice/text std_msgs/msg/String "{data: 'mueve el joint 1 uno grados'}"
ros2 topic pub --once /voice/text std_msgs/msg/String "{data: 'agarra el cubo azul'}"
ros2 topic pub --once /web/sequence_id std_msgs/msg/String "{data: 'open_gripper'}"
ros2 topic pub --once /web/sequence_id std_msgs/msg/String "{data: 'close_gripper'}"
ros2 topic pub --once /voice/text std_msgs/msg/String "{data: 'cancelar'}"
```

## Hub Web

El hub vive fuera de `src` para que `colcon` no intente compilar Next.js:

```text
../web_control_hub
```

Backend:

```bash
cd ~/Brazo-Robotico/web_control_hub/backend
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
PYTHONPATH= pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

Frontend:

```bash
cd ~/Brazo-Robotico/web_control_hub
npm install
cp .env.example .env.local
npm run dev -- --hostname 0.0.0.0
```

Abrir:

```text
http://localhost:3000/teleoperation
http://localhost:3000/sequences
```
