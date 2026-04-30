# abb_irb14050_egm — Bridge EGM + manipulación y guardado de poses (ROS2)

Esta rama extiende el paquete `abb_irb14050_egm` con la **capa de manipulación interactiva y guardado de poses** sobre el bridge EGM. Hereda toda la infraestructura de comunicación de la rama `conexion` y le añade tres nodos:

- **`joint_commander`** — CLI interactiva para mover el robot articulación por articulación.
- **`teach`** — guarda la pose actual del robot (leída por RWS) en un archivo YAML mientras tú jogueas con el FlexPendant.
- **`waypoint_player`** — reproduce las poses guardadas en YAML, una por una o en secuencia.

El flujo natural es: enseñas → guardas → reproduces. Sin tener que escribir ángulos a mano.

## Archivos del paquete

| Archivo | Función |
|---|---|
| `abb_irb14050_egm/egm_bridge_node.py` | (heredado de `conexion`) Puente UDP a 250 Hz con el OmniCore. Publica `/joint_states`, suscribe `/joint_command`. |
| `abb_irb14050_egm/joint_state_listener_node.py` | (heredado) Lector simple de `/joint_states` para verificación. |
| `abb_irb14050_egm/egm_pb2.py` | (heredado) Definiciones Protobuf del protocolo EGM. |
| `abb_irb14050_egm/joint_commander_node.py` | **Nuevo.** CLI interactiva. Subscrita a `/joint_states`, publica a `/joint_command`. Comandos: `j N DELTA`, `go J1..J7`, `rel ...`, `home`, `q`. Entrada en grados, conversión a radianes interna. |
| `abb_irb14050_egm/teach_node.py` | **Nuevo.** Lee `jointtarget` del OmniCore vía RWS 2.0 (HTTPS:443, Basic Auth) y lo guarda como pose nombrada en un YAML. Pensado para correr con EGM apagado mientras se joguea con el FlexPendant. |
| `abb_irb14050_egm/waypoint_player_node.py` | **Nuevo.** Lee el YAML, publica a `/joint_command` y espera convergencia en `/joint_states` antes de pasar al siguiente waypoint. No habla con RWS — funciona igual en simulación. |
| `launch/egm_bridge.launch.py` | (heredado) Levanta el bridge con parámetros configurables. |
| `setup.py` / `package.xml` / `setup.cfg` | Metadatos. `setup.py` registra las 5 entry points (`egm_bridge`, `joint_commander`, `joint_listener`, `teach`, `waypoint_player`). |

## Topics

Iguales que en `conexion`:

| Dirección | Topic | Tipo | Notas |
|---|---|---|---|
| pub | `/joint_states` | `sensor_msgs/JointState` | 7 articulaciones, **radianes**, orden EGM |
| sub | `/joint_command` | `sensor_msgs/JointState` | 7 valores de posición, **radianes** |

`teach_node` NO usa estos topics — habla directamente con el OmniCore por HTTP. Por eso puede correr aunque el bridge no esté arriba.

## Prerrequisitos

- Todo lo de la rama `conexion` (Ubuntu 24.04, ROS2 Jazzy, RAPID `egm_joint_irb14050.mod`, etc.).
- Para `teach`: usuario y contraseña de RWS configurados en el OmniCore (los defaults de fábrica son `Default User` / `robotics`, pero confirma con el FlexPendant: *Settings → Network → User Authorization*).
- Para `waypoint_player` y `joint_commander`: el bridge corriendo y el programa RAPID en RUN.

## Build

```bash
cd ~/brazo_robotico_ws/src
git clone -b movimiento-y-guardado https://github.com/leiaLC/Brazo-Robotico.git
cd ~/brazo_robotico_ws
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install --packages-select abb_irb14050_egm
source install/setup.bash
```

## Flujos de uso

### Flujo A — Enseñar y guardar poses (con EGM apagado)

Útil cuando quieres capturar posiciones físicamente seguras moviendo el robot a mano con el joystick.

1. **FlexPendant en Manual Reduced Speed**, programa RAPID **detenido** (no necesitas EGM activo).
2. Bridge **NO** es necesario para este paso — `teach` habla directo con el OmniCore.
3. Lanza el nodo:

   ```bash
   ros2 run abb_irb14050_egm teach \
       --ros-args \
       -p ip:=192.168.125.1 \
       -p user:=Default\ User \
       -p password:=robotics \
       -p file:=poses.yaml
   ```

4. Mueve el robot al pose deseado con el FlexPendant.
5. En el prompt, escribe `save <nombre>` (ej. `save pick_a`). El nodo lee la posición actual vía RWS y la guarda en `poses.yaml`.
6. Repite para cada pose. `list` muestra lo guardado, `raw` imprime el JSON crudo del controlador (útil para debug si la versión de RW7 no parsea).

### Flujo B — Reproducir poses guardadas (con EGM activo)

1. **FlexPendant en Auto**, programa RAPID `egm_joint_irb14050.mod` corriendo.
2. Levanta el bridge:

   ```bash
   ros2 launch abb_irb14050_egm egm_bridge.launch.py
   ```

3. En otra terminal, lanza el player apuntando al YAML:

   ```bash
   ros2 run abb_irb14050_egm waypoint_player \
       --ros-args -p file:=poses.yaml
   ```

4. Comandos disponibles en el prompt:
   - `list` — lista las poses guardadas.
   - `play <nombre>` — manda una pose y espera a que el robot llegue.
   - `play_all` — manda todas en orden alfabético.
   - `play_seq <n1> <n2> <n3> ...` — manda una secuencia explícita.
   - `tol <grados>` — cambia la tolerancia de convergencia (default 0.5°).
   - `dwell <segundos>` — espera entre waypoints.

### Flujo C — Comandar articulaciones a mano (con EGM activo)

Para tests rápidos sin guardar nada:

```bash
ros2 launch abb_irb14050_egm egm_bridge.launch.py   # T1
ros2 run abb_irb14050_egm joint_commander           # T2
```

CLI:
- `j N DELTA` — mueve la articulación N en `DELTA` grados (relativo). Ej: `j 1 -5`.
- `go A B C D E F G` — pose absoluta de las 7 articulaciones en grados.
- `rel A B C D E F G` — incremento relativo en grados.
- `home` — manda al pose home (`0 0 0 0 0 0 0`).
- `q` — salir.

## Notas de seguridad

- El bridge respeta los límites articulares y aplica un cap de slew rate (`max_speed_deg_s`).
- `waypoint_player` espera convergencia antes de mandar el siguiente waypoint, no encadena comandos.
- `teach` solo lee del controlador — no le manda nada — así que es seguro de correr con la celda activa.
- Los YAML de poses están en radianes (orden EGM). No los edites a mano sin doble-check.

## Próximos pasos

La siguiente rama (`moveit`) integra el robot con MoveIt2 para planificación de trayectorias, lo que permite reemplazar el control manual articulación-por-articulación con planificación cartesiana en el espacio de trabajo.
