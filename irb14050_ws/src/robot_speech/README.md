# robot_speech

`robot_speech` es el paquete ROS 2 encargado de convertir instrucciones por voz en comandos del sistema RAOR / Brazo-Robotico.

Este paquete integra el pipeline completo de voz:

```text
microfono
-> speech-to-text / Whisper
-> verificacion de contrasena
-> LLM local
-> parser estructurado
-> robot_task_msgs/msg/RobotCommand
-> /robot_task/command
-> robot_task_tree
```

La responsabilidad de `robot_speech` es actuar unicamente como fuente de comandos. Este paquete no mueve el robot directamente, no llama MoveIt, no controla EGM y no acciona el gripper por cuenta propia.

La ejecucion real del robot queda centralizada en:

```text
robot_task_tree
```

## Rol Dentro De La Arquitectura RAOR

En RAOR, distintas interfaces pueden generar comandos:

```text
voz
web
gamepad
sistema
```

Todas deben publicar hacia el mismo topic central:

```text
/robot_task/command
```

El nodo `robot_task_tree` escucha ese topic, valida/arbitra comandos y decide que acciones ejecutar usando MoveIt, EGM, percepcion, secuencias o gripper.

Por lo tanto, el flujo correcto de voz es:

```text
robot_speech
-> /robot_task/command
-> robot_task_tree
-> MoveIt / EGM / gripper
```

`robot_speech` no debe publicar comandos directos a MoveIt ni ejecutar trayectorias por si mismo.

## Topic Principal

### Publica

```text
/robot_task/command
```

Tipo:

```text
robot_task_msgs/msg/RobotCommand
```

Este es el mensaje comun del proyecto para enviar tareas al Behavior Tree.

Campos relevantes del mensaje:

```text
std_msgs/Header header

string source
string command_type

string object_class
string object_color
string place_target

int32 joint_id
float64 joint_delta_deg
float64 joint_target_deg
bool relative

string sequence_id

float64[] joint_values
geometry_msgs/Twist teleop_twist

float64 priority
```

Valores esperados para `command_type`:

```text
PICK_OBJECT
MOVE_JOINT
WEB_TELEOP
RUN_SEQUENCE
XBOX_TELEOP
CANCEL
ESTOP
PAUSE
RESUME
```

Para este paquete, `source` se establece como:

```text
voice
```

## Topic Auxiliar Opcional

El paquete puede publicar el texto reconocido en:

```text
/voice/text
```

Tipo:

```text
std_msgs/msg/String
```

Esta salida es solo auxiliar/debug o compatibilidad.

Por defecto esta desactivada para evitar duplicar comandos cuando tambien esta corriendo otro parser como `voice_command_parser`.

Para activarla:

```bash
ros2 run robot_speech voice_pipeline_node --ros-args -p publish_voice_text:=true
```

Importante: si se activa `/voice/text`, no debe correr al mismo tiempo otro nodo que escuche `/voice/text` y publique tambien en `/robot_task/command`, porque se podrian duplicar comandos.

## Nodos Ejecutables

El paquete instala tres ejecutables ROS 2:

```text
voice_pipeline_node
voice_command_node
verify_password
```

### `voice_pipeline_node`

Nodo principal del pipeline completo.

Ejecuta:

```text
contrasena por voz
-> autorizacion
-> comando por voz
-> Whisper
-> LLM
-> parser
-> RobotCommand
-> /robot_task/command
```

Comando:

```bash
ros2 run robot_speech voice_pipeline_node
```

### `voice_command_node`

Alias del mismo nodo principal.

Comando:

```bash
ros2 run robot_speech voice_command_node
```

### `verify_password`

Prueba aislada para validar la contrasena por voz sin ejecutar el pipeline completo.

Comando:

```bash
ros2 run robot_speech verify_password
```

## Verificacion De Contrasena

Antes de aceptar comandos, `voice_pipeline_node` solicita una contrasena por voz.

