"""Validation and arbitration helpers for RobotCommand messages."""

from robot_task_msgs.msg import RobotCommand


KNOWN_COMMAND_TYPES = {
    "PICK_OBJECT",
    "MOVE_JOINT",
    "WEB_TELEOP",
    "RUN_SEQUENCE",
    "XBOX_TELEOP",
    "CANCEL",
    "ESTOP",
    "PAUSE",
    "RESUME",
}

EMERGENCY_TYPES = {"ESTOP", "CANCEL"}

# Lower number means higher priority.
COMMAND_PRIORITY_RANK = {
    "ESTOP": 1,
    "CANCEL": 1,
    "XBOX_TELEOP": 2,
    "WEB_TELEOP": 3,
    "MOVE_JOINT": 4,
    "RUN_SEQUENCE": 5,
    "PICK_OBJECT": 6,
}

COMMAND_MODE = {
    "PICK_OBJECT": "VOICE_PICK",
    "MOVE_JOINT": "VOICE_JOINT",
    "WEB_TELEOP": "WEB_TELEOP",
    "RUN_SEQUENCE": "WEB_SEQUENCE",
    "XBOX_TELEOP": "XBOX_TELEOP",
    "ESTOP": "ESTOP",
    "CANCEL": "IDLE",
    "PAUSE": "IDLE",
    "RESUME": "IDLE",
}


def command_rank(command_type: str) -> int:
    """Return arbitration rank for a command type."""

    return COMMAND_PRIORITY_RANK.get(command_type, 99)


def validate_command(command: RobotCommand) -> tuple[bool, str]:
    """Perform schema-level command validation before it enters the tree."""

    if command.command_type not in KNOWN_COMMAND_TYPES:
        return False, f"Unknown command_type '{command.command_type}'"

    if command.command_type == "MOVE_JOINT":
        if command.joint_values:
            return True, "ok"
        if command.joint_id <= 0:
            return False, "MOVE_JOINT requires joint_id > 0"
        if command.relative and abs(command.joint_delta_deg) < 1e-9:
            return False, "Relative MOVE_JOINT requires joint_delta_deg"
        if not command.relative and abs(command.joint_target_deg) < 1e-9:
            # Zero is valid for explicit target commands; allow it when the
            # command came from text such as "a cero".
            return True, "ok"

    if command.command_type == "PICK_OBJECT":
        if not command.object_class:
            return False, "PICK_OBJECT requires object_class"

    if command.command_type == "RUN_SEQUENCE" and not command.sequence_id:
        return False, "RUN_SEQUENCE requires sequence_id"

    return True, "ok"


def is_emergency(command: RobotCommand | None) -> bool:
    return command is not None and command.command_type in EMERGENCY_TYPES


def should_accept_command(
    incoming: RobotCommand,
    current: RobotCommand | None,
    arm_busy: bool,
) -> tuple[bool, str]:
    """Apply the central command admission policy."""

    if incoming.command_type == "RESUME":
        return True, "resume"

    if is_emergency(incoming):
        return True, "emergency"

    if arm_busy:
        return False, "robot arm is busy; only ESTOP or CANCEL can preempt"

    if current is None or not current.command_type:
        return True, "idle"

    if incoming.command_type == current.command_type and incoming.command_type in {
        "WEB_TELEOP",
        "XBOX_TELEOP",
    }:
        return True, "teleop refresh"

    incoming_rank = command_rank(incoming.command_type)
    current_rank = command_rank(current.command_type)
    if incoming_rank <= current_rank:
        return True, "higher or equal priority"

    return False, (
        f"lower priority than current command "
        f"({incoming.command_type}:{incoming_rank} > {current.command_type}:{current_rank})"
    )


def mode_for_command(command: RobotCommand | None) -> str:
    if command is None:
        return "IDLE"
    return COMMAND_MODE.get(command.command_type, "IDLE")


def describe_command(command: RobotCommand | None) -> str:
    """Create a concise human-readable command label for status messages."""

    if command is None or not command.command_type:
        return ""

    if command.command_type == "PICK_OBJECT":
        color = f" {command.object_color}" if command.object_color else ""
        return f"pick {command.object_class}{color}".strip()

    if command.command_type == "MOVE_JOINT":
        if command.relative:
            return f"joint {command.joint_id} delta {command.joint_delta_deg:.2f} deg"
        return f"joint {command.joint_id} target {command.joint_target_deg:.2f} deg"

    if command.command_type == "RUN_SEQUENCE":
        return f"sequence {command.sequence_id}"

    return command.command_type.lower()
