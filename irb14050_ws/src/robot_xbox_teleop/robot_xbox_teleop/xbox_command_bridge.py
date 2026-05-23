#!/usr/bin/env python3
"""Compatibility entry point for the generic gamepad command bridge."""

from robot_xbox_teleop.gamepad_command_bridge import GamepadCommandBridge, main


class XboxCommandBridge(GamepadCommandBridge):
    """Backward-compatible class name used by older launch files."""


__all__ = ["XboxCommandBridge", "main"]
