# Robot Voice Commander

Sistema modular de control por voz para brazo robótico en ROS2 Jazzy.

```
Voz → Whisper STT → Context Builder → Ollama LLM → Action Parser → (ROS2)
                          ↑
                    YOLO v11 (cámara)
```

---

## Requisitos de sistema

| Componente | Versión mínima |
|---|---|
| Ubuntu | 24.04 |
| Python | 3.10+ |
| CUDA | 12.1+ (GPU NVIDIA) |
| Ollama | 0.3+ |

---

## Instalación

### 1. Clonar y crear entorno virtual

```bash
git clone <repo>
cd robot_voice_commander
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev ffmpeg
```

### 3. Instalar dependencias Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Instalar y configurar Ollama

```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar el servidor (en otra terminal o como servicio)
ollama serve

# Descargar el modelo (en otra terminal)
ollama pull llama3.2        # ~2 GB — recomendado para español
# Alternativas:
# ollama pull mistral        # más rápido
# ollama pull phi3           # más ligero
```

### 5. (Opcional) Descargar modelo YOLO

El modelo se descarga automáticamente la primera vez que se ejecuta.
Para descargarlo manualmente:

```bash
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

---

## Configuración

Edita `config/settings.yaml` según tu hardware:

```yaml
whisper:
  model_size: "base"     # tiny/base/small/medium — más grande = más preciso
  device: "cuda"         # cuda | cpu
  language: "es"         # es | en | null (auto-detect)

ollama:
  model: "llama3.2"      # modelo instalado con ollama pull

vision:
  enabled: true
  camera_index: 0        # índice de tu webcam
```

---

## Uso

### Ejecutar el sistema completo

```bash
source .venv/bin/activate
python main.py
```

### Comandos de voz de ejemplo (en español)

| Comando | Acción generada |
|---|---|
| "mueve el joint 1 a 45 grados" | `move_joint(joint1, 45°)` |
| "ve a home" | `move_home()` |
| "abre el gripper" | `open_gripper()` |
| "agarra la taza" | `pick(target=cup)` |
| "muévete 10 centímetros en X" | `move_cartesian(x=0.1)` |
| "stop" / "para" | `stop()` |
| "rota el joint 3 treinta grados" | `rotate_joint(joint3, +30°)` |

### Ejecutar solo el parser (sin hardware)

```bash
python -c "
from modules.parser import ActionParser
import json

p = ActionParser()
raw = json.dumps({
    'intent': 'Move joint1 to 45 degrees',
    'confidence': 0.97,
    'actions': [{'action': 'move_joint', 'parameters': {'joint': 'joint1', 'angle': 45}}],
    'clarification_needed': False,
    'clarification_message': ''
})
cmd = p.parse(raw)
print(cmd.summary())
"
```

---

## Tests

Los tests corren **sin hardware** usando stubs.

```bash
# Instalar pytest
pip install pytest

# Correr todos los tests
python -m pytest tests/ -v

# Solo parser (más rápido)
python -m pytest tests/test_parser.py -v

# Integración end-to-end (con stubs)
python -m pytest tests/test_pipeline_integration.py -v
```

---

## Arquitectura de módulos

```
modules/
├── audio/
│   ├── capture.py       # PyAudio + Silero VAD — graba hasta silencio
│   └── transcriber.py   # faster-whisper — convierte audio a texto
├── vision/
│   ├── capture.py       # OpenCV — captura en hilo de fondo
│   └── detector.py      # YOLO v11 — devuelve Detection objects
├── llm/
│   ├── client.py        # Cliente Ollama con retry
│   └── prompts.py       # System prompt con schema de acciones
├── parser/
│   ├── action_parser.py # Extrae JSON del output LLM + validación
│   └── schema.py        # Modelos Pydantic de cada acción
└── context/
    └── builder.py       # Fusiona transcripción + detecciones → prompt
```

### Flujo de datos por ciclo

```
1. AudioCapture.record_until_silence() → np.ndarray (float32, 16kHz)
2. Transcriber.transcribe()            → TranscriptionResult (texto)
3. VideoCapture.get_frame()            → np.ndarray (BGR)
4. ObjectDetector.detect()             → DetectionResult (lista de objetos)
5. ContextBuilder.build()              → str (contexto para el prompt)
6. LLMClient.generate()               → str (JSON crudo)
7. ActionParser.parse()               → RobotCommand (validado)
```

---

## Integración futura con ROS2

El `RobotCommand` validado está listo para publicarse en un topic ROS2.
El paso siguiente es crear un nodo publisher en el paquete ROS2:

```python
# Ejemplo futuro — ros2_bridge/command_publisher.py
import rclpy
from std_msgs.msg import String
from modules.parser.schema import RobotCommand

class CommandPublisher(Node):
    def __init__(self):
        super().__init__("voice_command_publisher")
        self.pub = self.create_publisher(String, "/robot/voice_commands", 10)

    def publish(self, command: RobotCommand):
        msg = String()
        msg.data = command.model_dump_json()
        self.pub.publish(msg)
```

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `RVC_CONFIG` | `config/settings.yaml` | Ruta al archivo de configuración |

---

## Solución de problemas

**"Cannot connect to Ollama"**
```bash
ollama serve  # en otra terminal
```

**"No module named 'pyaudio'"**
```bash
sudo apt install portaudio19-dev
pip install pyaudio
```

**Whisper lento en CPU**
```yaml
# En settings.yaml:
whisper:
  model_size: "tiny"
  compute_type: "int8"
```

**YOLO no detecta objetos**
```yaml
# Bajar el umbral de confianza:
yolo:
  confidence_threshold: 0.3
```
