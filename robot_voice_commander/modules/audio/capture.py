"""
Audio capture module.
Uses PyAudio for recording and Silero VAD for voice activity detection.
"""

from __future__ import annotations

import time
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class AudioCapture:
    """
    Records audio from a microphone.
    Uses Silero VAD to detect speech boundaries automatically.
    """

    # Silero VAD requires exactly 512 samples per chunk at 16 kHz
    _VAD_CHUNK = 512

    def __init__(self, config: dict) -> None:
        self._cfg = config
        self._sample_rate: int = config["sample_rate"]
        self._channels: int = config["channels"]
        self._chunk: int = config["chunk_size"]
        self._silence_duration: float = config["silence_duration"]
        self._max_duration: float = config["max_recording_duration"]
        self._device_index: Optional[int] = config.get("device_index")

        self._pa = None
        self._stream: Optional[object] = None
        import pyaudio as _pyaudio
        self._pa = _pyaudio.PyAudio()
        self._vad_model, self._vad_utils = self._load_vad()

        logger.info("AudioCapture initialised (rate=%d Hz)", self._sample_rate)

    # ── VAD ────────────────────────────────────────────────────────────────

    def _load_vad(self):
        import torch
        logger.info("Loading Silero VAD model…")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        return model, utils

    def _is_speech(self, chunk: np.ndarray) -> bool:
        """
        Runs Silero VAD on a 512-sample window.
        chunk must be exactly _VAD_CHUNK samples long.
        np.frombuffer returns a read-only view — .copy() makes it writable for torch.
        """
        import torch
        tensor = torch.from_numpy(chunk.copy()).float()
        confidence: float = self._vad_model(tensor, self._sample_rate).item()
        return confidence > 0.5

    def _vad_on_buffer(self, buf: np.ndarray) -> bool:
        """
        Splits buf into _VAD_CHUNK windows, returns True if ANY window
        contains speech. Ignores leftover samples at the end.
        """
        n = len(buf) // self._VAD_CHUNK
        for i in range(n):
            window = buf[i * self._VAD_CHUNK : (i + 1) * self._VAD_CHUNK]
            if self._is_speech(window):
                return True
        return False

    # ── Stream management ──────────────────────────────────────────────────

    def _open_stream(self):
        import pyaudio as _pyaudio
        if self._pa is None:
            self._pa = _pyaudio.PyAudio()
        return self._pa.open(
            format=_pyaudio.paFloat32,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=self._device_index,
            frames_per_buffer=self._chunk,
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def record_until_silence(self) -> Optional[np.ndarray]:
        """
        Blocks until the user starts speaking, records until silence,
        and returns the audio as a float32 numpy array (16 kHz mono).
        Returns None if nothing was recorded within max_duration.
        """
        stream = self._open_stream()
        logger.info("Listening for speech…")

        frames: list[np.ndarray] = []
        silence_start: Optional[float] = None
        recording = False
        start_time = time.monotonic()

        try:
            while True:
                elapsed = time.monotonic() - start_time
                if elapsed > self._max_duration:
                    logger.warning("Max recording duration reached (%.1f s)", elapsed)
                    break

                raw = stream.read(self._chunk, exception_on_overflow=False)
                # frombuffer gives a read-only view; .copy() makes it writable for torch
                chunk = np.frombuffer(raw, dtype=np.float32).copy()

                # VAD operates on fixed 512-sample windows regardless of chunk_size
                speech_detected = self._vad_on_buffer(chunk)

                if speech_detected:
                    if not recording:
                        logger.debug("Speech detected — recording started")
                        recording = True
                    frames.append(chunk)
                    silence_start = None
                elif recording:
                    frames.append(chunk)  # keep trailing silence for context
                    if silence_start is None:
                        silence_start = time.monotonic()
                    elif time.monotonic() - silence_start >= self._silence_duration:
                        logger.debug(
                            "Silence for %.1f s — recording stopped", self._silence_duration
                        )
                        break

        finally:
            stream.stop_stream()
            stream.close()

        if not frames:
            logger.warning("No speech detected in recording window")
            return None

        audio = np.concatenate(frames)
        logger.info(
            "Recorded %.2f s of audio (%d samples)", len(audio) / self._sample_rate, len(audio)
        )
        return audio

    def list_devices(self) -> list[dict]:
        """Returns available audio input devices."""
        import pyaudio as _pyaudio
        if self._pa is None:
            self._pa = _pyaudio.PyAudio()
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({"index": i, "name": info["name"]})
        return devices

    def close(self) -> None:
        if self._pa:
            self._pa.terminate()
        logger.info("AudioCapture closed")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