El flujo es:

```text
escuchar contrasena
-> transcribir con Whisper
-> comparar con password configurado
-> autorizar sesion
-> escuchar comando real
```

La contrasena se configura en:

```text
config/settings.yaml
```

Ejemplo:

```yaml
speaker_verification:
  enabled: true
  password: "arroz"
  session_timeout_sec: 60.0
```

### Campos

`enabled`: activa o desactiva la verificacion.

`password`: palabra o frase esperada.

`session_timeout_sec`: tiempo durante el cual el usuario queda autorizado despues de decir la contrasena correctamente.

Si vale `60.0`, el usuario puede enviar comandos durante 60 segundos antes de volver a autenticarse.

## Configuracion

Archivo principal:

```text
config/settings.yaml
```

Este archivo se instala junto con el paquete y se carga automaticamente desde:

```text
install/robot_speech/share/robot_speech/config/settings.yaml
```

Tambien se puede sobrescribir con variables de entorno.

Prioridad de carga:

```text
ROBOT_SPEECH_CONFIG
RVC_CONFIG
config instalado del paquete
```

Uso recomendado:

```bash
export ROBOT_SPEECH_CONFIG=/ruta/a/settings.yaml
```

`RVC_CONFIG` existe solo por compatibilidad con el proyecto anterior de voz.

## Secciones De `settings.yaml`

### Audio

```yaml
audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 1024
  silence_threshold: 0.01
  silence_duration: 1.5
  max_recording_duration: 15.0
  device_index: null
```

Controla la captura desde microfono.

- `sample_rate`: frecuencia de muestreo esperada por Whisper y VAD.
- `channels`: numero de canales de audio.
- `chunk_size`: tamano de lectura.
- `silence_duration`: duracion de silencio para terminar la grabacion.
- `max_recording_duration`: duracion maxima de una captura.
- `device_index`: indice del microfono. `null` usa el dispositivo por defecto.

### Speaker Verification

```yaml
speaker_verification:
  enabled: true
  password: "arroz"
  session_timeout_sec: 60.0
```

Controla la compuerta de acceso por contrasena.

### Whisper

```yaml
whisper:
  model_size: "base"
  device: "cpu"
  compute_type: "int8"
  language: "es"
  beam_size: 5
```

Configura el modelo de speech-to-text.

### llama.cpp

```yaml
llama_cpp:
  model_path: "/ruta/al/modelo.gguf"
  temperature: 0.1
  max_tokens: 512
  n_ctx: 2048
  n_threads: 4
```

Configura el LLM local usado para interpretar comandos.

El archivo `.gguf` no debe subirse al repositorio.

### Robot

```yaml
robot:
  actions:
    - move_joint
    - open_gripper
    - close_gripper
    - move_home
    - stop
    - pick
    - rotate_joint
  joints: ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "joint7"]
  cartesian_axes: ["x", "y", "z", "roll", "pitch", "yaw"]
  units:
    angles: "degrees"
    distances: "meters"
    speed: "percentage"
```

Define las acciones que el LLM puede generar y que el parser valida.

## Mapeo De Acciones Del LLM A RobotCommand

El LLM genera una estructura interna con acciones como:

```text
pick
move_joint
rotate_joint
move_home
open_gripper
close_gripper
stop
```

El nodo `voice_pipeline_node` las convierte a comandos RAOR:

| Accion interna | RobotCommand.command_type | Campos principales |
|---|---|---|
| `pick` | `PICK_OBJECT` | `object_class`, `object_color`, `place_target` |
| `move_joint` | `MOVE_JOINT` | `joint_id`, `joint_target_deg`, `relative=false` |
| `rotate_joint` | `MOVE_JOINT` | `joint_id`, `joint_delta_deg`, `relative=true` |
| `move_home` | `RUN_SEQUENCE` | `sequence_id=home` |
| `open_gripper` | `RUN_SEQUENCE` | `sequence_id=open_gripper` |
| `close_gripper` | `RUN_SEQUENCE` | `sequence_id=close_gripper` |
| `stop` | `CANCEL` | `priority=100.0` |

