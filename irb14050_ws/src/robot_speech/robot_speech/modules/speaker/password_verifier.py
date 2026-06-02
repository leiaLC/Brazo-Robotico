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
        self._accepted_passwords: set[str] = {
            self._normalize(value)
            for value in config.get("accepted_variants", [])
            if str(value).strip()
        }
        if self._password:
            self._accepted_passwords.add(self._normalize(self._password))

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
        accepted_passwords = self._accepted_passwords or {self._normalize(self._password)}

        if any(password and password in normalized for password in accepted_passwords):
            logger.info("Contraseña verificada correctamente")
            return True, "Acceso concedido"

        logger.warning(
            "Contraseña incorrecta; recibido: '%s' (normalizado: '%s')",
            transcription,
            normalized,
        )
        return False, "Acceso denegado: contraseña incorrecta"

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^\w\s]", " ", text)
        return re.sub(r"\s+", " ", text)
