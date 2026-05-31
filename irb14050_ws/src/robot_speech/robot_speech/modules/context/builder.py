"""Context builder module.

Merges transcription text into a unified prompt context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Carries all information through a single pipeline cycle."""

    raw_audio_duration: float = 0.0
    transcription: str = ""
    transcription_language: str = ""
    transcription_confidence: float = 0.0
    scene_context_text: str = ""
    llm_raw_response: str = ""
    parsed_command: object = None
    parse_error: Optional[str] = None
    cycle_id: int = 0

    @property
    def success(self) -> bool:
        """Returns True if the cycle produced a valid parsed command."""
        return self.parsed_command is not None and self.parse_error is None


class ContextBuilder:
    """Builds the scene context string injected into the LLM system prompt."""

    def build(self, transcription: str) -> str:
        """Returns a context string based on the transcription only."""
        context = "No visual context available. Interpret command from voice only."
        logger.debug("Scene context: %s", context)
        return context