Las acciones que no tienen representacion directa en `/robot_task/command` son rechazadas y no se publican.

## Prioridades

El nodo asigna prioridad segun el tipo de comando:

```text
PICK_OBJECT     94.0
RUN_SEQUENCE    95.0
MOVE_JOINT      96.0
CANCEL          100.0
```

La decision final de aceptar, rechazar o interrumpir comandos ocurre en `robot_task_tree`.

## Estructura Del Paquete

```text
robot_speech/
├── config/
│   └── settings.yaml
├── resource/
│   └── robot_speech
├── robot_speech/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── voice_commander_node.py
│   └── modules/
│       ├── audio/
│       │   ├── capture.py
│       │   └── transcriber.py
│       ├── context/
│       │   └── builder.py
│       ├── llm/
│       │   ├── client.py
│       │   ├── llama_cpp_client.py
│       │   └── prompts.py
│       ├── parser/
│       │   ├── action_parser.py
│       │   └── schema.py
│       ├── speaker/
│       │   ├── password_verifier.py
│       │   └── verify.py
│       └── hardware.py
├── package.xml
├── setup.cfg
└── setup.py
```

## Componentes Internos

### `voice_commander_node.py`

Nodo ROS 2 principal.

Responsabilidades:

- Cargar configuracion.
- Crear publishers.
- Verificar contrasena por voz.
- Ejecutar el pipeline completo.
- Convertir el comando interno del parser a `robot_task_msgs/msg/RobotCommand`.
- Publicar en `/robot_task/command`.

No ejecuta movimiento directo.

### `pipeline.py`

Orquestador del pipeline de voz.

Responsabilidades:

- Capturar audio.
- Transcribir audio.
- Construir contexto.
- Consultar el LLM.
- Parsear y validar la respuesta.

Tambien expone `listen_and_transcribe()` para reutilizar audio + Whisper durante la verificacion de contrasena sin pasar por el LLM.

### `modules/audio/capture.py`

Captura audio del microfono.

Usa deteccion de voz/silencio para terminar la grabacion automaticamente.

### `modules/audio/transcriber.py`

Wrapper de Whisper usando `faster-whisper`.

Convierte audio a texto.

### `modules/llm/llama_cpp_client.py`

Cliente para inferencia local con `llama-cpp-python`.

Carga un modelo `.gguf` y genera una respuesta estructurada.

### `modules/llm/prompts.py`

Define el prompt de sistema que obliga al LLM a responder en JSON estructurado.

### `modules/parser/schema.py`

Define los modelos Pydantic esperados para las respuestas del LLM.

Incluye acciones internas como:

```text
move_joint
rotate_joint
pick
move_home
open_gripper
close_gripper
stop
```

### `modules/parser/action_parser.py`

Extrae JSON desde la respuesta del LLM y valida el resultado contra el schema.

Soporta:

- JSON directo.
- JSON dentro de bloques Markdown.
- Extraccion best-effort de un objeto JSON.

### `modules/speaker/password_verifier.py`

Verifica la contrasena transcrita.

Normaliza:

- mayusculas/minusculas
- acentos
- espacios repetidos

### `modules/speaker/verify.py`

Script independiente para probar la contrasena por voz.

### `modules/hardware.py`

Detecta configuracion de hardware, incluyendo disponibilidad de CUDA.

## Compilacion

Desde el workspace:

```bash
cd ~/8_semestre/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select robot_task_msgs
source install/setup.bash
colcon build --packages-select robot_speech
source install/setup.bash
```

Si el paquete ya habia sido compilado en modo editable y aparece un error como:

```text
error: option --uninstall not recognized
```

limpiar solo los artefactos generados del paquete:

```bash
rm -rf build/robot_speech install/robot_speech
colcon build --packages-select robot_speech
source install/setup.bash
```

