"""Shared helpers for behavior-tree behaviours."""

from __future__ import annotations

import py_trees
import rclpy
from geometry_msgs.msg import Twist

from robot_task_manager import blackboard_keys as bb_keys


class BlackboardBehavior(py_trees.behaviour.Behaviour):
    """Behavior base class with convenient blackboard and ROS node access."""

    def __init__(self, name: str, node):
        super().__init__(name=name)
        self.node = node
        self.blackboard = py_trees.blackboard.Blackboard()

    def bb_get(self, key: str, default=None):
        if py_trees.blackboard.Blackboard.exists(key):
            return self.blackboard.get(key)
        return default

    def bb_set(self, key: str, value) -> None:
        self.blackboard.set(key, value)

    def now(self) -> float:
        return self.node.get_clock().now().nanoseconds * 1e-9

    def set_status(
        self,
        *,
        mode: str | None = None,
        message: str | None = None,
        progress: float | None = None,
        error_code: str | None = None,
        current_task: str | None = None,
    ) -> None:
        if mode is not None:
            self.bb_set(bb_keys.CURRENT_MODE, mode)
        if message is not None:
            self.bb_set(bb_keys.STATUS_TEXT, message)
        if progress is not None:
            self.bb_set(bb_keys.TASK_PROGRESS, float(progress))
        if error_code is not None:
            self.bb_set(bb_keys.ERROR_CODE, error_code)
        if current_task is not None:
            self.bb_set(bb_keys.CURRENT_TASK, current_task)

    def publish_zero_twist(self) -> None:
        if not rclpy.ok():
            return
        try:
            self.node.servo_pub.publish(Twist())
        except Exception as exc:  # noqa: BLE001 - shutdown can invalidate publishers first.
            self.node.get_logger().debug(f"Skipping zero twist publish: {exc}")


class TimedSimulationBehavior(BlackboardBehavior):
    """Small non-blocking timed behavior for mock motion primitives."""

    def __init__(
        self,
        name: str,
        node,
        *,
        duration_s: float | None = None,
        mode: str = "IDLE",
        message: str = "",
        busy: bool = True,
    ):
        super().__init__(name, node)
        self.duration_s = duration_s
        self.mode = mode
        self.message = message or name
        self.busy = busy
        self._start_time: float | None = None

    def initialise(self) -> None:
        self._start_time = self.now()
        if self.busy:
            self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode=self.mode, message=self.message, progress=0.0)

    def update(self) -> py_trees.common.Status:
        duration = self.duration_s
        if duration is None:
            duration = float(self.node.simulation_motion_duration_s)
        elapsed = self.now() - (self._start_time or self.now())
        progress = 1.0 if duration <= 0.0 else min(1.0, elapsed / duration)
        self.set_status(mode=self.mode, message=self.message, progress=progress)
        if progress >= 1.0:
            if self.busy:
                self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID and self.busy:
            self.bb_set(bb_keys.ARM_BUSY, False)
