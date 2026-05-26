"""
Password-based speaker verification module.

Verifies access by comparing a transcribed voice password
against the configured password in settings.yaml.
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


class PasswordVerifier:
    """Verifies access using a voice password compared as plain text."""

    def __init__(self, config: dict) -> None:
        self._enabled: bool = config.get("enabled", True)
        self._password: str = config.get("password", "")

        logger.info(
            "PasswordVerifier initialized (enabled=%s)",
            self._enabled,
        )

    def is_enabled(self) -> bool:
        """Returns True if password verification is enabled."""
        return self._enabled

    def verify(self, transcription: str) -> tuple[bool, str]:
        """
        Verifies if the transcription contains the correct password.

        Args:
            transcription: Text transcribed from the user's audio.

        Returns:
            authorized: True if the password was found in the transcription.
            message: Human-readable result message.
        """
        if not self._enabled:
            return True, "Verification disabled"

        if not transcription:
            return False, "No transcription received"

        normalized = self._normalize(transcription)
        password = self._normalize(self._password)

        if password in normalized:
            logger.info("Contraseña verificada correctamente")
            return True, "Acceso concedido"

        logger.warning("Contraseña incorrecta; recibido: '%s'", transcription)
        return False, "Acceso denegado: contraseña incorrecta"

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return re.sub(r"\s+", " ", text)
