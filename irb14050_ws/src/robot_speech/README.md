# robot_speech

`robot_speech` convierte instrucciones por voz en comandos ROS 2 para el sistema RAOR / Brazo-Robotico.

Flujo principal:

```text
microfono
-> Whisper / faster-whisper
-> verificacion de contrasena
-> LLM local con llama-cpp-python
-> parser estructurado
-> robot_task_msgs/msg/RobotCommand
-> /robot_task/command
-> robot_task_tree
```

Este paquete no mueve el robot directamente. Solo publica comandos de tarea hacia `/robot_task/command`; el Behavior Tree (`robot_task_tree`) decide que ejecutar.

## Requisitos

Recomendado:

```text
Ubuntu 24.04
ROS 2 Jazzy
Python 3.12
microfono funcional
modelo LLM local en formato .gguf
```

Dependencias del sistema:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  python3-dev \
  python3-pip \
  python3-venv \
  portaudio19-dev \
  python3-pyaudio \
  python3-numpy \
  python3-yaml \
  python3-pydantic
```

Dependencias Python principales:

```text
faster-whisper
torch
llama-cpp-python
```

Dependencias ROS principales:

```text
rclpy
std_msgs
robot_task_msgs
ament_index_python
```

## Instalacion

Desde el workspace:

```bash
cd ~/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Si se usa entorno virtual, crearlo con `--system-site-packages` para que Python pueda ver los paquetes de ROS:

```bash
cd ~/Brazo-Robotico/irb14050_ws
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install --upgrade pip
pip install faster-whisper torch llama-cpp-python
```

Verificacion rapida:

```bash
python3 -c "import rclpy; from robot_task_msgs.msg import RobotCommand; print('ros ok')"
python3 -c "import torch; from faster_whisper import WhisperModel; from llama_cpp import Llama; print('voice deps ok')"
```

## Configuracion

El archivo principal es:

```text
config/settings.yaml
```

Tambien puede usarse un archivo externo:

```bash
export ROBOT_SPEECH_CONFIG=/ruta/a/settings.yaml
```

Lo mas importante a revisar antes de correr:

```yaml
speaker_verification:
  enabled: true
  password: "robotica"
  session_timeout_sec: 60.0

whisper:
  model_size: "base"
  device: "cpu"
  compute_type: "int8"
  language: "es"

llama_cpp:
  model_path: "/ruta/al/modelo.gguf"
  n_threads: 4
```

El modelo `.gguf` no se sube al repo. Cada computadora debe descargarlo o copiarlo localmente y ajustar `model_path`.

## Uso Con GPU

Si la computadora tiene GPU NVIDIA:

```bash
python3 -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

Instalar `llama-cpp-python` con soporte CUDA:

```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install --force-reinstall --no-cache-dir llama-cpp-python
```

Config recomendado:

```yaml
whisper:
  model_size: "base"
  device: "cuda"
  compute_type: "float16"
  language: "es"

llama_cpp:
  model_path: "/ruta/al/modelo.gguf"
  n_threads: 4
  n_gpu_layers: -1
```

`n_gpu_layers: -1` intenta usar la GPU para todas las capas posibles. Si falta VRAM, usar un numero menor, por ejemplo `20`.

## Correr

Probar solo la contraseña:

```bash
cd ~/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run robot_speech verify_password
```

Correr el pipeline completo:

```bash
ros2 run robot_speech voice_pipeline_node --ros-args -p triggered_mode:=true

```

Alias equivalente:

```bash
ros2 run robot_speech voice_command_node
```

Ver comandos publicados en otra terminal:

```bash
cd ~/Brazo-Robotico/irb14050_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic echo /robot_task/command
```

## Topics

Publica:

```text
/robot_task/command   robot_task_msgs/msg/RobotCommand
```

Opcional/debug:

```text
/voice/text           std_msgs/msg/String
```

Para activar la salida de texto:

```bash
ros2 run robot_speech voice_pipeline_node --ros-args -p publish_voice_text:=true
```

No correr al mismo tiempo otro parser de voz que escuche `/voice/text` y tambien publique en `/robot_task/command`, porque puede duplicar comandos.

## Comandos De Voz De Ejemplo

```text
abre el gripper
cierra el gripper
ve a home
mueve joint 1 a 45 grados
gira joint 2 treinta grados
agarra el cubo azul
detente
```

## Version De llama.cpp

Este paquete usa la libreria Python `llama-cpp-python`, no el ejecutable externo de `llama.cpp`.

Revisar la version instalada:

```bash
python3 -c "import llama_cpp; print(llama_cpp.__version__)"
pip show llama-cpp-python
```

Si tambien existe un clon del repo original `llama.cpp`:

```bash
git -C /ruta/a/llama.cpp describe --tags --always
git -C /ruta/a/llama.cpp rev-parse --short HEAD
```

En algunas instalaciones el binario puede reportar version:

```bash
/ruta/a/llama.cpp/build/bin/llama-cli --version
```

En versiones antiguas el binario podia llamarse `main`.

## Notas Importantes

- El paquete no controla MoveIt, EGM ni el gripper directamente.
- La ejecucion real queda en `robot_task_tree`.
- No versionar `build/`, `install/`, `log/`, `.venv/`, `__pycache__/`, `models/` ni archivos `*.gguf`.
- Si Pylance no encuentra `robot_task_msgs`, normalmente falta abrir VS Code desde una terminal con `source install/setup.bash`.
