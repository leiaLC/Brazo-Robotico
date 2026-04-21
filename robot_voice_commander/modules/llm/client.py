"""
Ollama LLM client.
Handles communication with the local Ollama instance and basic retry logic.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from .prompts import build_system_prompt

logger = logging.getLogger(__name__)


class LLMClient:
    """Wraps the Ollama Python client with retry and structured output helpers."""

    def __init__(self, config: dict, robot_config: dict) -> None:
        self._cfg = config
        self._robot_cfg = robot_config
        self._model: str = config["model"]
        self._temperature: float = config["temperature"]
        self._max_tokens: int = config["max_tokens"]
        self._timeout: int = config["timeout"]
        self._base_url: str = config["base_url"]

        import ollama  # lazy import
        self._client = ollama.Client(host=self._base_url)
        self._verify_connection()

    def _verify_connection(self) -> None:
        try:
            models = self._client.list()
            available = [m.model for m in models.models]
            # match "llama3.2" against "llama3.2:latest" etc.
            if not any(self._model in m for m in available):
                logger.warning(
                    "Model '%s' not found locally. Available: %s. "
                    "Run: ollama pull %s",
                    self._model,
                    available,
                    self._model,
                )
            else:
                logger.info("Ollama ready — model '%s' available", self._model)
        except Exception as exc:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Make sure Ollama is running: `ollama serve`"
            ) from exc

    def generate(
        self, user_message: str, scene_context: str = "", retries: int = 2
    ) -> Optional[str]:
        """
        Sends a user message to the LLM and returns the raw text response.
        Retries on transient failures.
        """
        system_prompt = build_system_prompt(self._robot_cfg, scene_context)

        for attempt in range(retries + 1):
            try:
                t0 = time.monotonic()
                response = self._client.chat(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    options={
                        "temperature": self._temperature,
                        "num_predict": self._max_tokens,
                    },
                )
                elapsed = time.monotonic() - t0
                raw = response.message.content.strip()
                logger.info("LLM responded in %.2f s", elapsed)
                logger.debug("LLM raw output: %s", raw)
                return raw

            except Exception as exc:
                logger.warning(
                    "LLM request failed (attempt %d/%d): %s",
                    attempt + 1,
                    retries + 1,
                    exc,
                )
                if attempt < retries:
                    time.sleep(1.0 * (attempt + 1))

        return None
