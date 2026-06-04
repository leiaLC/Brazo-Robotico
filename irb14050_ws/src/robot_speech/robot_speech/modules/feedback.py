"""Centralized status text and optional text-to-speech feedback."""

from __future__ import annotations

import queue
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class LoggerLike(Protocol):
    """Small logger protocol compatible with rclpy loggers."""

    def warn(self, message: str) -> None:
        """Log a warning message."""

    def info(self, message: str) -> None:
        """Log an info message."""


STATUS_MESSAGES: dict[str, str] = {
    "idle": "",
    "listening_password": " Di la contraseña.",
    "listening_command": "Dime la instrucción que quieres que realice.",
    "transcribing": "",
    "interpreting": "Un momento, estoy interpretando.",
    "processing": "",
    "accepted": "",
    "publishing": "",
    "published": " Ejecutando comando interpretado.",
    "no_audio": "No escuché nada.",
    "password_rejected": "Contraseña incorrecta.",
    "clarification_needed": (
        "No entendí el comando. Intenta decirlo de otra forma."
    ),
    "error": "Ese comando no se puede realizar.",
    "done": "",
}

STATUS_LOG_MESSAGES: dict[str, str] = {
    "idle": "Voice system ready",
    "listening_password": "Listening for password",
    "listening_command": "Listening for command",
    "transcribing": "Transcribing audio",
    "interpreting": "Interpreting command",
    "processing": "Processing command",
    "accepted": "Command accepted",
    "publishing": "Sending command to robot task system",
    "published": "Command sent",
    "no_audio": "No speech detected",
    "password_rejected": "Password rejected",
    "clarification_needed": "Command not understood",
    "error": "Command rejected",
    "done": "Voice cycle finished",
}

VERBOSE_STATUS_MESSAGES: dict[str, str] = {
    "idle": "Sistema de voz listo.",
    "listening_command": (
        "Te escucho. Puedes decir: mueve la articulación 1 a 50 grados."
    ),
    "clarification_needed": (
        "No entendí el comando. Puedes decir, por ejemplo: mueve la articulación 1 a 50 grados."
    ),
    "no_audio": "No alcancé a escuchar. Intenta otra vez.",
}


@dataclass(frozen=True)
class FeedbackConfig:
    """Runtime configuration for optional spoken feedback."""

    enable_tts: bool = False
    tts_engine: str = "piper"
    tts_language: str = "es"
    tts_rate: int = 0
    tts_piper_model: str = ""
    tts_piper_config: str = ""
    verbose_feedback: bool = False
    speak_examples_on_start: bool = False


class VoiceFeedbackManager:
    """Publishes optional spoken feedback without making TTS a hard dependency."""

    _SUPPORTED_ENGINES = {"piper", "spd-say", "none"}

    def __init__(self, logger: LoggerLike, config: FeedbackConfig) -> None:
        self._logger = logger
        self._config = config
        self._engine = config.tts_engine.strip().lower() or "none"
        self._process: subprocess.Popen | None = None
        self._speech_queue: queue.Queue[tuple[str, threading.Event] | None] | None = None
        self._speech_thread: threading.Thread | None = None
        self._enabled = bool(config.enable_tts) and self._engine != "none"

        if self._engine not in self._SUPPORTED_ENGINES:
            self._logger.warn(
                f"[robot_speech] Unsupported TTS engine '{self._engine}'; voice feedback disabled."
            )
            self._enabled = False
            return

        if not self._enabled:
            return

        if self._engine == "piper" and not self._piper_available():
            self._logger.warn(
                "[robot_speech] Piper TTS is not ready; falling back to spd-say."
            )
            self._engine = "spd-say"

        if self._engine == "spd-say" and shutil.which("spd-say") is None:
            self._logger.warn(
                "[robot_speech] TTS enabled but spd-say was not found; "
                "continuing without spoken feedback."
            )
            self._enabled = False
            return

        self._speech_queue = queue.Queue(maxsize=1)
        self._speech_thread = threading.Thread(target=self._run_speech_worker, daemon=True)
        self._speech_thread.start()

    @property
    def enabled(self) -> bool:
        """Return whether spoken feedback is active."""
        return self._enabled

    def log_message(self, status: str) -> str:
        """Return a stable human-readable log message for a status."""
        return STATUS_LOG_MESSAGES.get(status, status)

    def status_message(self, status: str) -> str:
        """Return the spoken message for a status."""
        if self._config.verbose_feedback and status in VERBOSE_STATUS_MESSAGES:
            return VERBOSE_STATUS_MESSAGES[status]
        return STATUS_MESSAGES.get(status, "")

    def say_status(self, status: str, wait: bool = False, timeout_sec: float = 5.0) -> None:
        """Speak the configured phrase for a status, if enabled."""
        self.say(self.status_message(status), wait=wait, timeout_sec=timeout_sec)

    def say_start_example(self) -> None:
        """Speak an optional startup hint."""
        if self._config.speak_examples_on_start:
            self.say("Sistema de voz listo. Puedes decir: mueve la articulación 1 a 50 grados.")

    def say(self, text: str, wait: bool = False, timeout_sec: float = 5.0) -> None:
        """Speak text with the configured engine. Failures only produce warnings."""
        if not self._enabled or not text:
            return

        try:
            done = self._queue_text(text)
            if wait and done is not None:
                done.wait(timeout=max(0.1, timeout_sec))
        except Exception as exc:  # noqa: BLE001 - feedback must never break command handling.
            self._logger.warn(f"[robot_speech] TTS feedback failed: {exc}")

    def _start_process(self, command: list[str]) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _queue_text(self, text: str) -> threading.Event | None:
        if self._speech_queue is None:
            return None
        done = threading.Event()
        try:
            while True:
                pending = self._speech_queue.get_nowait()
                if pending is not None:
                    _text, pending_done = pending
                    pending_done.set()
        except queue.Empty:
            pass
        self._speech_queue.put_nowait((text, done))
        return done

    def _run_speech_worker(self) -> None:
        if self._speech_queue is None:
            return
        while True:
            item = self._speech_queue.get()
            if item is None:
                return
            text, done = item
            try:
                if self._engine == "piper":
                    self._say_with_piper(text)
                elif self._engine == "spd-say":
                    self._say_with_spd(text)
            except Exception as exc:  # noqa: BLE001 - background feedback is best effort.
                self._logger.warn(f"[robot_speech] TTS feedback failed: {exc}")
            finally:
                done.set()

    def _piper_available(self) -> bool:
        if shutil.which("piper") is None:
            return False
        if shutil.which("aplay") is None:
            return False
        model_path = Path(self._config.tts_piper_model).expanduser()
        return bool(self._config.tts_piper_model and model_path.is_file())

    def _say_with_piper(self, text: str) -> None:
        model_path = str(Path(self._config.tts_piper_model).expanduser())
        config_path = str(Path(self._config.tts_piper_config).expanduser())
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as wav_file:
            command = ["piper", "--model", model_path, "--output_file", wav_file.name]
            if self._config.tts_piper_config and Path(config_path).is_file():
                command.extend(["--config", config_path])
            subprocess.run(
                command,
                input=text,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            subprocess.run(
                ["aplay", "-q", wav_file.name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

    def _say_with_spd(self, text: str) -> None:
        command = ["spd-say", "-w", "-l", self._config.tts_language]
        if -100 <= self._config.tts_rate <= 100:
            command.extend(["-r", str(self._config.tts_rate)])
        command.append(text)
        self._start_process(command)
