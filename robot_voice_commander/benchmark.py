"""Benchmark del pipeline de voz.

Mide latencia por etapa, consumo de CPU/RAM y precision de comandos.
Usa microfono real para captura de audio.
"""

from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread, Event

import psutil
import yaml

logging.disable(logging.CRITICAL)

COMANDOS_PRUEBA = [
    {"texto_esperado": "move_home",        "descripcion": "Di: 've a home'"},
    {"texto_esperado": "move_joint",       "descripcion": "Di: 'mueve el joint 1 a 45 grados'"},
    {"texto_esperado": "move_joint",       "descripcion": "Di: 'mueve el joint 3 a 90 grados'"},
    {"texto_esperado": "open_gripper",     "descripcion": "Di: 'abre el gripper'"},
    {"texto_esperado": "close_gripper",    "descripcion": "Di: 'cierra el gripper'"},
    {"texto_esperado": "stop",             "descripcion": "Di: 'para' o 'stop'"},
    {"texto_esperado": "move_cartesian",   "descripcion": "Di: 'muevete 10 centimetros en X'"},
    {"texto_esperado": "rotate_joint",     "descripcion": "Di: 'rota el joint 2 treinta grados'"},
]


@dataclass
class ResultadoCiclo:
    """Resultado de un ciclo completo del benchmark."""
    comando_esperado: str
    texto_transcrito: str = ""
    accion_detectada: str = ""
    correcto: bool = False
    t_audio: float = 0.0
    t_whisper: float = 0.0
    t_llm: float = 0.0
    t_parser: float = 0.0
    t_total: float = 0.0
    cpu_promedio: float = 0.0
    ram_mb: float = 0.0
    gpu_disponible: bool = False
    gpu_memoria_mb: float = 0.0


@dataclass
class MonitorRecursos:
    """Monitorea CPU y RAM en un hilo separado."""
    muestras_cpu: list[float] = field(default_factory=list)
    muestras_ram: list[float] = field(default_factory=list)
    _stop: Event = field(default_factory=Event)
    _hilo: object = field(default=None)

    def iniciar(self) -> None:
        self._stop.clear()
        self._hilo = Thread(target=self._loop, daemon=True)
        self._hilo.start()

    def detener(self) -> tuple[float, float]:
        self._stop.set()
        if self._hilo:
            self._hilo.join(timeout=2)
        cpu = sum(self.muestras_cpu) / len(self.muestras_cpu) if self.muestras_cpu else 0.0
        ram = sum(self.muestras_ram) / len(self.muestras_ram) if self.muestras_ram else 0.0
        self.muestras_cpu.clear()
        self.muestras_ram.clear()
        return cpu, ram

    def _loop(self) -> None:
        proceso = psutil.Process()
        while not self._stop.is_set():
            self.muestras_cpu.append(psutil.cpu_percent(interval=None))
            self.muestras_ram.append(proceso.memory_info().rss / 1024 / 1024)
            time.sleep(0.2)


def detectar_gpu() -> tuple[bool, str]:
    """Detecta si hay GPU disponible y retorna (disponible, descripcion)."""
    try:
        import torch
        if torch.cuda.is_available():
            nombre = torch.cuda.get_device_name(0)
            return True, nombre
    except ImportError:
        pass
    return False, "No disponible"