## Ejecucion

### Probar contrasena

```bash
cd ~/8_semestre/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run robot_speech verify_password
```

### Correr pipeline principal

```bash
ros2 run robot_speech voice_pipeline_node
```

O usando el alias:

```bash
ros2 run robot_speech voice_command_node
```

### Ver comandos publicados

En otra terminal:

```bash
cd ~/8_semestre/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic echo /robot_task/command
```

## Prueba Sin Robot Real

Para probar sin robot real:

1. Levantar un echo del topic:

```bash
ros2 topic echo /robot_task/command
```

2. Ejecutar el pipeline:

```bash
ros2 run robot_speech voice_pipeline_node
```

3. Decir la contrasena configurada.

4. Decir un comando de voz.

Ejemplos de comandos esperados:

```text
mueve joint 1 a 45 grados
gira joint 2 treinta grados
ve a home
abre el gripper
cierra el gripper
agarra el cubo azul
detente
```

El resultado esperado es un mensaje `RobotCommand` publicado en:

```text
/robot_task/command
```

## Dependencias

Dependencias ROS declaradas:

```text
rclpy
std_msgs
robot_task_msgs
ament_index_python
python3-yaml
python3-numpy
python3-pydantic
```

Dependencias Python usadas por el pipeline de voz:

```text
pyaudio
torch
faster-whisper
llama-cpp-python
pydantic
numpy
PyYAML
```

Estas dependencias pueden requerir instalacion adicional segun el entorno.

## Variables De Entorno

### `ROBOT_SPEECH_CONFIG`

Ruta recomendada para cargar un archivo de configuracion personalizado.

```bash
export ROBOT_SPEECH_CONFIG=/ruta/a/settings.yaml
```

### `RVC_CONFIG`

Variable heredada del proyecto anterior.

Se mantiene por compatibilidad, pero se recomienda usar `ROBOT_SPEECH_CONFIG`.

Si `RVC_CONFIG` apunta a un archivo inexistente, el paquete usa automaticamente el config instalado.

## Reglas De Seguridad Del Paquete

Este paquete debe cumplir:

- No mover el robot directamente.
- No usar MoveIt directamente.
- No publicar comandos directos hacia controladores.
- No ejecutar EGM.
- No controlar el gripper directamente.
- Publicar unicamente comandos de tarea hacia `/robot_task/command`.
- Dejar que `robot_task_tree` decida que hacer.
- No correr simultaneamente con otro parser de voz que tambien publique en `/robot_task/command`.

## Archivos Que No Deben Estar En Este Paquete

No deben formar parte de `robot_speech`:

```text
benchmark.py
benchmark_cpp.py
moveit_executor_node.py
```

Tampoco deben existir entry points relacionados con:

```text
benchmark
benchmark_cpp
moveit_executor
moveit_executor_node
```

La razon es que:

- Los benchmarks eran solo pruebas de rendimiento.
- El executor de MoveIt movia el robot directamente.
- En RAOR, voz solo debe producir comandos para el Behavior Tree.

## Archivos Generados Que No Deben Versionarse

No deben subirse al repositorio:

```text
build/
install/
log/
__pycache__/
*.pyc
venv/
.venv/
models/
*.gguf
```

Los modelos `.gguf` deben vivir fuera del repositorio o descargarse/configurarse localmente.

## Estado Actual

`robot_speech` integra:

- Captura de audio por microfono.
- Transcripcion con Whisper.
- Verificacion de contrasena por voz.
- LLM local con llama.cpp.
- Parser estructurado con Pydantic.
- Conversion a `robot_task_msgs/msg/RobotCommand`.
- Publicacion en `/robot_task/command`.

La salida principal del paquete es:

```text
/robot_task/command
```

La salida opcional de debug es:

```text
/voice/text
```

El nodo principal se ejecuta con:

```bash
ros2 run robot_speech voice_pipeline_node
```
