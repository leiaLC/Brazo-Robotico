"""
Cliente llama.cpp — reemplaza Ollama para inferencia local más rápida.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .prompts import build_system_prompt

logger = logging.getLogger(__name__)


class LlamaCppClient:
    """Wraps llama-cpp-python para inferencia local rápida en CPU."""

    def __init__(self, config: dict, robot_config: dict) -> None:
        self._cfg = config
        self._robot_cfg = robot_config
        self._model_path: str = config["model_path"]
        self._temperature: float = config.get("temperature", 0.1)
        self._max_tokens: int = config.get("max_tokens", 512)
        self._n_ctx: int = config.get("n_ctx", 2048)
        self._n_threads: int = config.get("n_threads", 4)

        logger.info("Cargando modelo llama.cpp: %s", self._model_path)

        self._n_gpu_layers: int = config.get("n_gpu_layers", 0)

        from llama_cpp import Llama

        self._llm = Llama(
            model_path=self._model_path,
            n_ctx=self._n_ctx,
            n_threads=self._n_threads,
            n_gpu_layers=self._n_gpu_layers,
            verbose=False,
        )

        if self._n_gpu_layers != 0:
            logger.info("llama.cpp usando GPU (%d capas)", self._n_gpu_layers)
        else:
            logger.info("llama.cpp usando CPU")


        logger.info("Modelo llama.cpp listo.")

    def generate(
        self, user_message: str, scene_context: str = "", retries: int = 2
    ) -> Optional[str]:
        """Genera una respuesta dado un mensaje de usuario."""

        system_prompt = build_system_prompt(self._robot_cfg, scene_context)

        for attempt in range(retries + 1):
            try:
                t0 = time.monotonic()

                response = self._llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )

                elapsed = time.monotonic() - t0
                raw = response["choices"][0]["message"]["content"].strip()

                logger.info("llama.cpp respondio en %.2f s", elapsed)
                logger.debug("llama.cpp output: %s", raw)
                return raw

            except Exception as exc:
                logger.warning(
                    "llama.cpp fallo (intento %d/%d): %s",
                    attempt + 1, retries + 1, exc,
                )
                if attempt < retries:
                    time.sleep(1.0)

        return None
