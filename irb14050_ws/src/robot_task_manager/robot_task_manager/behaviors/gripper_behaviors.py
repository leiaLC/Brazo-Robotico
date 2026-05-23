"""Gripper behaviours."""

import py_trees

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior


class _GripperCommand(BlackboardBehavior):
    command = "open"
    label = "Opening gripper"

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._start_time: float | None = None
        self._published = False

    def initialise(self) -> None:
        self._start_time = self.now()
        self._published = False
        self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode="VOICE_PICK", message=self.label, progress=0.65)

    def update(self) -> py_trees.common.Status:
        if not self._published:
            self.node.publish_gripper_command(self.command)
            self.node.get_logger().info(f"Gripper command: {self.command}")
            self._published = True

        elapsed = self.now() - (self._start_time or self.now())
        if elapsed >= float(self.node.gripper_motion_duration_s):
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            self.bb_set(bb_keys.ARM_BUSY, False)


class OpenGripper(_GripperCommand):
    command = "open"
    label = "Opening gripper"


class CloseGripper(_GripperCommand):
    command = "close"
    label = "Closing gripper"
