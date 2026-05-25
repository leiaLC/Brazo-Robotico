"""Safety and system-state behaviours."""

import py_trees

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior


class UpdateSystemState(BlackboardBehavior):
    """Refresh default blackboard state before each behavior-tree tick."""

    def update(self) -> py_trees.common.Status:
        defaults = {
            bb_keys.CURRENT_COMMAND: None,
            bb_keys.CURRENT_MODE: "IDLE",
            bb_keys.ROBOT_READY: bool(self.node.simulation_mode),
            bb_keys.ESTOP_ACTIVE: False,
            bb_keys.ARM_BUSY: False,
            bb_keys.TELEOP_ACTIVE: False,
            bb_keys.YOLO_DETECTIONS: [],
            bb_keys.STATUS_TEXT: "Idle",
            bb_keys.ERROR_CODE: "",
            bb_keys.TASK_PROGRESS: 0.0,
            bb_keys.CURRENT_TASK: "",
            bb_keys.JOINT_STATE_DEG: [0.0] * int(self.node.joint_count),
        }
        for key, value in defaults.items():
            if not py_trees.blackboard.Blackboard.exists(key):
                self.bb_set(key, value)

        if self.node.simulation_mode:
            self.bb_set(bb_keys.ROBOT_READY, True)

        if self.bb_get(bb_keys.ESTOP_ACTIVE, False):
            self.bb_set(bb_keys.CURRENT_MODE, "ESTOP")

        return py_trees.common.Status.SUCCESS


class CheckRobotReady(BlackboardBehavior):
    """Gate execution on robot readiness."""

    def update(self) -> py_trees.common.Status:
        if self.node.simulation_mode:
            self.bb_set(bb_keys.ROBOT_READY, True)
            return py_trees.common.Status.SUCCESS

        if self.bb_get(bb_keys.ROBOT_READY, False):
            return py_trees.common.Status.SUCCESS

        self.set_status(mode="ERROR", message="Robot is not ready", error_code="ROBOT_NOT_READY")
        return py_trees.common.Status.FAILURE


class CheckEStop(BlackboardBehavior):
    """Keep estop state visible while allowing the emergency branch to tick."""

    def update(self) -> py_trees.common.Status:
        if self.bb_get(bb_keys.ESTOP_ACTIVE, False):
            self.set_status(mode="ESTOP", message="Emergency stop is active", progress=0.0)
        return py_trees.common.Status.SUCCESS


class CheckArmNotInFault(BlackboardBehavior):
    """Placeholder hook for a real arm fault state."""

    def update(self) -> py_trees.common.Status:
        # Real hardware adapters should write an arm fault key here. Mocks are
        # considered healthy so the safety gate can pass.
        return py_trees.common.Status.SUCCESS


class ReportEmergency(BlackboardBehavior):
    """Publish the emergency/cancel result into the blackboard."""

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        command_type = command.command_type if command is not None else "ESTOP"
        self.publish_zero_twist()
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.bb_set(bb_keys.ARM_BUSY, False)

        if command_type == "CANCEL":
            self.bb_set(bb_keys.CURRENT_COMMAND, None)
            self.bb_set(bb_keys.CURRENT_MODE, "IDLE")
            self.set_status(
                mode="IDLE",
                message="Current task cancelled",
                progress=0.0,
                error_code="",
                current_task="",
            )
            return py_trees.common.Status.SUCCESS

        self.bb_set(bb_keys.ESTOP_ACTIVE, True)
        self.bb_set(bb_keys.CURRENT_COMMAND, None)
        self.bb_set(bb_keys.CURRENT_MODE, "ESTOP")
        self.set_status(
            mode="ESTOP",
            message="Emergency stop active; send RESUME to continue",
            progress=0.0,
            error_code="",
            current_task="",
        )
        return py_trees.common.Status.SUCCESS
