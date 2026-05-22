from pydantic import BaseModel, Field, field_validator


class JointTargetRequest(BaseModel):
    positions_deg: list[float] = Field(min_length=7, max_length=7)

    @field_validator("positions_deg")
    @classmethod
    def validate_finite_values(cls, values: list[float]) -> list[float]:
        for value in values:
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError("joint values must be finite numbers")
        return values


class TeleopState(BaseModel):
    enabled: bool


class TeleopTwistRequest(BaseModel):
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0


class SequenceRequest(BaseModel):
    sequence_id: str = Field(min_length=1)


class VoiceTextRequest(BaseModel):
    text: str = Field(min_length=1)


class RobotState(BaseModel):
    connected: bool
    state_count: int
    joint_names: list[str]
    positions_rad: list[float] | None
    positions_deg: list[float] | None
