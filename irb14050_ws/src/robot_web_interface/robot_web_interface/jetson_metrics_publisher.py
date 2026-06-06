#!/usr/bin/env python3
"""Publish Jetson system metrics as JSON over ROS2."""

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


THERMAL_ROOT = Path("/sys/devices/virtual/thermal")
CPU_ROOT = Path("/sys/devices/system/cpu")
PROC_MEMINFO = Path("/proc/meminfo")
PROC_STAT = Path("/proc/stat")
PROC_UPTIME = Path("/proc/uptime")
DEVICE_MODEL = Path("/proc/device-tree/model")


class JetsonMetricsPublisher(Node):
    def __init__(self) -> None:
        super().__init__("jetson_metrics_publisher")
        self.declare_parameter("topic", "/system/jetson_metrics")
        self.declare_parameter("publish_hz", 0.5)

        topic = str(self.get_parameter("topic").value)
        publish_hz = max(0.1, float(self.get_parameter("publish_hz").value))

        self.publisher = self.create_publisher(String, topic, 10)
        self.timer = self.create_timer(1.0 / publish_hz, self._publish_metrics)
        self.get_logger().info(f"Publishing Jetson metrics on {topic}")

    def _publish_metrics(self) -> None:
        metrics = collect_metrics()
        msg = String()
        msg.data = json.dumps(metrics, separators=(",", ":"))
        self.publisher.publish(msg)


def collect_metrics() -> dict:
    warnings: list[str] = []
    tegrastats_raw = _read_tegrastats(warnings)
    temperatures = _read_temperatures(warnings)
    power_rails = _parse_power_rails(tegrastats_raw)
    cpu = _read_cpu_metrics(warnings)
    memory = _read_memory(warnings)
    swap = _read_swap(warnings)
    max_temperature_c = max((item["value_c"] for item in temperatures), default=None)
    total_power_mw = next(
        (rail["current_mw"] for rail in power_rails if rail["name"] == "VDD_IN"),
        None,
    )

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "ros2",
        "model": _read_device_model(),
        "power_mode": _read_power_mode(warnings),
        "uptime_seconds": _read_uptime_seconds(warnings),
        "load_average": [round(value, 2) for value in os.getloadavg()],
        "cpu": cpu,
        "cpu_usage_percent": _average_cpu_usage(cpu),
        "gpu_usage_percent": _parse_gpu_usage(tegrastats_raw),
        "memory": memory,
        "swap": swap,
        "disk": _read_disk("/"),
        "temperatures": temperatures,
        "max_temperature_c": max_temperature_c,
        "power_rails": power_rails,
        "total_power_mw": total_power_mw,
        "tegrastats_raw": tegrastats_raw,
        "warnings": warnings,
    }


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_device_model() -> str | None:
    model = _read_text(DEVICE_MODEL)
    return model.replace("\x00", "").strip() if model else None


