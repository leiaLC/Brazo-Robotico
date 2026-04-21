"""
Integration test: simulates a full pipeline cycle end-to-end without hardware.
Replaces audio/video/LLM with stubs so it runs on any machine.

Run with:
    python -m pytest tests/test_pipeline_integration.py -v
"""

from __future__ import annotations

import json
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from modules.context import ContextBuilder, PipelineContext
from modules.parser import ActionParser
from modules.vision.detector import DetectionResult, Detection
from pipeline import VoiceCommandPipeline


# ── Stubs ──────────────────────────────────────────────────────────────────────

def make_audio_stub(text: str):
    """Returns a mock AudioCapture that always yields a dummy numpy array."""
    stub = MagicMock()
    stub.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
    return stub


def make_transcriber_stub(text: str):
    stub = MagicMock()
    result = MagicMock()
    result.text = text
    result.language = "es"
    result.language_probability = 0.99
    stub.transcribe.return_value = result
    return stub


def make_llm_stub(response_dict: dict):
    stub = MagicMock()
    stub.generate.return_value = json.dumps(response_dict)
    return stub


def make_detection_result(objects: list[str]) -> DetectionResult:
    detections = [
        Detection(
            class_id=i,
            class_name=name,
            confidence=0.9,
            bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
            center={"cx": 55, "cy": 55},
        )
        for i, name in enumerate(objects)
    ]
    return DetectionResult(detections=detections, frame_width=640, frame_height=480)


def make_video_stub(objects: list[str]):
    video = MagicMock()
    video.get_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

    detector = MagicMock()
    detector.detect.return_value = make_detection_result(objects)

    return video, detector


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestPipelineIntegration:

    def _build_pipeline(
        self,
        transcription: str,
        llm_response: dict,
        detected_objects: Optional[list[str]] = None,
        vision_enabled: bool = True,
    ) -> VoiceCommandPipeline:
        video, detector = (
            make_video_stub(detected_objects or []) if vision_enabled else (None, None)
        )
        return VoiceCommandPipeline(
            audio_capture=make_audio_stub(transcription),
            transcriber=make_transcriber_stub(transcription),
            video_capture=video,
            detector=detector,
            llm_client=make_llm_stub(llm_response),
            action_parser=ActionParser(),
            context_builder=ContextBuilder(),
            vision_enabled=vision_enabled,
        )

    def test_move_joint_command(self):
        pipeline = self._build_pipeline(
            transcription="mueve el joint 1 a 45 grados",
            llm_response={
                "intent": "Rotate joint1 to 45 degrees",
                "confidence": 0.95,
                "actions": [
                    {"action": "move_joint", "parameters": {"joint": "joint1", "angle": 45}}
                ],
                "clarification_needed": False,
                "clarification_message": "",
            },
        )
        ctx = pipeline.run_cycle()
        assert ctx.success
        assert ctx.parsed_command.actions[0].action.value == "move_joint"

    def test_move_home_command(self):
        pipeline = self._build_pipeline(
            transcription="ve a home",
            llm_response={
                "intent": "Move to home position",
                "confidence": 0.99,
                "actions": [{"action": "move_home", "parameters": {"speed": 30}}],
                "clarification_needed": False,
                "clarification_message": "",
            },
        )
        ctx = pipeline.run_cycle()
        assert ctx.success
        assert len(ctx.parsed_command.actions) == 1

    def test_pick_with_vision(self):
        pipeline = self._build_pipeline(
            transcription="agarra la taza",
            llm_response={
                "intent": "Pick up the cup",
                "confidence": 0.88,
                "actions": [
                    {"action": "pick", "parameters": {"target_object": "cup", "speed": 20}}
                ],
                "clarification_needed": False,
                "clarification_message": "",
            },
            detected_objects=["cup", "table"],
        )
        ctx = pipeline.run_cycle()
        assert ctx.success
        assert ctx.detection_result is not None
        assert "cup" in ctx.detection_result.object_names

    def test_clarification_needed(self):
        pipeline = self._build_pipeline(
            transcription="mueve eso",
            llm_response={
                "intent": "Ambiguous move command",
                "confidence": 0.35,
                "actions": [],
                "clarification_needed": True,
                "clarification_message": "¿Qué objeto debo mover?",
            },
        )
        ctx = pipeline.run_cycle()
        assert ctx.success  # parse still succeeds
        assert ctx.parsed_command.clarification_needed

    def test_llm_parse_error(self):
        pipeline = self._build_pipeline(
            transcription="algo",
            llm_response={"broken": "response with no required fields"},
        )
        ctx = pipeline.run_cycle()
        assert not ctx.success
        assert ctx.parse_error is not None

    def test_multi_action_sequence(self):
        pipeline = self._build_pipeline(
            transcription="abre el gripper y ve a home",
            llm_response={
                "intent": "Open gripper then go home",
                "confidence": 0.92,
                "actions": [
                    {"action": "open_gripper", "parameters": {"speed": 50}},
                    {"action": "move_home", "parameters": {"speed": 30}},
                ],
                "clarification_needed": False,
                "clarification_message": "",
            },
        )
        ctx = pipeline.run_cycle()
        assert ctx.success
        assert len(ctx.parsed_command.actions) == 2

    def test_cycle_id_increments(self):
        pipeline = self._build_pipeline(
            transcription="stop",
            llm_response={
                "intent": "Stop",
                "confidence": 0.99,
                "actions": [{"action": "stop", "parameters": {}}],
                "clarification_needed": False,
                "clarification_message": "",
            },
        )
        ctx1 = pipeline.run_cycle()
        ctx2 = pipeline.run_cycle()
        assert ctx2.cycle_id == ctx1.cycle_id + 1
