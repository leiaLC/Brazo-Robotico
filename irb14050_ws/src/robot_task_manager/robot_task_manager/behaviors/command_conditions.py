"""Command condition and housekeeping behaviours."""

import py_trees

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior
from robot_task_manager.utils.command_utils import describe_command, mode_for_command


class HasCommandType(BlackboardBehavior):
    """Return SUCCESS when the current command has the requested type."""

    def __init__(self, name: str, node, command_type: str):
        super().__init__(name, node)
        self.command_type = command_type

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if command is not None and command.command_type == self.command_type:
            self.set_status(
                mode=mode_for_command(command),
                message=f"Handling {command.command_type}",
                current_task=describe_command(command),
            )
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class HasEStopOrCancel(BlackboardBehavior):
    """Detect fresh emergency stop or cancel commands."""

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if command is not None and command.command_type in {"ESTOP", "CANCEL"}:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class ClearCurrentCommand(BlackboardBehavior):
    """Clear the current command after a branch completes."""

    def update(self) -> py_trees.common.Status:
        self.bb_set(bb_keys.CURRENT_COMMAND, None)
        self.bb_set(bb_keys.ARM_BUSY, False)
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.bb_set(bb_keys.TASK_PROGRESS, 1.0)
        self.set_status(message="Task complete", error_code="", current_task="")
        return py_trees.common.Status.SUCCESS


class PublishIdleStatus(BlackboardBehavior):
    """Maintain safe idle state and publish a zero servo twist."""

    def update(self) -> py_trees.common.Status:
        if self.bb_get(bb_keys.ESTOP_ACTIVE, False):
            self.bb_set(bb_keys.CURRENT_MODE, "ESTOP")
            self.bb_set(bb_keys.TELEOP_ACTIVE, False)
            self.bb_set(bb_keys.TASK_PROGRESS, 0.0)
            self.bb_set(bb_keys.STATUS_TEXT, "Emergency stop active; send RESUME to continue")
            return py_trees.common.Status.SUCCESS

        # Secuencia pausada: mantenemos el estado "Paused" de forma estable (sin
        # caer a "Idle") y conservamos el progreso para que el front muestre el
        # boton Resume y la barra no se reinicie a 0.
        paused_id = self.bb_get(bb_keys.PAUSED_SEQUENCE_ID, None)
        if paused_id:
            paused_step = int(self.bb_get(bb_keys.PAUSED_SEQUENCE_STEP, 0) or 0)
            self.bb_set(bb_keys.CURRENT_MODE, "WEB_SEQUENCE")
            self.bb_set(bb_keys.TELEOP_ACTIVE, False)
            self.bb_set(bb_keys.CURRENT_TASK, f"sequence {paused_id}")
            self.bb_set(bb_keys.STATUS_TEXT, f"Paused (sequence '{paused_id}', step {paused_step + 1})")
            return py_trees.common.Status.SUCCESS

        if not self.bb_get(bb_keys.ESTOP_ACTIVE, False):
            self.bb_set(bb_keys.CURRENT_MODE, "IDLE")
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.bb_set(bb_keys.TASK_PROGRESS, 0.0)
        if not self.bb_get(bb_keys.ARM_BUSY, False):
            self.bb_set(bb_keys.STATUS_TEXT, "Idle")
        return py_trees.common.Status.SUCCESS
