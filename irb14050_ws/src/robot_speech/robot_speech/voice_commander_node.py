"""ROS 2 node that runs the voice pipeline and publishes task commands."""

from __future__ import annotations

import os
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from std_msgs.msg import Empty, String

from robot_task_msgs.msg import RobotCommand

from .modules.audio import AudioCapture, Transcriber
from .modules.context import ContextBuilder
from .modules.feedback import FeedbackConfig, VoiceFeedbackManager
from .modules.hardware import get_hardware_config
from .modules.llm import LlamaCppClient
from .modules.parser import ActionParser
from .modules.parser.schema import ActionType
from .modules.speaker.password_verifier import PasswordVerifier
from .pipeline import VoiceCommandPipeline


COMMAND_TOPIC = "/robot_task/command"
TEXT_TOPIC = "/voice/text"
START_TOPIC = "/voice/start_listening"
STATUS_TOPIC = "/voice/status"
EVENT_TOPIC = "/voice/events"

SEQUENCE_PHRASES = {
    "perception_pose": [
        "ve a perception pose",
        "ve a la pose de percepcion",
        "ve a la pose de percepción",
        "go to perception pose",
        "perception pose",
        "pose de percepcion",
    ],
    "classify_objects": [
        "clasifica los objetos",
        "clasificar objetos",
        "classify objects",
        "detecta y clasifica los objetos",
        "detecta objetos",
        "detect objects",
    ],
}

OBJECT_CLASS_ALIASES = {
    "cubo": "cube",
    "cube": "cube",
    "cilindro": "cylinder",
    "cylinder": "cylinder",
    "hexagono": "hexagon",
    "hexagon": "hexagon",
    "toroide": "toroid",
    "toroid": "toroid",
    "manzana": "apple",
    "apple": "apple",
}

COLOR_ALIASES = {
    "azul": "blue",
    "blue": "blue",
    "rojo": "red",
    "roja": "red",
    "red": "red",
    "verde": "green",
    "green": "green",
    "amarillo": "yellow",
    "amarilla": "yellow",
    "yellow": "yellow",
    "rosa": "pink",
    "rosado": "pink",
    "rosada": "pink",
    "pink": "pink",
}

SPANISH_NUMBERS = {
    "cero": 0.0,
    "un": 1.0,
    "uno": 1.0,
    "unos": 1.0,
    "una": 1.0,
    "dos": 2.0,
    "tres": 3.0,
    "cuatro": 4.0,
    "cinco": 5.0,
    "seis": 6.0,
    "siete": 7.0,
    "ocho": 8.0,
    "nueve": 9.0,
    "diez": 10.0,
    "veinte": 20.0,
    "treinta": 30.0,
    "cuarenta": 40.0,
    "cincuenta": 50.0,
}


class UnsupportedVoiceCommand(ValueError):
    """Raised when a parsed LLM action cannot be represented in RobotCommand."""


