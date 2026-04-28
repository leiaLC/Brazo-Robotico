"""
Unit tests for the action parser and schema validation.
These run without any hardware (no microphone, camera, or GPU needed).

Run with:
    python -m pytest tests/test_parser.py -v
"""

from __future__ import annotations

import json
import pytest

from modules.parser.action_parser import ActionParser, ParseError
from modules.parser.schema import ActionType, RobotCommand


@pytest.fixture
def parser() -> ActionParser:
    return ActionParser()


# ── Valid command samples ──────────────────────────────────────────────────────

VALID_MOVE_JOINT = {
    "intent": "Rotate joint1 to 45 degrees",
    "confidence": 0.97,
    "actions": [
        {"action": "move_joint", "parameters": {"joint": "joint1", "angle": 45, "speed": 30}}
    ],
    "clarification_needed": False,
    "clarification_message": "",
}

VALID_MOVE_HOME = {
    "intent": "Move to home position",
    "confidence": 0.99,
    "actions": [{"action": "move_home", "parameters": {"speed": 30}}],
    "clarification_needed": False,
    "clarification_message": "",
}

VALID_PICK = {
    "intent": "Pick up the cup",
    "confidence": 0.85,
    "actions": [
        {"action": "pick", "parameters": {"target_object": "cup", "speed": 20}}
    ],
    "clarification_needed": False,
    "clarification_message": "",
}

VALID_MULTI_ACTION = {
    "intent": "Open gripper then move home",
    "confidence": 0.91,
    "actions": [
        {"action": "open_gripper", "parameters": {"speed": 50}},
        {"action": "move_home", "parameters": {"speed": 30}},
    ],
    "clarification_needed": False,
    "clarification_message": "",
}

VALID_CLARIFICATION = {
    "intent": "Ambiguous placement target",
    "confidence": 0.4,
    "actions": [],
    "clarification_needed": True,
    "clarification_message": "Where should I place the object?",
}


# ── Tests: happy path ──────────────────────────────────────────────────────────

class TestValidCommands:
    def test_move_joint(self, parser):
        cmd = parser.parse(json.dumps(VALID_MOVE_JOINT))
        assert isinstance(cmd, RobotCommand)
        assert cmd.actions[0].action == ActionType.MOVE_JOINT
        assert cmd.actions[0].parameters["joint"] == "joint1"
        assert cmd.actions[0].parameters["angle"] == 45
        assert cmd.confidence == pytest.approx(0.97)

    def test_move_home(self, parser):
        cmd = parser.parse(json.dumps(VALID_MOVE_HOME))
        assert cmd.actions[0].action == ActionType.MOVE_HOME
        assert cmd.is_high_confidence

    def test_pick(self, parser):
        cmd = parser.parse(json.dumps(VALID_PICK))
        assert cmd.actions[0].action == ActionType.PICK
        assert cmd.actions[0].parameters["target_object"] == "cup"

    def test_multi_action(self, parser):
        cmd = parser.parse(json.dumps(VALID_MULTI_ACTION))
        assert len(cmd.actions) == 2
        assert cmd.actions[0].action == ActionType.OPEN_GRIPPER
        assert cmd.actions[1].action == ActionType.MOVE_HOME

    def test_clarification_needed(self, parser):
        cmd = parser.parse(json.dumps(VALID_CLARIFICATION))
        assert cmd.clarification_needed is True
        assert "Where" in cmd.clarification_message
        assert len(cmd.actions) == 0


# ── Tests: JSON extraction ─────────────────────────────────────────────────────

class TestJsonExtraction:
    def test_plain_json(self, parser):
        cmd = parser.parse(json.dumps(VALID_MOVE_HOME))
        assert cmd is not None

    def test_json_in_markdown_fence(self, parser):
        wrapped = f"```json\n{json.dumps(VALID_MOVE_HOME)}\n```"
        cmd = parser.parse(wrapped)
        assert cmd.actions[0].action == ActionType.MOVE_HOME

    def test_json_with_preamble(self, parser):
        text = f"Sure! Here is the command:\n{json.dumps(VALID_MOVE_JOINT)}\nHope that helps!"
        cmd = parser.parse(text)
        assert cmd.actions[0].action == ActionType.MOVE_JOINT

    def test_empty_string_raises(self, parser):
        with pytest.raises(ParseError):
            parser.parse("")

    def test_no_json_raises(self, parser):
        with pytest.raises(ParseError):
            parser.parse("I cannot understand your command.")


# ── Tests: schema validation ───────────────────────────────────────────────────

class TestSchemaValidation:
    def test_invalid_action_type_raises(self, parser):
        bad = {**VALID_MOVE_JOINT, "actions": [{"action": "fly_away", "parameters": {}}]}
        with pytest.raises(ParseError):
            parser.parse(json.dumps(bad))

    def test_angle_out_of_range_raises(self, parser):
        bad = {
            **VALID_MOVE_JOINT,
            "actions": [
                {"action": "move_joint", "parameters": {"joint": "joint1", "angle": 999}}
            ],
        }
        with pytest.raises(ParseError):
            parser.parse(json.dumps(bad))

    def test_invalid_joint_name_raises(self, parser):
        bad = {
            **VALID_MOVE_JOINT,
            "actions": [
                {"action": "move_joint", "parameters": {"joint": "turbo_joint", "angle": 45}}
            ],
        }
        with pytest.raises(ParseError):
            parser.parse(json.dumps(bad))

    def test_speed_out_of_range_raises(self, parser):
        bad = {
            **VALID_MOVE_JOINT,
            "actions": [
                {
                    "action": "move_joint",
                    "parameters": {"joint": "joint1", "angle": 45, "speed": 150},
                }
            ],
        }
        with pytest.raises(ParseError):
            parser.parse(json.dumps(bad))

    def test_confidence_out_of_range_raises(self, parser):
        bad = {**VALID_MOVE_HOME, "confidence": 1.5}
        with pytest.raises(ParseError):
            parser.parse(json.dumps(bad))


# ── Tests: safe parse ──────────────────────────────────────────────────────────

class TestParseSafe:
    def test_success_returns_command(self, parser):
        cmd, err = parser.parse_safe(json.dumps(VALID_MOVE_HOME))
        assert cmd is not None
        assert err is None

    def test_failure_returns_error(self, parser):
        cmd, err = parser.parse_safe("not json at all")
        assert cmd is None
        assert err is not None
        assert isinstance(err, str)


# ── Tests: summary rendering ───────────────────────────────────────────────────

class TestSummary:
    def test_summary_contains_intent(self, parser):
        cmd = parser.parse(json.dumps(VALID_MOVE_JOINT))
        summary = cmd.summary()
        assert "Rotate joint1" in summary
        assert "move_joint" in summary

    def test_low_confidence_label(self, parser):
        low = {**VALID_MOVE_HOME, "confidence": 0.4}
        cmd = parser.parse(json.dumps(low))
        assert "LOW" in cmd.summary()