def medir_gpu_memoria() -> float:
    """Retorna memoria GPU usada en MB, o 0 si no hay GPU."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated(0) / 1024 / 1024
    except ImportError:
        pass
    return 0.0


def cargar_modulos(cfg: dict):
    """Carga todos los modulos del pipeline."""
    from modules.audio import AudioCapture, Transcriber
    from modules.llm import LLMClient
    from modules.parser import ActionParser
    from modules.context import ContextBuilder

    print("  Cargando AudioCapture...")
    audio = AudioCapture(cfg["audio"])

    print("  Cargando Whisper...")
    transcriber = Transcriber(cfg["whisper"])

    print("  Cargando Ollama LLM...")
    llm = LLMClient(cfg["ollama"], cfg["robot"])

    parser = ActionParser()
    context = ContextBuilder()

    return audio, transcriber, llm, parser, context


def correr_ciclo(
    descripcion: str,
    comando_esperado: str,
    audio_cap,
    transcriber,
    llm,
    parser,
    context_builder,
    monitor: MonitorRecursos,
    gpu_disponible: bool,
) -> ResultadoCiclo:
    """Corre un ciclo completo midiendo cada etapa."""
    resultado = ResultadoCiclo(
        comando_esperado=comando_esperado,
        gpu_disponible=gpu_disponible,
    )

    print(f"\n  >> {descripcion}")
    print("     Esperando que hables...")

    monitor.iniciar()
    t_inicio_total = time.monotonic()

    # 1. Audio
    t0 = time.monotonic()
    audio = audio_cap.record_until_silence()
    resultado.t_audio = time.monotonic() - t0

    if audio is None:
        print("     [!] No se capturo audio")
        resultado.cpu_promedio, resultado.ram_mb = monitor.detener()
        return resultado

    print(f"     Audio: {resultado.t_audio:.2f}s  ({len(audio)/16000:.1f}s grabados)")

    # 2. Whisper STT
    t0 = time.monotonic()
    transcript = transcriber.transcribe(audio)
    resultado.t_whisper = time.monotonic() - t0

    if transcript is None or not transcript.text:
        print("     [!] Transcripcion vacia")
        resultado.cpu_promedio, resultado.ram_mb = monitor.detener()
        return resultado

    resultado.texto_transcrito = transcript.text
    print(f"     Whisper: {resultado.t_whisper:.2f}s  -> '{transcript.text}'")

    # 3. LLM
    scene_ctx = context_builder.build(transcription=transcript.text)
    t0 = time.monotonic()
    raw_response = llm.generate(user_message=transcript.text, scene_context=scene_ctx)
    resultado.t_llm = time.monotonic() - t0

    if not raw_response:
        print("     [!] LLM no respondio")
        resultado.cpu_promedio, resultado.ram_mb = monitor.detener()
        return resultado

    print(f"     LLM: {resultado.t_llm:.2f}s")

    # 4. Parser
    t0 = time.monotonic()
    command, error = parser.parse_safe(raw_response)
    resultado.t_parser = time.monotonic() - t0

    if command and command.actions:
        resultado.accion_detectada = command.actions[0].action.value
        resultado.correcto = resultado.accion_detectada == comando_esperado
        estado = "OK" if resultado.correcto else "MAL"
        print(f"     Parser: {resultado.t_parser:.3f}s  -> {resultado.accion_detectada} [{estado}]")
    else:
        print(f"     [!] Parser fallo: {error}")

    resultado.t_total = time.monotonic() - t_inicio_total
    resultado.cpu_promedio, resultado.ram_mb = monitor.detener()
    resultado.gpu_memoria_mb = medir_gpu_memoria()

    return resultado


def imprimir_reporte(resultados: list[ResultadoCiclo], gpu_nombre: str) -> None:
    """Imprime el reporte final en consola."""
    sep = "=" * 60

    print(f"\n{sep}")
    print("  REPORTE BENCHMARK — ROBOT VOICE COMMANDER")
    print(sep)

    # Hardware
    gpu_disp = any(r.gpu_disponible for r in resultados)
    print(f"\n  Hardware:")
    print(f"    CPU cores : {psutil.cpu_count(logical=False)} fisicos / {psutil.cpu_count()} logicos")
    print(f"    RAM total : {psutil.virtual_memory().total / 1024**3:.1f} GB")
    print(f"    GPU       : {gpu_nombre}")

    # Precision
    total = len(resultados)
    correctos = sum(1 for r in resultados if r.correcto)
    print(f"\n  Precision:")
    print(f"    Comandos probados  : {total}")
    print(f"    Correctos          : {correctos}")
    print(f"    Incorrectos        : {total - correctos}")
    print(f"    Tasa de exito      : {correctos/total*100:.1f}%")

    # Latencias promedio (solo ciclos con resultado)
    validos = [r for r in resultados if r.t_total > 0]
    if validos:
        print(f"\n  Latencia promedio por etapa:")
        print(f"    Audio (grabacion)  : {sum(r.t_audio   for r in validos)/len(validos):.2f}s")
        print(f"    Whisper STT        : {sum(r.t_whisper for r in validos)/len(validos):.2f}s")
        print(f"    Ollama LLM         : {sum(r.t_llm     for r in validos)/len(validos):.2f}s")
        print(f"    Parser             : {sum(r.t_parser  for r in validos)/len(validos):.3f}s")
        print(f"    Total por ciclo    : {sum(r.t_total   for r in validos)/len(validos):.2f}s")

    # Recursos
    print(f"\n  Consumo de recursos promedio:")
    print(f"    CPU                : {sum(r.cpu_promedio for r in validos)/len(validos):.1f}%")
    print(f"    RAM                : {sum(r.ram_mb       for r in validos)/len(validos):.0f} MB")
    if gpu_disp:
        print(f"    GPU memoria        : {sum(r.gpu_memoria_mb for r in validos)/len(validos):.0f} MB")

    # Detalle por comando
    print(f"\n  Detalle por comando:")
    print(f"  {'Esperado':<18} {'Detectado':<18} {'Total':>7} {'LLM':>7} {'OK':>4}")
    print(f"  {'-'*18} {'-'*18} {'-'*7} {'-'*7} {'-'*4}")
    for r in resultados:
        ok = "SI" if r.correcto else "NO"
        print(f"  {r.comando_esperado:<18} {r.accion_detectada:<18} {r.t_total:>6.2f}s {r.t_llm:>6.2f}s {ok:>4}")

    print(f"\n{sep}\n")


def guardar_json(resultados: list[ResultadoCiclo], path: str = "benchmark_resultados.json") -> None:
    """Guarda resultados en JSON para analisis posterior."""
    datos = []
    for r in resultados:
        datos.append({
            "comando_esperado": r.comando_esperado,
            "texto_transcrito": r.texto_transcrito,
            "accion_detectada": r.accion_detectada,
            "correcto": r.correcto,
            "latencias": {
                "audio_s": round(r.t_audio, 3),
                "whisper_s": round(r.t_whisper, 3),
                "llm_s": round(r.t_llm, 3),
                "parser_s": round(r.t_parser, 4),
                "total_s": round(r.t_total, 3),
            },
            "recursos": {
                "cpu_promedio_pct": round(r.cpu_promedio, 1),
                "ram_mb": round(r.ram_mb, 1),
                "gpu_memoria_mb": round(r.gpu_memoria_mb, 1),
            },
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"  Resultados guardados en: {path}")


def main() -> None:
    """Punto de entrada del benchmark."""
    print("\n" + "=" * 60)
    print("  BENCHMARK — ROBOT VOICE COMMANDER")
    print("=" * 60)

    # Config
    with open("config/settings.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    # GPU
    gpu_disponible, gpu_nombre = detectar_gpu()
    print(f"\n  GPU detectada: {gpu_nombre}")

    # Cargar modulos
    print("\n  Cargando modulos del pipeline...")
    audio_cap, transcriber, llm, parser, context_builder = cargar_modulos(cfg)

    monitor = MonitorRecursos()
    resultados: list[ResultadoCiclo] = []

    print(f"\n  Se probaran {len(COMANDOS_PRUEBA)} comandos.")
    print("  Habla claramente cuando se indique.\n")

    input("  Presiona ENTER para comenzar...")

    for i, cmd in enumerate(COMANDOS_PRUEBA, 1):
        print(f"\n  [{i}/{len(COMANDOS_PRUEBA)}] {cmd['descripcion']}")
        input("  Presiona ENTER cuando estes listo...")

        resultado = correr_ciclo(
            descripcion=cmd["descripcion"],
            comando_esperado=cmd["texto_esperado"],
            audio_cap=audio_cap,
            transcriber=transcriber,
            llm=llm,
            parser=parser,
            context_builder=context_builder,
            monitor=monitor,
            gpu_disponible=gpu_disponible,
        )
        resultados.append(resultado)

    imprimir_reporte(resultados, gpu_nombre)
    guardar_json(resultados)


if __name__ == "__main__":
    main()