class VoiceCommanderNode(Node):
    """Run STT -> LLM -> parser and publish robot_task_msgs/RobotCommand."""

    def __init__(self) -> None:
        super().__init__("voice_commander_node")

        raw_config = self._load_config()
        feedback_defaults = raw_config.get("feedback", {})

        self.declare_parameter("publish_voice_text", False)
        self.declare_parameter("triggered_mode", False)
        self.declare_parameter("password_attempts", 2)
        self.declare_parameter("require_password", True)
        self.declare_parameter("enable_tts", bool(feedback_defaults.get("enable_tts", False)))
        self.declare_parameter("tts_engine", str(feedback_defaults.get("tts_engine", "piper")))
        self.declare_parameter("tts_language", str(feedback_defaults.get("tts_language", "es")))
        self.declare_parameter("tts_rate", int(feedback_defaults.get("tts_rate", 0)))
        self.declare_parameter(
            "tts_piper_model",
            str(feedback_defaults.get("tts_piper_model", "")),
        )
        self.declare_parameter(
            "tts_piper_config",
            str(feedback_defaults.get("tts_piper_config", "")),
        )
        self.declare_parameter(
            "verbose_feedback",
            bool(feedback_defaults.get("verbose_feedback", False)),
        )
        self.declare_parameter(
            "speak_examples_on_start",
            bool(feedback_defaults.get("speak_examples_on_start", False)),
        )
        self.declare_parameter(
            "tts_listen_guard_sec",
            float(feedback_defaults.get("tts_listen_guard_sec", 0.25)),
        )
        self.declare_parameter("subscribe_voice_text", True)
        self.publish_voice_text = bool(self.get_parameter("publish_voice_text").value)
        self.triggered_mode = bool(self.get_parameter("triggered_mode").value)
        self.password_attempts = int(self.get_parameter("password_attempts").value)
        self.require_password = bool(self.get_parameter("require_password").value)
        feedback_config = FeedbackConfig(
            enable_tts=bool(self.get_parameter("enable_tts").value),
            tts_engine=str(self.get_parameter("tts_engine").value),
            tts_language=str(self.get_parameter("tts_language").value),
            tts_rate=int(self.get_parameter("tts_rate").value),
            tts_piper_model=str(self.get_parameter("tts_piper_model").value),
            tts_piper_config=str(self.get_parameter("tts_piper_config").value),
            verbose_feedback=bool(self.get_parameter("verbose_feedback").value),
            speak_examples_on_start=bool(
                self.get_parameter("speak_examples_on_start").value
            ),
        )
        self.subscribe_voice_text = bool(self.get_parameter("subscribe_voice_text").value)
        self.tts_listen_guard_sec = max(
            0.0,
            float(self.get_parameter("tts_listen_guard_sec").value),
        )
        self.cycle_active = False
        self.command_pub = self.create_publisher(RobotCommand, COMMAND_TOPIC, 10)
        self.status_pub = self.create_publisher(String, STATUS_TOPIC, 10)
        self.event_pub = self.create_publisher(String, EVENT_TOPIC, 10)
        self.text_pub = (
            self.create_publisher(String, TEXT_TOPIC, 10)
            if self.publish_voice_text
            else None
        )
        self.start_sub = self.create_subscription(
            Empty,
            START_TOPIC,
            self._start_listening_callback,
            10,
        )
        self.text_sub = None
        if self.subscribe_voice_text and self.publish_voice_text:
            self.get_logger().warn(
                "[robot_speech] subscribe_voice_text disabled because publish_voice_text is enabled."
            )
            self.subscribe_voice_text = False
        if self.subscribe_voice_text:
            self.text_sub = self.create_subscription(
                String,
                TEXT_TOPIC,
                self._text_callback,
                10,
            )

        cfg = get_hardware_config(raw_config)
        cuda = cfg["hardware"]["cuda"]
        device = "CUDA" if cuda else "CPU"
        self.get_logger().info(f"Voice pipeline starting on {device}")
        self.password_verifier = PasswordVerifier(cfg["speaker_verification"])
        self.feedback = VoiceFeedbackManager(self.get_logger(), feedback_config)
        self.auth_session_timeout_sec = float(
            cfg["speaker_verification"].get("session_timeout_sec", 60.0)
        )
        self.authorized_until = 0.0

        self.pipeline = VoiceCommandPipeline(
            audio_capture=AudioCapture(cfg["audio"]),
            transcriber=Transcriber(cfg["whisper"]),
            llm_client=LlamaCppClient(cfg["llama_cpp"], cfg["robot"]),
            action_parser=ActionParser(),
            context_builder=ContextBuilder(),
            status_callback=self._publish_status,
        )

        self.timer = None
        if not self.triggered_mode:
            self.timer = self.create_timer(0.1, self.run_cycle)

        self.get_logger().info(
            f"voice_commander_node ready: publishing RobotCommand on {COMMAND_TOPIC}"
        )
        if self.subscribe_voice_text:
            self.get_logger().info(
                f"Text command input enabled: listening on {TEXT_TOPIC}"
            )
        if self.triggered_mode:
            self.get_logger().info(
                f"Triggered mode enabled: waiting for {START_TOPIC}"
            )
        self._publish_status("idle")
        self.feedback.say_start_example()

    def _load_config(self) -> dict[str, Any]:
        cfg_path = os.environ.get("ROBOT_SPEECH_CONFIG") or os.environ.get("RVC_CONFIG")
        if cfg_path is None or not Path(cfg_path).is_file():
            share_dir = Path(get_package_share_directory("robot_speech"))
            cfg_path = share_dir / "config" / "settings.yaml"

        with open(cfg_path, "r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file)

    def run_cycle(self) -> None:
        if self.cycle_active:
            self.get_logger().warn("Voice cycle already active; start request ignored")
            return

        self.cycle_active = True
        if self.timer is not None:
            self.timer.cancel()

        self.get_logger().info("[robot_speech] Voice cycle started from web interface.")
        self._publish_event("cycle_started", "Voice cycle started")

        if not self._has_active_authorization():
            if not self._authorize_speaker():
                self._finish_cycle("error")
                return

        self._prompt_then_listen("prompting_command", "listening_command")
        self.get_logger().info("[robot_speech] Listening for command...")

        ctx = self.pipeline.run_cycle()
        self._log_pipeline_timings(ctx)
        if ctx.transcription:
            if self.publish_voice_text:
                self._publish_text(ctx.transcription)
            self.get_logger().info(f"[robot_speech] Heard command: {ctx.transcription!r}")
            self._publish_event("heard", ctx.transcription, ctx.transcription_confidence)
        else:
            self.get_logger().warn("No voice detected")
            self._publish_event("no_audio", "No speech detected")
            self._finish_cycle("no_audio")
            return

        if ctx.parse_error:
            self.get_logger().warn(f"[robot_speech] Parser error: {ctx.parse_error}")

        if not ctx.success:
            clarification = self._clarification_for_text(ctx.transcription)
            if clarification:
                self.get_logger().warn(f"[robot_speech] Clarification needed: {clarification}")
                self._publish_event("clarification", clarification, ctx.transcription_confidence)
                self._finish_cycle("clarification_needed")
                return

            fallback = self._fallback_task_command_from_text(ctx.transcription)
            if fallback is None:
                self.get_logger().warn("[robot_speech] No valid command was produced.")
                self._publish_event("rejected", ctx.transcription, ctx.transcription_confidence)
                self._finish_cycle("error")
                return

            self._publish_status("processing")
            self._publish_status("accepted")
            self._publish_status("publishing")
            self.command_pub.publish(fallback)
            self._publish_event(
                "published",
                self._describe_robot_command(fallback),
                ctx.transcription_confidence,
            )
            self._publish_status("published", wait=True)
            self.get_logger().info("[robot_speech] Published fallback command to /robot_task/command.")
            self._finish_cycle("done")
            return

        clarification = self._clarification_for_text(ctx.transcription)
        if clarification:
            self.get_logger().warn(f"[robot_speech] Clarification needed: {clarification}")
            self._publish_event("clarification", clarification, ctx.transcription_confidence)
            self._finish_cycle("clarification_needed")
            return

        self._publish_status("processing")
        try:
            command = self._to_task_command(ctx.parsed_command)
        except UnsupportedVoiceCommand as exc:
            self.get_logger().warn(str(exc))
            self._publish_event("clarification", str(exc), getattr(ctx.parsed_command, "confidence", None))
            self._finish_cycle("clarification_needed")
            return

        self._publish_status("accepted")
        self._publish_status("publishing")
        self.command_pub.publish(command)
        self._publish_event(
            "published",
            self._describe_robot_command(command),
            getattr(ctx.parsed_command, "confidence", None),
        )
        self._publish_status("published", wait=True)
        self.get_logger().info(
            f"Published {command.command_type} command on {COMMAND_TOPIC}"
        )
        self.get_logger().info("[robot_speech] Published command to /robot_task/command.")
        self._finish_cycle("done")

    def _start_listening_callback(self, _msg: Empty) -> None:
        self.get_logger().info(f"Received voice start request on {START_TOPIC}")
        self.run_cycle()

    def _text_callback(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            self.get_logger().warn("[robot_speech] Empty text command ignored.")
            return

        self.get_logger().info(f"[robot_speech] Received text command: {text!r}")
        self._publish_event("heard_text", text)

        if not self._has_active_authorization():
            self.get_logger().warn(
                "[robot_speech] Text command rejected: password required."
            )
            self._publish_status("password_rejected")
            self._publish_event("rejected", "password required")
            return

        clarification = self._clarification_for_text(text)
        if clarification:
            self.get_logger().warn(
                f"[robot_speech] Text command needs clarification: {clarification}"
            )
            self._publish_event("clarification", clarification)
            self._publish_status("clarification_needed")
            return

        command = self._fallback_task_command_from_text(text)
        if command is None:
            self.get_logger().warn(
                f"[robot_speech] Unsupported text command: {text!r}"
            )
            self._publish_event("rejected", text)
            self._publish_status("error")
            return

        self._publish_status("processing")
        self._publish_status("accepted")
        self._publish_status("publishing")
        self.command_pub.publish(command)
        self._publish_event("published", self._describe_robot_command(command))
        self._publish_status("published", wait=True)
        self.get_logger().info(
            "[robot_speech] Published text command to /robot_task/command."
        )

    def _finish_cycle(self, status: str = "done") -> None:
        final_spoken_statuses = {
            "no_audio",
            "password_rejected",
            "clarification_needed",
            "error",
        }
        self._publish_status(status, wait=status in final_spoken_statuses)
        self._publish_event("cycle_finished", status)
        self.cycle_active = False
        if self.timer is not None:
            self.timer.reset()
        self._publish_status("idle", speak=False)
        self.get_logger().info("[robot_speech] Voice cycle finished. Returning to idle.")

    def _log_pipeline_timings(self, ctx) -> None:
        timings = getattr(ctx, "timings_sec", {}) or {}
        if not timings:
            return

        self.get_logger().info(
            "[robot_speech] Timing: "
            f"audio={timings.get('audio', 0.0):.2f}s "
            f"stt={timings.get('stt', 0.0):.2f}s "
            f"context={timings.get('context', 0.0):.2f}s "
            f"llm={timings.get('llm', 0.0):.2f}s "
            f"parse={timings.get('parse', 0.0):.2f}s "
            f"total={timings.get('total', 0.0):.2f}s"
        )

    def _prompt_then_listen(self, prompt_status: str, listening_status: str) -> None:
        self._publish_status(prompt_status, wait=True)
        self._guard_microphone_after_feedback()
        self._publish_status(listening_status, speak=False)

    def _guard_microphone_after_feedback(self) -> None:
        if self.feedback.enabled and self.tts_listen_guard_sec > 0.0:
            time.sleep(self.tts_listen_guard_sec)

    def _publish_status(
        self,
        status: str,
        *,
        speak: bool = True,
        wait: bool = False,
    ) -> None:
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)
        if speak:
            self.feedback.say_status(status, wait=wait)
        self.get_logger().info(
            f"[robot_speech] status={status} ({self.feedback.log_message(status)})"
        )

    def _publish_event(self, event_type: str, text: str, confidence: float | None = None) -> None:
        msg = String()
        msg.data = json.dumps(
            {
                "type": event_type,
                "text": text,
                "confidence": confidence,
                "stamp": self.get_clock().now().nanoseconds / 1_000_000_000,
            }
        )
        self.event_pub.publish(msg)

    def _has_active_authorization(self) -> bool:
        if not self.require_password:
            return True
        if not self.password_verifier.is_enabled():
            return True
        return time.monotonic() < self.authorized_until

    def _authorize_speaker(self) -> bool:
        attempts = max(1, int(self.password_attempts))

        for attempt in range(1, attempts + 1):
            self._prompt_then_listen("prompting_password", "listening_password")
            self.get_logger().info(
                f"[robot_speech] Listening for password... attempt {attempt}/{attempts}"
            )
            ctx = self.pipeline.listen_and_transcribe()
            if not ctx.transcription:
                self.get_logger().warn("No password transcription received")
                self._publish_event("no_audio", "No password speech detected")
                self._publish_status("no_audio", wait=True)
                self._publish_status("password_rejected")
                continue

            self.get_logger().info(
                f"[robot_speech] Heard password candidate: {ctx.transcription!r}"
            )
            authorized, message = self.password_verifier.verify(ctx.transcription)
            if authorized:
                if self.auth_session_timeout_sec <= 0.0:
                    self.authorized_until = time.monotonic()
                else:
                    self.authorized_until = time.monotonic() + self.auth_session_timeout_sec
                self.get_logger().info(message)
                self.get_logger().info("[robot_speech] Password accepted.")
                return True

            self._publish_status("password_rejected", wait=True)
            self.get_logger().warn(message)
            self.get_logger().warn("[robot_speech] Password rejected.")

        self.get_logger().warn("[robot_speech] Maximum password attempts reached.")
        return False

    def _publish_text(self, text: str) -> None:
        if self.text_pub is None:
            return
        msg = String()
        msg.data = text
        self.text_pub.publish(msg)

    def _base_command(self) -> RobotCommand:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = "voice_commander_node"
        command.source = "voice"
        return command

    def _to_task_command(self, parsed_command) -> RobotCommand:
        if parsed_command.clarification_needed:
            raise UnsupportedVoiceCommand(
                f"Clarification needed: {parsed_command.clarification_message}"
            )

        if not parsed_command.is_high_confidence:
            raise UnsupportedVoiceCommand(
                f"Ignoring low-confidence voice command: {parsed_command.confidence:.2f}"
            )

        if len(parsed_command.actions) != 1:
            raise UnsupportedVoiceCommand(
                "Only one voice action can be sent as one RobotCommand; "
                f"got {len(parsed_command.actions)} actions"
            )

        action = parsed_command.actions[0]
        params = action.parameters
        command = self._base_command()

        if action.action == ActionType.PICK:
            command.command_type = "PICK_OBJECT"
            command.object_class = self._canonical_object_class(params.get("target_object", ""))
            command.object_color = self._canonical_color(params.get("color", ""))
            command.place_target = str(params.get("place_target", "box")).strip()
            command.priority = 94.0
            if not command.object_class:
                raise UnsupportedVoiceCommand("PICK_OBJECT requires target_object")
            self.get_logger().info(
                "[robot_speech] Parsed command: "
                f"pick object_class={command.object_class} "
                f"color={command.object_color} "
                f"place_target={command.place_target}"
            )
            return command

        if action.action == ActionType.MOVE_JOINT:
            command.command_type = "MOVE_JOINT"
            command.joint_id = self._joint_id(params.get("joint"))
            command.joint_target_deg = float(params.get("angle", 0.0))
            command.relative = False
            command.priority = 96.0
            self.get_logger().info(
                "[robot_speech] Parsed command: "
                f"joint_id={command.joint_id} "
                f"target={command.joint_target_deg:.2f} deg "
                "relative=false"
            )
            return command

        if action.action == ActionType.ROTATE_JOINT:
            command.command_type = "MOVE_JOINT"
            command.joint_id = self._joint_id(params.get("joint"))
            command.joint_delta_deg = float(params.get("delta_angle", 0.0))
            command.relative = True
            command.priority = 96.0
            self.get_logger().info(
                "[robot_speech] Parsed command: "
                f"joint_id={command.joint_id} "
                f"delta={command.joint_delta_deg:.2f} deg "
                "relative=true"
            )
            return command

        if action.action == ActionType.MOVE_HOME:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "home"
            command.priority = 95.0
            self.get_logger().info("[robot_speech] Parsed command: sequence_id=home")
            return command

        if action.action == ActionType.RUN_SEQUENCE:
            sequence_id = str(params.get("sequence_id", "")).strip()
            if not sequence_id:
                raise UnsupportedVoiceCommand("RUN_SEQUENCE requires sequence_id")
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = sequence_id
            command.priority = 95.0
            self.get_logger().info(
                f"[robot_speech] Parsed command: sequence_id={sequence_id}"
            )
            return command

        if action.action == ActionType.OPEN_GRIPPER:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "open_gripper"
            command.priority = 95.0
            self.get_logger().info("[robot_speech] Parsed command: sequence_id=open_gripper")
            return command

        if action.action == ActionType.CLOSE_GRIPPER:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "close_gripper"
            command.priority = 95.0
            self.get_logger().info("[robot_speech] Parsed command: sequence_id=close_gripper")
            return command

        if action.action == ActionType.STOP:
            command.command_type = "CANCEL"
            command.priority = 100.0
            return command

        raise UnsupportedVoiceCommand(
            f"Action '{action.action.value}' is not supported by /robot_task/command"
        )

    @staticmethod
    def _normalize_token(value: Any) -> str:
        text = str(value or "").lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^\w\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _canonical_object_class(cls, value: Any) -> str:
        normalized = cls._normalize_token(value)
        return OBJECT_CLASS_ALIASES.get(normalized, normalized)

    @classmethod
    def _canonical_color(cls, value: Any) -> str:
        normalized = cls._normalize_token(value)
        return COLOR_ALIASES.get(normalized, normalized)

    def _fallback_task_command_from_text(self, text: str) -> RobotCommand | None:
        normalized = self._normalize_token(text)
        if not normalized:
            return None

        control = self._fallback_control_command(normalized)
        if control is not None:
            return control

        sequence = self._fallback_sequence(normalized)
        if sequence:
            command = self._base_command()
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = sequence
            command.priority = 95.0
            self.get_logger().info(f"[robot_speech] Fallback command: sequence_id={sequence}")
            return command

        joint = self._fallback_joint(normalized)
        if joint is not None:
            return joint

        object_class = self._find_object_class(normalized)
        if object_class and self._has_object_action_word(normalized):
            command = self._base_command()
            command.command_type = "PICK_OBJECT"
            command.object_class = object_class
            command.object_color = self._find_color(normalized)
            command.place_target = "box"
            command.priority = 94.0
            self.get_logger().info(
                "[robot_speech] Fallback command: "
                f"pick object_class={command.object_class} "
                f"color={command.object_color} "
                f"place_target={command.place_target}"
            )
            return command

        if "agrupa" in normalized or "agrupar" in normalized:
            self.get_logger().warn(
                "[robot_speech] Fallback: 'agrupa las figuras' needs a defined sequence/action."
            )

        return None

    def _fallback_control_command(self, normalized: str) -> RobotCommand | None:
        command = self._base_command()
        if self._contains_phrase(
            normalized,
            [
                "emergencia",
                "paro de emergencia",
                "parada de emergencia",
                "estop",
                "e stop",
                "para todo",
            ],
        ):
            command.command_type = "ESTOP"
            command.priority = 100.0
            return command

        if self._contains_phrase(
            normalized,
            ["reanudar", "reanuda", "continua", "continuar", "resume"],
        ):
            command.command_type = "RESUME"
            command.priority = 100.0
            return command

        if self._contains_phrase(
            normalized,
            [
                "detente",
                "alto",
                "para",
                "parar",
                "cancelar",
                "cancela",
                "cancelo",
            ],
        ):
            command.command_type = "CANCEL"
            command.priority = 100.0
            return command

        return None

    def _clarification_for_text(self, text: str) -> str:
        normalized = self._normalize_token(text)
        if not normalized:
            return "I did not hear a command. Please try again."

        if self._fallback_sequence(normalized):
            return ""

        if ("joint" in normalized or "articulacion" in normalized) and "grado" not in normalized:
            return "Please include the angle, for example: move joint 1 to 30 degrees."

        if re.search(r"\b(?:mueve|move|gira|rota|rotate)\b", normalized):
            mentions_joint = "joint" in normalized or "articulacion" in normalized
            mentions_object = bool(self._find_object_class(normalized))
            if not mentions_joint and not mentions_object:
                return "Please include what should move, for example: move joint 1 to 30 degrees."

        if self._has_object_action_word(normalized) and not self._find_object_class(normalized):
            return "Please include the object, for example: pick the cube or grab the cylinder."

        if "agrupa" in normalized or "agrupar" in normalized:
            return "Grouping figures is not connected yet. Try: pick the cube or go home."

        return ""

    @staticmethod
    def _describe_robot_command(command: RobotCommand) -> str:
        if command.command_type == "PICK_OBJECT":
            color = f" {command.object_color}" if command.object_color else ""
            return f"Pick {command.object_class}{color}".strip()
        if command.command_type == "MOVE_JOINT":
            if command.relative:
                return f"Joint {command.joint_id} delta {command.joint_delta_deg:.2f} deg"
            return f"Joint {command.joint_id} target {command.joint_target_deg:.2f} deg"
        if command.command_type == "RUN_SEQUENCE":
            return f"Sequence {command.sequence_id}"
        return command.command_type

    @staticmethod
    def _has_object_action_word(normalized: str) -> bool:
        return any(
            re.search(rf"\b{word}\b", normalized)
            for word in ["agarra", "toma", "dame", "mueve", "recoge", "coge"]
        )

    @staticmethod
    def _fallback_sequence(normalized: str) -> str:
        for sequence_id, phrases in SEQUENCE_PHRASES.items():
            if VoiceCommanderNode._contains_phrase(normalized, phrases):
                return sequence_id
        if "home" in normalized or "casa" in normalized or "inicio" in normalized:
            return "home"
        if "abre" in normalized and "gripper" in normalized:
            return "open_gripper"
        if "cierra" in normalized and "gripper" in normalized:
            return "close_gripper"
        return ""

    @staticmethod
    def _contains_phrase(normalized: str, phrases: list[str]) -> bool:
        return any(
            re.search(rf"\b{re.escape(phrase)}\b", normalized)
            for phrase in phrases
        )

    def _fallback_joint(self, normalized: str) -> RobotCommand | None:
        if "joint" not in normalized and "articulacion" not in normalized:
            return None

        match = re.search(r"\b(?:joint|articulacion)\s+([a-z0-9.]+)\b", normalized)
        if not match:
            return None

        joint_value = self._parse_number(match.group(1))
        if joint_value is None:
            return None

        angle_match = re.search(r"\b(?:menos\s+)?[a-z0-9.]+\s+grados?\b", normalized[match.end():])
        if not angle_match:
            return None

        angle_text = angle_match.group(0).replace("grados", "").replace("grado", "").strip()
        angle = self._parse_number(angle_text)
        if angle is None:
            return None

        command = self._base_command()
        command.command_type = "MOVE_JOINT"
        command.joint_id = int(joint_value)
        command.priority = 96.0

        if re.search(r"\b(?:gira|rota|sube|baja)\b", normalized):
            command.joint_delta_deg = float(angle)
            command.relative = True
            self.get_logger().info(
                "[robot_speech] Fallback command: "
                f"joint_id={command.joint_id} delta={command.joint_delta_deg:.2f} deg relative=true"
            )
        else:
            command.joint_target_deg = float(angle)
            command.relative = False
            self.get_logger().info(
                "[robot_speech] Fallback command: "
                f"joint_id={command.joint_id} target={command.joint_target_deg:.2f} deg relative=false"
            )
        return command

    @classmethod
    def _find_object_class(cls, normalized: str) -> str:
        for alias, canonical in OBJECT_CLASS_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                return canonical
        return ""

    @classmethod
    def _find_color(cls, normalized: str) -> str:
        for alias, canonical in COLOR_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                return canonical
        return ""

    @staticmethod
    def _parse_number(text: str) -> float | None:
        token = text.strip().lower()
        sign = 1.0
        if token.startswith("menos "):
            sign = -1.0
            token = token.replace("menos ", "", 1).strip()
        try:
            return sign * float(token)
        except ValueError:
            pass
        if token in SPANISH_NUMBERS:
            return sign * SPANISH_NUMBERS[token]
        return None

    @staticmethod
    def _joint_id(joint: Any) -> int:
        joint_name = str(joint or "").strip().lower()
        if joint_name.startswith("joint"):
            joint_name = joint_name.replace("joint", "", 1)
        try:
            joint_id = int(joint_name)
        except ValueError as exc:
            raise UnsupportedVoiceCommand(f"Invalid joint name: {joint!r}") from exc
        if joint_id <= 0:
            raise UnsupportedVoiceCommand(f"Invalid joint id: {joint_id}")
        return joint_id


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiceCommanderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
