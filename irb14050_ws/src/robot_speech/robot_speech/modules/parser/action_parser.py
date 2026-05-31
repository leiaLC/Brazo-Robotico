"""
Action parser module.
Extracts and validates structured robot commands from raw LLM output.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from .schema import RobotCommand

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when the LLM output cannot be parsed into a valid RobotCommand."""


class ActionParser:
    """
    Parses raw LLM text into validated RobotCommand objects.

    Handles:
    - Clean JSON responses
    - JSON embedded in markdown fences (```json ... ```)
    - Partial or malformed JSON with best-effort extraction
    """

    # Regex to find the first JSON object in a string
    _JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

    def parse(self, raw_text: str) -> RobotCommand:
        """
        Main entry point. Raises ParseError if parsing fails.
        """
        if not raw_text:
            raise ParseError("LLM returned empty response")

        json_str = self._extract_json(raw_text)
        data = self._parse_json(json_str)
        command = self._validate(data)
        self._validate_action_parameters(command)

        logger.info(
            "Parsed command: '%s' (confidence=%.2f, %d action(s))",
            command.intent,
            command.confidence,
            len(command.actions),
        )
        return command

    def parse_safe(self, raw_text: str) -> tuple[Optional[RobotCommand], Optional[str]]:
        """
        Safe variant — returns (command, None) on success or (None, error_message) on failure.
        Never raises.
        """
        try:
            return self.parse(raw_text), None
        except ParseError as exc:
            logger.error("Parse failed: %s", exc)
            return None, str(exc)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _extract_json(self, text: str) -> str:
        # 1. Try stripping markdown fences
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)

        # 2. Try matching a raw JSON object
        match = self._JSON_PATTERN.search(text)
        if match:
            return match.group(0)

        raise ParseError(f"No JSON object found in LLM output: {text[:200]!r}")

    def _parse_json(self, json_str: str) -> dict:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ParseError(f"JSON decode error: {exc} — input: {json_str[:200]!r}") from exc

    def _validate(self, data: dict) -> RobotCommand:
        try:
            return RobotCommand(**data)
        except ValidationError as exc:
            raise ParseError(f"Schema validation failed: {exc}") from exc

    def _validate_action_parameters(self, command: RobotCommand) -> None:
        """Validates each action's parameters against its specific schema."""
        for i, action in enumerate(command.actions):
            try:
                action.validate_parameters()
            except Exception as exc:
                raise ParseError(
                    f"Parameter validation failed for action {i + 1} "
                    f"({action.action.value}): {exc}"
                ) from exc
