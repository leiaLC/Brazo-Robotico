"""Joint limit loading and validation helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class JointLimit:
    name: str
    min_deg: float
    max_deg: float


class JointLimitValidator:
    """Validate degree-space joint targets against a YAML limit file."""

    def __init__(self, limits: list[JointLimit]):
        self.limits = limits

    @classmethod
    def from_yaml(cls, path: str | Path) -> "JointLimitValidator":
        limit_path = Path(path)
        if not limit_path.exists():
            raise FileNotFoundError(f"Joint limits file not found: {limit_path}")

        data = yaml.safe_load(limit_path.read_text(encoding="utf-8")) or {}
        joints = data.get("joints", {})
        limits: list[JointLimit] = []
        for index in range(1, len(joints) + 1):
            name = f"joint_{index}"
            if name not in joints:
                raise ValueError(f"Missing joint limit entry: {name}")
            entry = joints[name]
            limits.append(
                JointLimit(
                    name=name,
                    min_deg=float(entry["min_deg"]),
                    max_deg=float(entry["max_deg"]),
                )
            )
        if not limits:
            raise ValueError(f"No joints found in {limit_path}")
        return cls(limits)

    def validate(self, values_deg: Iterable[float]) -> tuple[bool, str]:
        values = list(values_deg)
        if len(values) != len(self.limits):
            return False, f"Expected {len(self.limits)} joints, got {len(values)}"

        for value, limit in zip(values, self.limits):
            if value < limit.min_deg or value > limit.max_deg:
                return (
                    False,
                    f"{limit.name}={value:.2f} deg outside "
                    f"[{limit.min_deg:.2f}, {limit.max_deg:.2f}]",
                )
        return True, "ok"

    def clamp(self, values_deg: Iterable[float]) -> list[float]:
        return [
            max(limit.min_deg, min(float(value), limit.max_deg))
            for value, limit in zip(values_deg, self.limits)
        ]

    @property
    def joint_count(self) -> int:
        return len(self.limits)
