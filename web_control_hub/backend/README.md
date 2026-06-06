# Yumi Backend Gateway

Backend local para correr en la laptop que tiene ROS2/EGM. Expone una API web segura para que el frontend no hable directo con tópicos ROS2.

## Qué Hace

- Publica comandos de articulaciones como `robot_task_msgs/RobotCommand` a `/robot_task/command`.
- Publica secuencias web a `/web/sequence_id`, para que `web_command_bridge` las convierta al comando comun.
- Publica un disparador de voz a `/voice/start_listening`, para activar `robot_speech`.
- Escucha feedback desde `/joint_states`.
- Expone estado por REST y WebSocket.
- Expone en `/system/jetson` la última lectura recibida desde `/system/jetson_metrics`.
- Expone video desde un tópico de imagen ROS2 por WebRTC para la pestaña Vision/Voice.
- Mantiene el stream MJPEG en `/video/mjpeg` como compatibilidad.
- Mantiene el workspace EGM intacto y no manda `/joint_command` directo al robot.

## Requisitos

En la laptop ROS2/EGM:

```bash
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash
cd ~/Brazo-Robotico/web_control_hub/backend
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
PYTHONPATH= pip install -r requirements.txt
```

`--system-site-packages` es importante para que Python encuentre `rclpy` y mensajes ROS2 instalados por apt/colcon.

## Configuración

Copia el ejemplo:

```bash
cp .env.example .env
```

Variables principales:

```bash
ROS_DOMAIN_ID=0
ROS_COMMAND_TOPIC=/robot_task/command
ROS_STATE_TOPIC=/joint_states
ROS_SEQUENCE_TOPIC=/web/sequence_id
ROS_TELEOP_TWIST_TOPIC=/web/teleop_twist
ROS_VOICE_TEXT_TOPIC=/voice/text
ROS_VOICE_START_TOPIC=/voice/start_listening
ROS_VOICE_STATUS_TOPIC=/voice/status
ROS_JETSON_METRICS_TOPIC=/system/jetson_metrics
JETSON_METRICS_MAX_AGE_SEC=15.0
JETSON_METRICS_ALLOW_LOCAL_FALLBACK=false
ROS_IMAGE_TOPIC=/camera/color/image_raw
ROS_IMAGE_IS_COMPRESSED=false
ROS_REQUIRED_NODES=robot_state_publisher,move_group,egm_bridge,egm_moveit_executor,gripper_node,gripper_joint_state_publisher,robot_task_tree,voice_commander_node,web_command_bridge,gamepad_command_bridge
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

## Correr

```bash
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash
cd ~/Brazo-Robotico/web_control_hub/backend
source .venv/bin/activate
python -m app.main
```

## Métricas Jetson Remotas

Cuando el backend corre en una laptop distinta a la Jetson, la Jetson debe publicar:

```bash
ros2 run robot_web_interface jetson_metrics_publisher
```

Si usas el launch de Jetson, el publicador se levanta junto con `web_command_bridge`:

```bash
ros2 launch robot_task_manager full_system_jetson.launch.py launch_web_bridge:=true
```

La laptop y la Jetson deben compartir red, `ROS_DOMAIN_ID` y poder verse por DDS. Verificación rápida desde la laptop:

```bash
ros2 topic echo /system/jetson_metrics
curl http://localhost:8000/system/jetson
```

Por defecto, el backend no usa métricas locales de la laptop como fallback. Si necesitas correr todo en la Jetson sin el publicador, puedes habilitar:

```bash
JETSON_METRICS_ALLOW_LOCAL_FALLBACK=true
```

## Endpoints

```txt
GET  /health
GET  /robot/state
GET  /robot/task-status
GET  /robot/nodes
GET  /system/jetson
POST /teleop/enable
POST /teleop/disable
POST /teleop/joint-target
POST /teleop/twist
POST /sequence/run
POST /voice/text
POST /voice/start
GET  /voice/status
POST /task/cancel
POST /task/estop
WS   /ws/robot-state
WS   /ws/task-status
WS   /ws/voice-status
GET  /video/mjpeg
POST /webrtc/offer
```

Ejemplo de comando:

```bash
curl -X POST http://localhost:8000/teleop/enable
curl -X POST http://localhost:8000/teleop/joint-target \
  -H "Content-Type: application/json" \
  -d '{"positions_deg":[0,0,0,0,0,0,0]}'
```

Ejemplo de secuencia:

```bash
curl -X POST http://localhost:8000/sequence/run \
  -H "Content-Type: application/json" \
  -d '{"sequence_id":"open_gripper"}'
```
