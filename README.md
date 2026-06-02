# Robotic Arm with Object Recognition (RAOR) - Proyecto Final de Robótica

## 1. Descripción del Proyecto
Este repositorio contiene el desarrollo del sistema de control y visión para un brazo robótico **ABB IRB 14050**, integrado con un controlador **OmniCore C30**. El objetivo principal es la implementación de un controlador avanzado basado en **ROS 2** que permita la interacción humano-robot (HRI) mediante **lenguaje natural**, permitiendo al brazo ejecutar tareas complejas en un entorno de almacén inteligente compartido con otros agentes autónomos (Rover, Watch Tower y Banda Transportadora).

### Componentes de Hardware
* **Manipulador:** Brazo robótico colaborativo IRB 14050.
* **Controlador:** OmniCore C30.
* **Procesamiento Principal:** NVIDIA Jetson Orin NX.
* **Sensores:** * Cámara RGB-D para percepción 3D y reconocimiento de objetos.
    * Micrófono direccional para la ingesta de comandos de voz.
    * Botón de parada de emergencia y DeadMan Switch (Requisitos de seguridad).

### Software
* **Sistema Operativo:** Ubuntu 24.04 LTS.
* **Framework:** ROS 2 Jazzy Jalisco.
* **Simulación:** Gazebo / Webots / NVIDIA Isaac Sim (POR DEFINIR).
* **Visión:** OpenCV, TensorFlow, YOLOv7 para detección de objetos y gestos.
* **Interfaz de Voz:** Natural Language Interfaces (LUI) para procesamiento de lenguaje natural.

## 3. Características Principales
* **Interacción Humano-Robot (HRI):** Capacidad de recibir y entregar objetos a usuarios humanos mediante comandos de voz y reconocimiento de gestos.
* **Visión Artificial 2D/3D:** Identificación de defectos, anomalías y categorización de productos.
* **Planificación de Trayectorias:** Operaciones seguras de *pick-and-place* en entornos dinámicos con presencia de humanos y otros robots.
* **Árbol de Transformaciones (TF):** Sistema de coordenadas común referenciado a un mapa global para integración multi-robot.

## 4. Estructura de Sprints
El desarrollo se dividió en etapas incrementales de autonomía:
1.  **Sprint 1:** Validación de sensores, teleoperación y seguridad física.
2.  **Sprint 2:** Fundamentos de percepción y respuesta a comandos de voz simples (e.g., "stop", "pick up").
3.  **Sprint 3:** Prensión guiada por visión y coordinación brazo-base.
4.  **Sprint 4:** Comandos basados en categorías (e.g., "agarra una fruta") y recuperación de fallos.
5.  **Final Sprint:** Integración total: el sistema gestiona la ambigüedad y completa tareas complejas de almacenamiento.

## 5. Instalación y Uso
*(Nota: Asegúrate de tener instalado ROS2 Jazzy antes de comenzar)*.

```bash
# Clonar el repositorio en $HOME. La compilación de paquetes se explica posteriormente
git clone [URL-del-repositorio]
```

## 6. Rama De Integración Behavior Tree + Web

El sistema nuevo de supervisión se integró en una rama separada para revisión del equipo, sin modificar `master`:

```bash
git fetch origin
git switch feature/behavior-tree-web-integration
```

Esta rama mantiene el workspace principal en `irb14050_ws` y agrega el supervisor basado en `py_trees`, mensajes comunes, interfaces de voz/web/Xbox, adaptadores mock y el hub web:

```text
irb14050_ws/src/
├── robot_task_msgs
├── robot_task_manager
├── robot_voice_interface
├── robot_web_interface
├── robot_xbox_teleop
├── robot_arm_control
└── robot_perception  # conserva la percepción real y agrega mock_yolo_detector

web_control_hub/
├── backend
└── src
```

El contrato central es que ninguna interfaz mueve el robot directamente. Todas publican comandos comunes y el único nodo que decide movimiento es:

```text
robot_task_tree
```

Flujo real ABB:

```text
web / voz / xbox
  -> /robot_task/command
  -> robot_task_tree
  -> MoveIt
  -> egm_moveit_executor
  -> egm_bridge
  -> ABB OmniCore
```

### Compilar El Workspace Integrado

```bash
cd ~/Brazo-Robotico/irb14050_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src -y --ignore-src --skip-keys warehouse_ros_mongo
colcon build --symlink-install
source install/setup.bash
```

**Notas:**

+ El comando `rosdep install --from-paths src -y --ignore-src --skip-keys warehouse_ros_mongo` revisa todas las dependencias establecidas en los paquetes del workspace, sí faltan dependencias que se pueden obtener mediante apt, entonces las instala de forma automática. Algunas de las dependencias son: `ros-jazzy-py*` y `ros-jazzy-moveit*`.
+ Para que todos los paquetes de este workspace sean visto en cada nueva terminal, se necesitan ejecutar los comandos: `cd ~/Brazo-Robotico/irb14050_ws && source /opt/ros/jazzy/setup.bash`. Para evitar esto, se puede agregar la línea: `source ~/Brazo-Robotico/irb14050_ws/install/setup.bash`, al archivo `~/.bashrc`.


En esta computadora el repo local usado durante integración está en:

```bash
cd ~/Brazo-Robotico-zuriel/irb14050_ws
```

### Lanzar ABB Real Con El Árbol

Configura la Ethernet para que la computadora/Jetson tenga la IP que espera el `UC_DEVICE` del robot. En nuestro banco fue:

```bash
sudo ip addr flush dev eno1
sudo ip addr add 192.168.125.5/24 dev eno1
sudo ip link set eno1 up
sudo ip route replace 192.168.125.0/24 dev eno1 src 192.168.125.5
ip route get 192.168.125.1
```

Luego lanza:

```bash
cd ~/Brazo-Robotico/irb14050_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch robot_task_manager full_system_abb.launch.py \
  with_viewer:=true \
  launch_object_cloud_bridge:=false \
  controller_ip:=192.168.125.1 \
  egm_rx_port:=6511 \
  egm_tx_port:=6510
```

### Pruebas Rápidas

```bash
ros2 topic pub --once /voice/text std_msgs/msg/String "{data: 'mueve el joint 1 uno grados'}"
ros2 topic pub --once /web/sequence_id std_msgs/msg/String "{data: 'open_gripper'}"
ros2 topic pub --once /web/sequence_id std_msgs/msg/String "{data: 'close_gripper'}"
ros2 topic pub --once /voice/text std_msgs/msg/String "{data: 'cancelar'}"
```

### Hub Web

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

## 7. Equipo de Trabajo
* **Integrantes:** Daniel Avendaño Llanos, Paola Arizbeth Mejía Alcantar, Francisco Zuriel Tovar Mendoza, Ariadna Laurent Cienfuegos
* **Institución:** Tecnológico de Monterrey, Escuela de Ingeniería y Ciencias.
* **Socio Formador:** Octopy y Ecuela de Ingeniería Industrial.
* **Profesores:** David Balderas (Coordinador), Oscar Fuentes, Jesús Vázquez, José Ángel Martínez.

---

**Licencia:** Este proyecto se desarrolla bajo fines académicos para el curso de Integración de Robótica y Sistemas Inteligentes 2026.
