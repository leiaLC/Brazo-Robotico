# abb_irb14050_egm — Puente EGM (ROS2)

Esta rama contiene la **infraestructura de comunicación EGM** entre ROS2 y el controlador OmniCore C30 del ABB IRB 14050. Es la capa más baja del stack: convierte los paquetes UDP del protocolo EGM en topics estándar de ROS2 que cualquier otro nodo puede consumir sin saber nada del controlador.

## ¿Qué incluye?

| Archivo | Función |
|---|---|
| `abb_irb14050_egm/egm_bridge_node.py` | Nodo principal. Mantiene la sesión UDP con el OmniCore (TX a 250 Hz), publica `/joint_states` y se subscribe a `/joint_command`. |
| `abb_irb14050_egm/joint_state_listener_node.py` | Lector simple de `/joint_states` (en radianes y grados). Útil para verificar que el bridge está vivo. |
| `abb_irb14050_egm/egm_pb2.py` | Definiciones Protobuf compiladas del protocolo EGM (`EgmRobot` / `EgmSensor`). No editar a mano. |
| `launch/egm_bridge.launch.py` | Levanta el bridge con parámetros configurables (IP del OmniCore, puertos UDP, velocidad máxima de slew). |
| `setup.py`, `package.xml`, `setup.cfg` | Metadatos del paquete ROS2. |

## Topics

| Dirección | Topic | Tipo | Notas |
|---|---|---|---|
| pub | `/joint_states` | `sensor_msgs/JointState` | 7 articulaciones, **radianes**, orden EGM (J1..J6 + J7 codo) |
| sub | `/joint_command` | `sensor_msgs/JointState` | 7 valores de posición, **radianes** |

Las unidades en ROS son radianes (convención ROS, compatible con URDF y MoveIt2). La conversión a grados (que usa el controlador) se hace solo en la frontera UDP.

## Prerrequisitos

- Ubuntu 24.04 + ROS2 Jazzy
- ABB IRB 14050 con OmniCore C30 (RobotWare 7.x)
- Programa RAPID `egm_joint_irb14050.mod` cargado en el controlador
- PC y OmniCore en la misma red (típicamente el OmniCore en `192.168.125.1`)

## Build

```bash
# Clonar la rama en tu workspace
cd ~/brazo_robotico_ws/src
git clone -b conexion https://github.com/leiaLC/Brazo-Robotico.git
# (los paquetes quedan en Brazo-Robotico/irb14050_ws/src/)

# Resolver dependencias y compilar
cd ~/brazo_robotico_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install --packages-select abb_irb14050_egm
source install/setup.bash
```

## Uso

### Checklist de seguridad (antes de cada sesión)

1. FlexPendant en *Manual Reduced Speed*.
2. Override de velocidad ≤ 25%.
3. Espacio libre alrededor del robot.
4. Enabling device presionado.
5. **Levanta el bridge ANTES** de iniciar el programa RAPID en el controlador.

### Levantar el bridge

```bash
ros2 launch abb_irb14050_egm egm_bridge.launch.py
```

Con parámetros custom (IP del OmniCore, cap de velocidad, etc.):

```bash
ros2 launch abb_irb14050_egm egm_bridge.launch.py \
    egm_tx_ip:=192.168.125.1 \
    max_speed_deg_s:=3.0
```

### Verificar que llegan datos

En otra terminal:

```bash
source ~/brazo_robotico_ws/install/setup.bash
ros2 run abb_irb14050_egm joint_listener
```

O directamente sobre el topic:

```bash
ros2 topic echo /joint_states
```

Si no ves nada, revisa que: (a) el programa RAPID esté en RUN, (b) el OmniCore tenga ruta a la IP donde corre el bridge, y (c) el firewall no esté bloqueando los puertos UDP 6510/6511.

## Notas de seguridad y diseño

- El bridge respeta los límites articulares del IRB14050 (basados en YuMi/IRB14000, mecánicamente idénticos).
- Hay un cap de slew rate (`max_speed_deg_s`, default 5°/s) para evitar comandos abruptos al controlador.
- El TX loop manda paquetes a 250 Hz **siempre**, aunque no haya comandos nuevos. Si se interrumpe, el OmniCore lanza `ERR_UDPUC_COMM` y aborta la sesión EGM.
- Toda la lógica EGM está aislada en este paquete. Cualquier otro nodo que quiera mover el robot solo tiene que publicar a `/joint_command` — no necesita saber nada de UDP, Protobuf ni del controlador.

## Próximos pasos

Con el bridge funcionando, las ramas siguientes añaden capas encima:

- **`movimiento-y-guardado`** → nodos para enseñar poses con el FlexPendant (vía RWS), guardarlas en YAML, y reproducirlas en secuencia.
- **`moveit`** → integración con MoveIt2 para planificación de trayectorias.
