#!/usr/bin/env python3
"""Spanish text command parser for the robot task interface."""

from __future__ import annotations

import re
import unicodedata

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from robot_task_msgs.msg import RobotCommand
from robot_task_msgs.srv import ParseVoiceCommand


SPANISH_NUMBERS = {
    "cero": 0.0,
    "un": 1.0,
    "uno": 1.0,
    "una": 1.0,
    "dos": 2.0,
    "tres": 3.0,
    "cuatro": 4.0,
    "cinco": 5.0,
    "seis": 6.0,
    "siete": 7.0,
    "ocho": 8.0,
    "nueve": 9.0,
    "diez": 10.0,
    "quince": 15.0,
    "veinte": 20.0,
    "treinta": 30.0,
    "cuarenta": 40.0,
    "cincuenta": 50.0,
    "noventa": 90.0,
}

OBJECTS = {
    "cubo": "cube",
    "cube": "cube",
    "botella": "bottle",
    "bottle": "bottle",
}

COLORS = {
    "azul": "blue",
    "blue": "blue",
    "rojo": "red",
    "roja": "red",
    "red": "red",
    "verde": "green",
    "green": "green",
    "amarillo": "yellow",
    "amarilla": "yellow",
    "yellow": "yellow",
}


def normalize(text: str) -> str:
    """Lowercase and remove accents so regexes stay simple."""

    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def parse_number(text: str) -> float | None:
    token = text.strip().lower()
    sign = 1.0
    if token.startswith("menos "):
        sign = -1.0
        token = token.replace("menos ", "", 1).strip()

    try:
        return sign * float(token)
    except ValueError:
        pass

    if token in SPANISH_NUMBERS:
        return sign * SPANISH_NUMBERS[token]
    return None


def contains_phrase(text: str, phrases: list[str]) -> bool:
    """Return true when any whole phrase appears in normalized text."""

    return any(re.search(rf"\b{re.escape(phrase)}\b", text) for phrase in phrases)


class VoiceCommandParser(Node):
    """Parse text commands and publish RobotCommand messages."""

    def __init__(self) -> None:
        super().__init__("voice_command_parser")
        self.command_pub = self.create_publisher(RobotCommand, "/robot_task/command", 10)
        self.text_sub = self.create_subscription(String, "/voice/text", self._text_callback, 10)
        self.parse_srv = self.create_service(
            ParseVoiceCommand,
            "/voice/parse_command",
            self._parse_service_callback,
        )
        self.get_logger().info("voice_command_parser ready")

    def _text_callback(self, msg: String) -> None:
        success, message, command = self.parse_text(msg.data)
        if success:
            self.command_pub.publish(command)
            self.get_logger().info(f"Voice command parsed: {command.command_type} ({message})")
        else:
            self.get_logger().warn(f"Could not parse voice text '{msg.data}': {message}")

    def _parse_service_callback(self, request, response):
        success, message, command = self.parse_text(request.text)
        response.success = success
        response.message = message
        response.command = command
        return response

    def _new_command(self) -> RobotCommand:
        command = RobotCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = "voice_command_parser"
        command.source = "voice"
        return command

    def parse_text(self, text: str) -> tuple[bool, str, RobotCommand]:
        command = self._new_command()
        normalized = normalize(text)
        if not normalized:
            return False, "empty text", command

        if contains_phrase(
            normalized,
            ["emergencia", "paro de emergencia", "parada de emergencia", "estop", "e stop", "para todo"],
        ):
            command.command_type = "ESTOP"
            command.priority = 100.0
            return True, "emergency stop", command

        if contains_phrase(normalized, ["reanudar", "reanuda", "continua", "continuar", "resume"]):
            command.command_type = "RESUME"
            command.priority = 100.0
            return True, "resume", command

        if contains_phrase(normalized, ["detente", "alto", "para", "parar", "cancelar", "cancela", "cancelo"]):
            command.command_type = "CANCEL"
            command.priority = 100.0
            return True, "cancel", command

        pick = self._parse_pick(normalized, command)
        if pick[0]:
            return pick

        joint = self._parse_joint(normalized, command)
        if joint[0]:
            return joint

        return False, "unsupported voice command", command

    def _parse_pick(self, normalized: str, command: RobotCommand) -> tuple[bool, str, RobotCommand]:
        if not any(verb in normalized for verb in ["agarra", "toma", "recoge"]):
            return False, "not a pick command", command

        object_class = ""
        for word, value in OBJECTS.items():
            if re.search(rf"\b{word}\b", normalized):
                object_class = value
                break

        if not object_class:
            return False, "pick command without known object", command

        object_color = ""
        for word, value in COLORS.items():
            if re.search(rf"\b{word}\b", normalized):
                object_color = value
                break

        command.command_type = "PICK_OBJECT"
        command.object_class = object_class
        command.object_color = object_color
        command.place_target = "box"
        command.priority = 94.0
        return True, f"pick {object_color} {object_class}".strip(), command

    def _parse_joint(self, normalized: str, command: RobotCommand) -> tuple[bool, str, RobotCommand]:
        if "joint" not in normalized and "articulacion" not in normalized:
            return False, "not a joint command", command

        joint_match = re.search(r"\b(?:joint|articulacion)\s+([a-z0-9.]+)\b", normalized)
        if not joint_match:
            return False, "joint id not found", command

        joint_value = parse_number(joint_match.group(1))
        if joint_value is None:
            return False, "joint id is not numeric", command
        joint_id = int(joint_value)

        tail = normalized[joint_match.end() :]
        absolute_match = re.search(r"\ba\s+((?:menos\s+)?[a-z0-9.]+)\s*(?:grados?)?", tail)
        if absolute_match:
            target = parse_number(absolute_match.group(1))
            if target is None:
                return False, "absolute target not understood", command
            command.command_type = "MOVE_JOINT"
            command.joint_id = joint_id
            command.joint_target_deg = float(target)
            command.relative = False
            command.priority = 96.0
            return True, f"move joint {joint_id} to {target:g} deg", command

        relative_match = re.search(r"((?:menos\s+)?[a-z0-9.]+)\s+grados?", tail)
        if not relative_match:
            return False, "joint angle not found", command

        delta = parse_number(relative_match.group(1))
        if delta is None:
            return False, "relative angle not understood", command

        command.command_type = "MOVE_JOINT"
        command.joint_id = joint_id
        command.joint_delta_deg = float(delta)
        command.relative = True
        command.priority = 96.0
        return True, f"move joint {joint_id} by {delta:g} deg", command


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiceCommandParser()
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
