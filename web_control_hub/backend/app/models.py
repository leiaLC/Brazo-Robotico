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


class GripperRequest(BaseModel):
    command: str = Field(pattern="^(open|close)$")


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


class JetsonMemoryMetrics(BaseModel):
    total_mb: float
    used_mb: float
    available_mb: float
    used_percent: float


class JetsonDiskMetrics(BaseModel):
    mount: str
    total_gb: float
    used_gb: float
    available_gb: float
    used_percent: float


class JetsonCpuCoreMetric(BaseModel):
    index: int
    usage_percent: float
    frequency_mhz: float | None = None


class JetsonTemperatureMetric(BaseModel):
    name: str
    value_c: float


class JetsonPowerRailMetric(BaseModel):
    name: str
    current_mw: int
    average_mw: int | None = None


class JetsonMetrics(BaseModel):
    checked_at: str
    source: str = "ros2"
    model: str | None
    power_mode: str | None
    uptime_seconds: float
    load_average: list[float]
    cpu: list[JetsonCpuCoreMetric]
    cpu_usage_percent: float | None
    gpu_usage_percent: float | None
    memory: JetsonMemoryMetrics
    swap: JetsonMemoryMetrics
    disk: JetsonDiskMetrics
    temperatures: list[JetsonTemperatureMetric]
    max_temperature_c: float | None
    power_rails: list[JetsonPowerRailMetric]
    total_power_mw: int | None
    tegrastats_raw: str | None
    warnings: list[str]
