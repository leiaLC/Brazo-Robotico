"""
Speech-to-text module using faster-whisper.
Wraps the model with caching and language configuration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration: float
    words: list[dict]

    def __str__(self) -> str:
        return self.text


class Transcriber:
    """Wraps faster-whisper for efficient STT with GPU support."""

    def __init__(self, config: dict) -> None:
        self._cfg = config
        model_size = config["model_size"]
        device = config["device"]
        compute_type = config["compute_type"]

        logger.info(
            "Loading Whisper model '%s' on %s (%s)…", model_size, device, compute_type
        )
        from faster_whisper import WhisperModel  # lazy — not needed in parser-only mode
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        self._language: Optional[str] = config.get("language")
        self._beam_size: int = config.get("beam_size", 5)
        logger.info("Whisper model ready")

    def transcribe(self, audio: np.ndarray) -> Optional[TranscriptionResult]:
        """
        Transcribes a float32 numpy array (16 kHz mono) to text.
        Returns None if no speech is detected.
        """
        if audio is None or len(audio) == 0:
            return None

        logger.debug("Transcribing %.2f s of audio…", len(audio) / 16000)

        segments, info = self._model.transcribe(
            audio,
            beam_size=self._beam_size,
            language=self._language,
            word_timestamps=True,
            vad_filter=True,           # built-in VAD for extra filtering
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=100,
            ),
        )

        words = []
        text_parts = []

        for segment in segments:
            text_parts.append(segment.text.strip())
            if segment.words:
                for word in segment.words:
                    words.append({
                        "word": word.word,
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "probability": round(word.probability, 3),
                    })

        full_text = " ".join(text_parts).strip()

        if not full_text:
            logger.warning("Transcription returned empty text")
            return None

        result = TranscriptionResult(
            text=full_text,
            language=info.language,
            language_probability=round(info.language_probability, 3),
            duration=round(info.duration, 3),
            words=words,
        )

        logger.info(
            "Transcribed [%s %.0f%%]: '%s'",
            result.language,
            result.language_probability * 100,
            result.text,
        )
        return result
