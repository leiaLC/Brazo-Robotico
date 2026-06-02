"""
Pydantic schemas for robot arm actions.
All parsed commands are validated against these models before being used.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    MOVE_JOINT = "move_joint"
    MOVE_CARTESIAN = "move_cartesian"
    OPEN_GRIPPER = "open_gripper"
    CLOSE_GRIPPER = "close_gripper"
    MOVE_HOME = "move_home"
    STOP = "stop"
    PICK = "pick"
    PLACE = "place"
    ROTATE_JOINT = "rotate_joint"


class JointName(str, Enum):
    JOINT1 = "joint1"
    JOINT2 = "joint2"
    JOINT3 = "joint3"
    JOINT4 = "joint4"
    JOINT5 = "joint5"
    JOINT6 = "joint6"


# ── Parameter models ───────────────────────────────────────────────────────────

class SpeedMixin(BaseModel):
    speed: float = Field(default=30.0, ge=0.0, le=100.0)


class MoveJointParams(SpeedMixin):
    joint: JointName
    angle: float = Field(..., ge=-360.0, le=360.0, description="Target angle in degrees")


class MoveCartesianParams(SpeedMixin):
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    roll: Optional[float] = None
    pitch: Optional[float] = None
    yaw: Optional[float] = None


class GripperParams(SpeedMixin):
    opening: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class MoveHomeParams(SpeedMixin):
    pass


class StopParams(BaseModel):
    pass


class PickParams(SpeedMixin):
    target_object: str
    approach_height: float = Field(default=0.1, ge=0.0)


class PlaceParams(SpeedMixin):
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    target_zone: Optional[str] = None


class RotateJointParams(SpeedMixin):
    joint: JointName
    delta_angle: float = Field(..., ge=-360.0, le=360.0)


# ── Action union model ─────────────────────────────────────────────────────────

PARAMS_MAP: dict[ActionType, type[BaseModel]] = {
    ActionType.MOVE_JOINT: MoveJointParams,
    ActionType.MOVE_CARTESIAN: MoveCartesianParams,
    ActionType.OPEN_GRIPPER: GripperParams,
    ActionType.CLOSE_GRIPPER: GripperParams,
    ActionType.MOVE_HOME: MoveHomeParams,
    ActionType.STOP: StopParams,
    ActionType.PICK: PickParams,
    ActionType.PLACE: PlaceParams,
    ActionType.ROTATE_JOINT: RotateJointParams,
}


class RobotAction(BaseModel):
    action: ActionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    _validated_params: Optional[BaseModel] = None

    def validate_parameters(self) -> BaseModel:
        """Validates parameters against the action-specific schema."""
        param_model = PARAMS_MAP.get(self.action)
        if param_model is None:
            raise ValueError(f"Unknown action type: {self.action}")
        return param_model(**self.parameters)


# ── Top-level command model ────────────────────────────────────────────────────

class RobotCommand(BaseModel):
    intent: str = Field(..., description="Human-readable summary of the command")
    confidence: float = Field(..., ge=0.0, le=1.0)
    actions: list[RobotAction] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_message: str = ""

    @field_validator("actions")
    @classmethod
    def at_least_one_action_or_clarification(
        cls, v: list, info
    ) -> list:
        # Allow empty actions if clarification is needed — checked at parse time
        return v

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7

    def summary(self) -> str:
        lines = [
            f"Intent   : {self.intent}",
            f"Confidence: {self.confidence:.2f} ({'HIGH' if self.is_high_confidence else 'LOW'})",
        ]
        if self.clarification_needed:
            lines.append(f"Clarification needed: {self.clarification_message}")
        for i, act in enumerate(self.actions, 1):
            lines.append(f"  Action {i}: {act.action.value} — {act.parameters}")
        return "\n".join(lines)