def _read_power_mode(warnings: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["nvpmodel", "-q"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        warnings.append(f"nvpmodel unavailable: {exc}")
        return None

    if result.returncode != 0:
        warnings.append("nvpmodel returned a non-zero status")
        return None

    match = re.search(r"NV Power Mode:\s*(.+)", result.stdout)
    return match.group(1).strip() if match else result.stdout.strip() or None


def _read_tegrastats(warnings: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["timeout", "2", "tegrastats", "--interval", "1000"],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        warnings.append(f"tegrastats unavailable: {exc}")
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        warnings.append("tegrastats did not return metrics")
        return None
    return lines[-1]


def _read_meminfo(warnings: list[str]) -> dict[str, int]:
    text = _read_text(PROC_MEMINFO)
    if text is None:
        warnings.append("unable to read /proc/meminfo")
        return {}

    values: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(":")] = int(parts[1])
    return values


def _memory_metric(total_kb: int, available_kb: int) -> dict:
    total_mb = total_kb / 1024
    available_mb = available_kb / 1024
    used_mb = max(total_mb - available_mb, 0)
    used_percent = (used_mb / total_mb * 100) if total_mb else 0
    return {
        "total_mb": round(total_mb, 1),
        "used_mb": round(used_mb, 1),
        "available_mb": round(available_mb, 1),
        "used_percent": round(used_percent, 1),
    }


def _read_memory(warnings: list[str]) -> dict:
    meminfo = _read_meminfo(warnings)
    return _memory_metric(meminfo.get("MemTotal", 0), meminfo.get("MemAvailable", 0))


def _read_swap(warnings: list[str]) -> dict:
    meminfo = _read_meminfo(warnings)
    return _memory_metric(meminfo.get("SwapTotal", 0), meminfo.get("SwapFree", 0))


def _read_disk(mount: str) -> dict:
    usage = shutil.disk_usage(mount)
    total_gb = usage.total / 1024**3
    used_gb = usage.used / 1024**3
    available_gb = usage.free / 1024**3
    used_percent = (used_gb / total_gb * 100) if total_gb else 0
    return {
        "mount": mount,
        "total_gb": round(total_gb, 1),
        "used_gb": round(used_gb, 1),
        "available_gb": round(available_gb, 1),
        "used_percent": round(used_percent, 1),
    }


def _read_uptime_seconds(warnings: list[str]) -> float:
    text = _read_text(PROC_UPTIME)
    if text is None:
        warnings.append("unable to read /proc/uptime")
        return 0.0
    return round(float(text.split()[0]), 1)


def _read_temperatures(warnings: list[str]) -> list[dict]:
    if not THERMAL_ROOT.exists():
        warnings.append("thermal sysfs path does not exist")
        return []

    temperatures: list[dict] = []
    for zone in sorted(THERMAL_ROOT.glob("thermal_zone*")):
        name = _read_text(zone / "type")
        raw_temp = _read_text(zone / "temp")
        if not name or raw_temp is None:
            continue
        try:
            temperatures.append({"name": name, "value_c": round(int(raw_temp) / 1000, 1)})
        except ValueError:
            warnings.append(f"invalid thermal value for {name}")

    order = {
        "cpu-thermal": 0,
        "gpu-thermal": 1,
        "tj-thermal": 2,
        "soc0-thermal": 3,
        "soc1-thermal": 4,
        "soc2-thermal": 5,
        "cv0-thermal": 6,
        "cv1-thermal": 7,
        "cv2-thermal": 8,
    }
    return sorted(temperatures, key=lambda item: order.get(item["name"], 99))


def _read_cpu_snapshot() -> dict[int, tuple[int, int]]:
    text = _read_text(PROC_STAT)
    if text is None:
        return {}

    snapshot: dict[int, tuple[int, int]] = {}
    for line in text.splitlines():
        if not re.match(r"cpu\d+\s", line):
            continue
        parts = line.split()
        values = [int(value) for value in parts[1:]]
        idle = values[3] + values[4]
        total = sum(values)
        snapshot[int(parts[0][3:])] = (idle, total)
    return snapshot


def _read_cpu_metrics(warnings: list[str]) -> list[dict]:
    before = _read_cpu_snapshot()
    time.sleep(0.12)
    after = _read_cpu_snapshot()

    if not before or not after:
        warnings.append("unable to read CPU usage from /proc/stat")
        return []

    metrics: list[dict] = []
    for index in sorted(after):
        if index not in before:
            continue
        idle_before, total_before = before[index]
        idle_after, total_after = after[index]
        total_delta = total_after - total_before
        idle_delta = idle_after - idle_before
        usage_percent = (1 - idle_delta / total_delta) * 100 if total_delta > 0 else 0.0
        metrics.append(
            {
                "index": index,
                "usage_percent": round(max(usage_percent, 0), 1),
                "frequency_mhz": _read_cpu_frequency_mhz(index),
            }
        )
    return metrics


def _read_cpu_frequency_mhz(index: int) -> float | None:
    raw = _read_text(CPU_ROOT / f"cpu{index}" / "cpufreq" / "scaling_cur_freq")
    if raw is None:
        return None
    try:
        return round(int(raw) / 1000, 1)
    except ValueError:
        return None


def _average_cpu_usage(cpu: list[dict]) -> float | None:
    if not cpu:
        return None
    return round(sum(float(core["usage_percent"]) for core in cpu) / len(cpu), 1)


def _parse_gpu_usage(tegrastats_raw: str | None) -> float | None:
    if not tegrastats_raw:
        return None
    match = re.search(r"GR3D_FREQ\s+(\d+)%", tegrastats_raw)
    return float(match.group(1)) if match else None


def _parse_power_rails(tegrastats_raw: str | None) -> list[dict]:
    if not tegrastats_raw:
        return []

    rails: list[dict] = []
    for match in re.finditer(r"\b(VDD_[A-Z0-9_]+)\s+(\d+)mW(?:/(\d+)mW)?", tegrastats_raw):
        rails.append(
            {
                "name": match.group(1),
                "current_mw": int(match.group(2)),
                "average_mw": int(match.group(3)) if match.group(3) else None,
            }
        )
    return rails


def main(args=None) -> None:
    rclpy.init(args=args)
    node = JetsonMetricsPublisher()
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
