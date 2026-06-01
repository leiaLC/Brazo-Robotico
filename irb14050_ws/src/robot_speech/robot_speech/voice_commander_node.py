"""ROS 2 node that runs the voice pipeline and publishes task commands."""

from __future__ import annotations

import os
import time
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
from .modules.hardware import get_hardware_config
from .modules.llm import LlamaCppClient
from .modules.parser import ActionParser
from .modules.parser.schema import ActionType
from .modules.speaker.password_verifier import PasswordVerifier
from .pipeline import VoiceCommandPipeline


COMMAND_TOPIC = "/robot_task/command"
TEXT_TOPIC = "/voice/text"
START_TOPIC = "/voice/start_listening"


class UnsupportedVoiceCommand(ValueError):
    """Raised when a parsed LLM action cannot be represented in RobotCommand."""


class VoiceCommanderNode(Node):
    """Run STT -> LLM -> parser and publish robot_task_msgs/RobotCommand."""

    def __init__(self) -> None:
        super().__init__("voice_pipeline_node")

        self.declare_parameter("publish_voice_text", False)
        self.declare_parameter("triggered_mode", False)
        self.publish_voice_text = bool(self.get_parameter("publish_voice_text").value)
        self.triggered_mode = bool(self.get_parameter("triggered_mode").value)
        self.cycle_active = False
        self.command_pub = self.create_publisher(RobotCommand, COMMAND_TOPIC, 10)
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

        cfg = get_hardware_config(self._load_config())
        cuda = cfg["hardware"]["cuda"]
        device = "CUDA" if cuda else "CPU"
        self.get_logger().info(f"Voice pipeline starting on {device}")
        self.password_verifier = PasswordVerifier(cfg["speaker_verification"])
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
        )

        self.timer = None
        if not self.triggered_mode:
            self.timer = self.create_timer(0.1, self.run_cycle)

        self.get_logger().info(
            f"voice_pipeline_node ready: publishing RobotCommand on {COMMAND_TOPIC}"
        )
        if self.triggered_mode:
            self.get_logger().info(
                f"Triggered mode enabled: waiting for {START_TOPIC}"
            )

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

        if not self._has_active_authorization():
            if not self._authorize_speaker():
                self._finish_cycle()
                return

        self.get_logger().info("Waiting for a voice command...")

        ctx = self.pipeline.run_cycle()
        if ctx.transcription:
            if self.publish_voice_text:
                self._publish_text(ctx.transcription)
            self.get_logger().info(f"Recognized voice text: {ctx.transcription!r}")
        else:
            self.get_logger().warn("No voice detected")
            self._finish_cycle()
            return

        if ctx.parse_error:
            self.get_logger().error(f"LLM/parser error: {ctx.parse_error}")
            self._finish_cycle()
            return

        if not ctx.success:
            self.get_logger().warn("Pipeline finished without a valid command")
            self._finish_cycle()
            return

        try:
            command = self._to_task_command(ctx.parsed_command)
        except UnsupportedVoiceCommand as exc:
            self.get_logger().warn(str(exc))
            self._finish_cycle()
            return

        self.command_pub.publish(command)
        self.get_logger().info(
            f"Published {command.command_type} command on {COMMAND_TOPIC}"
        )
        self._finish_cycle()

    def _start_listening_callback(self, _msg: Empty) -> None:
        self.get_logger().info(f"Received voice start request on {START_TOPIC}")
        self.run_cycle()

    def _finish_cycle(self) -> None:
        self.cycle_active = False
        if self.timer is not None:
            self.timer.reset()

    def _has_active_authorization(self) -> bool:
        if not self.password_verifier.is_enabled():
            return True
        return time.monotonic() < self.authorized_until

    def _authorize_speaker(self) -> bool:
        self.get_logger().info("Waiting for voice password...")
        ctx = self.pipeline.listen_and_transcribe()
        if not ctx.transcription:
            self.get_logger().warn("No password transcription received")
            return False

        authorized, message = self.password_verifier.verify(ctx.transcription)
        if not authorized:
            self.get_logger().warn(message)
            return False

        if self.auth_session_timeout_sec <= 0.0:
            self.authorized_until = time.monotonic()
        else:
            self.authorized_until = time.monotonic() + self.auth_session_timeout_sec
        self.get_logger().info(message)
        return True

    def _publish_text(self, text: str) -> None:
        if self.text_pub is None:
            return
        msg = String()
        msg.data = text
        self.text_pub.publish(msg)

    def _base_command(self) -> RobotCommand:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = "voice_pipeline_node"
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
            command.object_class = str(params.get("target_object", "")).strip()
            command.object_color = str(params.get("color", "")).strip()
            command.place_target = str(params.get("place_target", "box")).strip()
            command.priority = 94.0
            if not command.object_class:
                raise UnsupportedVoiceCommand("PICK_OBJECT requires target_object")
            return command

        if action.action == ActionType.MOVE_JOINT:
            command.command_type = "MOVE_JOINT"
            command.joint_id = self._joint_id(params.get("joint"))
            command.joint_target_deg = float(params.get("angle", 0.0))
            command.relative = False
            command.priority = 96.0
            return command

        if action.action == ActionType.ROTATE_JOINT:
            command.command_type = "MOVE_JOINT"
            command.joint_id = self._joint_id(params.get("joint"))
            command.joint_delta_deg = float(params.get("delta_angle", 0.0))
            command.relative = True
            command.priority = 96.0
            return command

        if action.action == ActionType.MOVE_HOME:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "home"
            command.priority = 95.0
            return command

        if action.action == ActionType.OPEN_GRIPPER:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "open_gripper"
            command.priority = 95.0
            return command

        if action.action == ActionType.CLOSE_GRIPPER:
            command.command_type = "RUN_SEQUENCE"
            command.sequence_id = "close_gripper"
            command.priority = 95.0
            return command

        if action.action == ActionType.STOP:
            command.command_type = "CANCEL"
            command.priority = 100.0
            return command

        raise UnsupportedVoiceCommand(
            f"Action '{action.action.value}' is not supported by /robot_task/command"
        )

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
