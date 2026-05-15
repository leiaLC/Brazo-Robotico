# abb_irb14050_egm — Bridge EGM + manipulación de poses + integración MoveIt (ROS2)

Paquete completo de comunicación con el ABB IRB 14050 vía protocolo EGM. Incluye desde la capa más baja (puente UDP a 250 Hz con el OmniCore) hasta la integración con MoveIt2 para ejecutar trayectorias planificadas.

## Capas del paquete

```
                          MoveIt2 (planificador)
                                 │
                                 ▼  /…/follow_joint_trajectory  (action)
                       egm_moveit_executor   ◄─── trayectorias N waypoints
                                 │
                                 ▼  /joint_command  (rad, orden URDF)
                       egm_bridge_node       ◄─── permuta + slew + UDP 250 Hz
                                 │
                                 ▼  UDP 6510/6511
                          OmniCore C30 + RAPID
                                 │
                                 ▼
                              IRB 14050
```

Las capas superiores no necesitan saber nada de UDP, Protobuf, ni del orden de ejes ABB. Todo eso se aísla en el bridge.

## Archivos

| Archivo | Función |
|---|---|
| `abb_irb14050_egm/egm_bridge_node.py` | Puente UDP. Publica `/joint_states` (rad, orden URDF) y se subscribe a `/joint_command`. Internamente permuta el orden URDF↔ABB (axis 7 = articulación física 3, el codo), aplica cap de slew rate, y mantiene el TX a 250 Hz aunque no haya comandos nuevos. |
| `abb_irb14050_egm/joint_state_listener_node.py` | Lector simple de `/joint_states` para verificación rápida. |
| `abb_irb14050_egm/joint_commander_node.py` | CLI interactiva para mover articulaciones a mano. Comandos: `j N DELTA`, `go`, `rel`, `home`, `q`. Entrada en grados, conversión a rad interna. |
| `abb_irb14050_egm/teach_node.py` | Lee `jointtarget` por RWS 2.0 (HTTPS:443, Basic Auth) y guarda poses nombradas en YAML. Pensado para correr con EGM apagado mientras se joguea con el FlexPendant. |
| `abb_irb14050_egm/waypoint_player_node.py` | Reproduce el YAML publicando a `/joint_command` y esperando convergencia en `/joint_states` antes del siguiente waypoint. |
| `abb_irb14050_egm/egm_moveit_executor.py` | **Action server `FollowJointTrajectory`.** Recibe trayectorias de MoveIt, las publica a `/joint_command` respetando el `time_from_start` de cada punto, y reporta éxito cuando la pose real converge. Es el pegamento entre el planificador y el bridge. |
| `abb_irb14050_egm/egm_pb2.py` | Definiciones Protobuf compiladas del protocolo EGM. No editar a mano. |
| `launch/egm_bridge.launch.py` | Levanta el bridge con parámetros configurables (IP, puertos UDP, slew rate). |
| `setup.py`, `package.xml`, `setup.cfg` | Metadatos. Registra 6 entry points. |

## Topics y acciones

| Tipo | Nombre | Mensaje | Notas |
|---|---|---|---|
| topic (pub) | `/joint_states` | `sensor_msgs/JointState` | 7 articulaciones, **radianes**, **orden URDF** (`joint_1`..`joint_7`) |
| topic (sub) | `/joint_command` | `sensor_msgs/JointState` | 7 valores de posición, radianes, orden URDF |
| action (server) | `/irb14050_arm_controller/follow_joint_trajectory` | `control_msgs/FollowJointTrajectory` | El que MoveIt invoca al ejecutar un plan |

## Build y uso

```bash
cd ~/brazo_robotico_ws/src
git clone -b feature/egm-moveit-executor https://github.com/leiaLC/Brazo-Robotico.git
cd ~/brazo_robotico_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install --packages-select abb_irb14050_egm
source install/setup.bash
```

### Modo bajo nivel (sin MoveIt) — comandar a mano

```bash
ros2 launch abb_irb14050_egm egm_bridge.launch.py        # T1
ros2 run abb_irb14050_egm joint_commander                # T2
```

### Modo enseñar/reproducir poses (sin MoveIt)

Ver el flujo en la sección de `teach_node` y `waypoint_player_node` de las versiones previas. En resumen:

```bash
ros2 run abb_irb14050_egm teach --ros-args -p file:=poses.yaml          # con EGM apagado
ros2 launch abb_irb14050_egm egm_bridge.launch.py                       # con EGM activo
ros2 run abb_irb14050_egm waypoint_player --ros-args -p file:=poses.yaml
```

### Modo MoveIt (planificación + ejecución real)

Requiere el paquete `abb_irb14050_moveit_config` configurado en modo `real` (rama `feature/moveit-gazebo-support` o equivalente).

```bash
# T1: bridge EGM
ros2 launch abb_irb14050_egm egm_bridge.launch.py

# T2: action server que conecta MoveIt con el bridge
ros2 run abb_irb14050_egm egm_moveit_executor

# T3: MoveIt + RViz apuntando al action server real
ros2 launch abb_irb14050_moveit_config moveit_real.launch.py
```

Ahora cuando hagas Plan + Execute en RViz, MoveIt invoca el action server, que publica a `/joint_command`, que el bridge envía al OmniCore por EGM. El robot real se mueve siguiendo la trayectoria planificada.

## Notas sobre el orden de joints

Esta es probablemente **la parte más confusa** del paquete y la fuente de bugs más frecuente, así que vale la pena documentar:

- **El URDF y MoveIt** usan el orden físico secuencial: `joint_1` (hombro) hasta `joint_7` (muñeca).
- **El protocolo EGM** divide en `joints` (6 valores) + `externalJoints` (1 valor para el codo). Y el codo, en la cadena cinemática física, está en la posición 3.
- El bridge esconde toda esa contabilidad. Cualquier nodo que consuma `/joint_states` o publique `/joint_command` solo tiene que hablar en orden URDF.

Si vas a escribir RAPID o tocar el bridge directamente, asegúrate de entender la permutación antes de modificar nada.

## Seguridad

- El bridge respeta los límites articulares y aplica cap de slew rate (`max_speed_deg_s`, default 5°/s).
- `waypoint_player` y `egm_moveit_executor` esperan convergencia entre puntos, no encadenan comandos a ciegas.
- `teach` solo lee del controlador, nunca le manda nada.
- En todos los flujos: FlexPendant en Manual Reduced Speed, override ≤ 25%, y el operador con la mano en el enabling device.
