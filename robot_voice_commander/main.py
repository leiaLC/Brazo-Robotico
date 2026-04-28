"""Entry point for the Robot Voice Commander system."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from modules.audio import AudioCapture, Transcriber
from modules.llm import LLMClient
from modules.parser import ActionParser
from modules.context import ContextBuilder, PipelineContext
from pipeline import VoiceCommandPipeline

console = Console()


def setup_logging(cfg: dict) -> None:
    """Configures logging with rich handler and optional file output."""
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO"))

    handlers: list[logging.Handler] = [
        RichHandler(console=console, show_path=False, markup=True)
    ]

    if log_cfg.get("log_to_file"):
        log_file = Path(log_cfg.get("log_file", "logs/robot_voice.log"))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )


def load_config(path: str = "config/settings.yaml") -> dict:
    """Loads YAML config from disk."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def print_banner() -> None:
    """Prints startup banner."""
    console.print(
        Panel.fit(
            "[bold cyan]Robot Voice Commander[/bold cyan]\n"
            "[dim]ROS2 Jazzy · Whisper STT · Ollama LLM[/dim]",
            border_style="cyan",
        )
    )


def print_cycle_result(ctx: PipelineContext) -> None:
    """Renders a summary after each pipeline cycle."""
    console.rule(f"[dim]Cycle #{ctx.cycle_id}[/dim]")

    if not ctx.transcription:
        console.print("[yellow]No transcription — skipping display[/yellow]")
        return

    console.print(f"[bold]Voice input:[/bold] [green italic]'{ctx.transcription}'[/green italic]")

    if ctx.parse_error:
        console.print(f"[red bold]Parse error:[/red bold] {ctx.parse_error}")
        return

    if ctx.parsed_command is None:
        return

    cmd = ctx.parsed_command
    conf_color = "green" if cmd.is_high_confidence else "yellow"
    console.print(
        f"[bold]Intent:[/bold] {cmd.intent}  "
        f"[{conf_color}]confidence={cmd.confidence:.2f}[/{conf_color}]"
    )

    if cmd.clarification_needed:
        console.print(
            f"[yellow bold]Clarification needed:[/yellow bold] {cmd.clarification_message}"
        )
        return

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
    table.add_column("#", style="dim", width=3)
    table.add_column("Action", style="bold")
    table.add_column("Parameters")

    for i, action in enumerate(cmd.actions, 1):
        params_str = ", ".join(f"{k}={v}" for k, v in action.parameters.items())
        table.add_row(str(i), action.action.value, params_str or "[dim]—[/dim]")

    console.print(table)
    console.print()


def build_pipeline(cfg: dict) -> VoiceCommandPipeline:
    """Instantiates and wires all pipeline modules."""
    console.print("[dim]Loading modules...[/dim]")

    audio_capture = AudioCapture(cfg["audio"])
    transcriber = Transcriber(cfg["whisper"])
    llm_client = LLMClient(cfg["ollama"], cfg["robot"])
    action_parser = ActionParser()
    context_builder = ContextBuilder()

    pipeline = VoiceCommandPipeline(
        audio_capture=audio_capture,
        transcriber=transcriber,
        llm_client=llm_client,
        action_parser=action_parser,
        context_builder=context_builder,
    )

    console.print("[green]All modules ready.[/green]")
    return pipeline


def main() -> None:
    """Main entry point."""
    cfg_path = os.environ.get("RVC_CONFIG", "config/settings.yaml")

    try:
        cfg = load_config(cfg_path)
    except FileNotFoundError:
        console.print(f"[red]Config file not found: {cfg_path}[/red]")
        sys.exit(1)

    setup_logging(cfg)
    print_banner()

    try:
        pipeline = build_pipeline(cfg)
    except ConnectionError as exc:
        console.print(f"[red bold]Startup error:[/red bold] {exc}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red bold]Fatal error during init:[/red bold] {exc}")
        raise

    pipeline.run_forever(on_command=print_cycle_result)


if __name__ == "__main__":
    main()
