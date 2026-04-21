"""Pipeline orchestrator.

Wires all modules together into a single processing cycle:
  audio -> STT -> context build -> LLM -> action parse
"""

from __future__ import annotations

import logging
import time

from modules.audio import AudioCapture, Transcriber
from modules.llm import LLMClient
from modules.parser import ActionParser, ParseError
from modules.context import ContextBuilder, PipelineContext

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
    ) -> None:
        self._audio = audio_capture
        self._transcriber = transcriber
        self._llm = llm_client
        self._parser = action_parser
        self._context_builder = context_builder
        self._cycle_count = 0

    def run_cycle(self) -> PipelineContext:
        """Executes one full pipeline cycle and returns a PipelineContext."""
        self._cycle_count += 1
        ctx = PipelineContext(cycle_id=self._cycle_count)
        t_start = time.monotonic()

        # 1. Audio capture
        logger.info("[%d] Waiting for voice command...", ctx.cycle_id)
        audio = self._audio.record_until_silence()

        if audio is None:
            logger.warning("[%d] No audio recorded", ctx.cycle_id)
            return ctx

        ctx.raw_audio_duration = len(audio) / 16000

        # 2. Speech-to-text
        transcript = self._transcriber.transcribe(audio)

        if transcript is None or not transcript.text:
            logger.warning("[%d] Transcription returned empty", ctx.cycle_id)
            return ctx

        ctx.transcription = transcript.text
        ctx.transcription_language = transcript.language
        ctx.transcription_confidence = transcript.language_probability

        logger.info("[%d] Transcription: '%s'", ctx.cycle_id, ctx.transcription)

        # 3. Build scene context
        scene_context = self._context_builder.build(transcription=ctx.transcription)
        ctx.scene_context_text = scene_context

        # 4. LLM inference
        logger.info("[%d] Sending to LLM...", ctx.cycle_id)
        raw_response = self._llm.generate(
            user_message=ctx.transcription,
            scene_context=scene_context,
        )

        if not raw_response:
            ctx.parse_error = "LLM returned no response"
            logger.error("[%d] %s", ctx.cycle_id, ctx.parse_error)
            return ctx

        ctx.llm_raw_response = raw_response

        # 5. Action parsing and validation
        command, error = self._parser.parse_safe(raw_response)
        ctx.parsed_command = command
        ctx.parse_error = error

        elapsed = time.monotonic() - t_start
        if ctx.success:
            logger.info(
                "[%d] Cycle complete in %.2f s — %d action(s) parsed",
                ctx.cycle_id,
                elapsed,
                len(command.actions),
            )
        else:
            logger.error("[%d] Cycle failed in %.2f s — %s", ctx.cycle_id, elapsed, error)

        return ctx

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
