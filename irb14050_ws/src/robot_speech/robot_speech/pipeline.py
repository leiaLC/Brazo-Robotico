"""Pipeline orchestrator.

Wires all modules together into a single processing cycle:
  audio -> STT -> context build -> LLM -> action parse
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from .modules.audio import AudioCapture, Transcriber
from .modules.llm import LLMClient
from .modules.parser import ActionParser, ParseError
from .modules.context import ContextBuilder, PipelineContext

logger = logging.getLogger(__name__)


class VoiceCommandPipeline:
    """Orchestrates a full voice-command cycle."""

    def __init__(
        self,
        audio_capture: AudioCapture,
        transcriber: Transcriber,
        llm_client: LLMClient,
        action_parser: ActionParser,
        context_builder: ContextBuilder,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._audio = audio_capture
        self._transcriber = transcriber
        self._llm = llm_client
        self._parser = action_parser
        self._context_builder = context_builder
        self._status_callback = status_callback
        self._cycle_count = 0

    def run_cycle(self) -> PipelineContext:
        """Executes one full pipeline cycle and returns a PipelineContext."""
        self._cycle_count += 1
        ctx = PipelineContext(cycle_id=self._cycle_count)
        t_start = time.monotonic()

        self.listen_and_transcribe(ctx)
        if not ctx.transcription:
            return ctx

        # 3. Build scene context
        t_context = time.monotonic()
        scene_context = self._context_builder.build(transcription=ctx.transcription)
        ctx.scene_context_text = scene_context
        ctx.timings_sec["context"] = time.monotonic() - t_context

        # 4. LLM inference
        self._publish_status("interpreting")
        logger.info("[%d] Sending to LLM...", ctx.cycle_id)
        t_llm = time.monotonic()
        raw_response = self._llm.generate(
            user_message=ctx.transcription,
            scene_context=scene_context,
        )
        ctx.timings_sec["llm"] = time.monotonic() - t_llm

        if not raw_response:
            ctx.parse_error = "LLM returned no response"
            logger.error("[%d] %s", ctx.cycle_id, ctx.parse_error)
            self._log_timing_summary(ctx, t_start)
            return ctx

        ctx.llm_raw_response = raw_response

        # 5. Action parsing and validation
        t_parse = time.monotonic()
        command, error = self._parser.parse_safe(raw_response)
        ctx.timings_sec["parse"] = time.monotonic() - t_parse
        ctx.parsed_command = command
        ctx.parse_error = error

        elapsed = time.monotonic() - t_start
        ctx.timings_sec["total"] = elapsed
        if ctx.success:
            logger.info(
                "[%d] Cycle complete in %.2f s — %d action(s) parsed",
                ctx.cycle_id,
                elapsed,
                len(command.actions),
            )
        else:
            logger.error("[%d] Cycle failed in %.2f s — %s", ctx.cycle_id, elapsed, error)

        self._log_timing_summary(ctx, t_start)
        return ctx

    def listen_and_transcribe(self, ctx: PipelineContext | None = None) -> PipelineContext:
        """Captures one utterance and stores only the transcription in context."""
        if ctx is None:
            self._cycle_count += 1
            ctx = PipelineContext(cycle_id=self._cycle_count)

        logger.info("[%d] Waiting for voice input...", ctx.cycle_id)
        t_audio = time.monotonic()
        audio = self._audio.record_until_silence()
        ctx.timings_sec["audio"] = time.monotonic() - t_audio

        if audio is None:
            logger.warning("[%d] No audio recorded", ctx.cycle_id)
            return ctx

        ctx.raw_audio_duration = len(audio) / 16000
        self._publish_status("transcribing")
        t_stt = time.monotonic()
        transcript = self._transcriber.transcribe(audio)
        ctx.timings_sec["stt"] = time.monotonic() - t_stt

        if transcript is None or not transcript.text:
            logger.warning("[%d] Transcription returned empty", ctx.cycle_id)
            return ctx

        ctx.transcription = transcript.text
        ctx.transcription_language = transcript.language
        ctx.transcription_confidence = transcript.language_probability

        logger.info("[%d] Transcription: '%s'", ctx.cycle_id, ctx.transcription)
        return ctx

    def _publish_status(self, status: str) -> None:
        if self._status_callback is not None:
            self._status_callback(status)

    @staticmethod
    def _log_timing_summary(ctx: PipelineContext, t_start: float) -> None:
        ctx.timings_sec.setdefault("total", time.monotonic() - t_start)
        logger.info(
            "[%d] Timing: audio=%.2fs stt=%.2fs context=%.2fs llm=%.2fs parse=%.2fs total=%.2fs",
            ctx.cycle_id,
            ctx.timings_sec.get("audio", 0.0),
            ctx.timings_sec.get("stt", 0.0),
            ctx.timings_sec.get("context", 0.0),
            ctx.timings_sec.get("llm", 0.0),
            ctx.timings_sec.get("parse", 0.0),
            ctx.timings_sec.get("total", 0.0),
        )

    def run_forever(self, on_command=None) -> None:
        """Runs the pipeline in a loop until Ctrl+C."""
        logger.info("Pipeline running. Press Ctrl+C to stop.")
        try:
            while True:
                ctx = self.run_cycle()
                if on_command:
                    on_command(ctx)
        except KeyboardInterrupt:
            logger.info("Pipeline stopped by user")
