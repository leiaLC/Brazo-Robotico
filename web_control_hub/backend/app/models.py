from pydantic import BaseModel, Field, field_validator, model_validator


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


class GripperRequest(BaseModel):
    command: str = Field(pattern="^(open|close)$")


class SequenceRequest(BaseModel):
    sequence_id: str = Field(min_length=1)


class VoiceTextRequest(BaseModel):
    text: str = Field(min_length=1)


class PoseRequest(BaseModel):
    frame_id: str = Field(default="base_link", min_length=1)
    x: float
    y: float
    z: float
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0
    qw: float = 1.0

    @field_validator("x", "y", "z", "qx", "qy", "qz", "qw")
    @classmethod
    def validate_finite_pose_values(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("pose values must be finite numbers")
        return value


class DetectionRequest(BaseModel):
    class_name: str = Field(min_length=1)
    color: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_width: int = Field(default=0, ge=0)
    bbox_height: int = Field(default=0, ge=0)
    pose_camera: PoseRequest | None = None
    pose_base: PoseRequest | None = None
    has_valid_depth: bool = True

    @model_validator(mode="after")
    def require_pose(self) -> "DetectionRequest":
        if self.pose_camera is None and self.pose_base is None:
            raise ValueError("pose_camera or pose_base is required")
        return self


class DetectionBatchRequest(BaseModel):
    detections: list[DetectionRequest] = Field(min_length=1, max_length=50)


class RobotCommandRequest(BaseModel):
    source: str = Field(default="remote_ai", min_length=1)
    command_type: str = Field(
        pattern="^(PICK_OBJECT|MOVE_JOINT|WEB_TELEOP|RUN_SEQUENCE|XBOX_TELEOP|CANCEL|ESTOP|PAUSE|RESUME)$"
    )
    object_class: str = ""
    object_color: str = ""
    place_target: str = ""
    joint_id: int = 0
    joint_delta_deg: float = 0.0
    joint_target_deg: float = 0.0
    relative: bool = False
    sequence_id: str = ""
    joint_values: list[float] = Field(default_factory=list, max_length=7)
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0
    priority: float = Field(default=90.0, ge=0.0, le=100.0)

    @field_validator(
        "joint_delta_deg",
        "joint_target_deg",
        "linear_x",
        "linear_y",
        "linear_z",
        "angular_x",
        "angular_y",
        "angular_z",
        "priority",
    )
    @classmethod
    def validate_finite_command_values(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("command values must be finite numbers")
        return value

    @field_validator("joint_values")
    @classmethod
    def validate_joint_values(cls, values: list[float]) -> list[float]:
        if values and len(values) != 7:
            raise ValueError("joint_values must be empty or contain exactly 7 values")
        for value in values:
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError("joint_values must be finite numbers")
        return values


class RobotState(BaseModel):
    connected: bool
    state_count: int
    joint_names: list[str]
    positions_rad: list[float] | None
    positions_deg: list[float] | None
