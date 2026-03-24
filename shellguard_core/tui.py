"""Rich TUI for ShellGuard — command table + interactive Q&A."""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

try:
    import readline  # noqa: F401 — enables line editing in input()
except ImportError:
    pass

from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .analyzer import ensure_risk_labels
from .config import Config
from .history import read_history_merged
from .llm import answer_question

console = Console()

# Risk level display config: (icon, rich color)
RISK_STYLE: Dict[str, tuple] = {
    "LOW":  ("✔", "green"),
    "MED":  ("⚠", "yellow"),
    "HIGH": ("✖", "dark_orange"),
    "CRIT": ("☠", "red"),
}


def _risk_text(risk: Optional[str]) -> Text:
    if not risk:
        return Text("…", style="dim")
    icon, color = RISK_STYLE.get(risk.upper(), ("?", "white"))
    return Text(f"{icon} {risk}", style=color)


def _build_table(records: List[Dict[str, Any]]) -> Table:
    """Build the command history Rich Table."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Timestamp", width=19)
    table.add_column("Command", no_wrap=False, ratio=3)
    table.add_column("CWD", no_wrap=True, ratio=1)
    table.add_column("Exit", width=5, justify="center")
    table.add_column("Risk", width=10)

    for i, rec in enumerate(records, 1):
        ts = rec.get("ts", "")[:19].replace("T", " ")
        cmd = escape(rec.get("cmd", ""))
        cwd = escape(rec.get("cwd", ""))
        exit_code = str(rec.get("exit_code", ""))
        exit_style = "red" if exit_code not in ("0", "") else "green"
        risk = rec.get("risk")
        table.add_row(
            str(i),
            ts,
            cmd,
            cwd,
            Text(exit_code, style=exit_style),
            _risk_text(risk),
        )
    return table


def _build_history_context(records: List[Dict[str, Any]]) -> str:
    """Build a text summary of command history for LLM context."""
    lines = []
    for i, rec in enumerate(records, 1):
        ts = rec.get("ts", "")[:19].replace("T", " ")
        cmd = rec.get("cmd", "")
        risk = rec.get("risk", "?")
        label = rec.get("risk_label", "")
        exit_code = rec.get("exit_code", "")
        line = f"{i}. [{ts}] {cmd}  (exit={exit_code}, risk={risk}"
        if label:
            line += f", {label}"
        line += ")"
        lines.append(line)
    return "\n".join(lines)


def _analyze_with_progress(records: List[Dict[str, Any]], cfg: Config) -> List[Dict[str, Any]]:
    """Run risk analysis with a Rich spinner showing progress."""
    needs_analysis = [r for r in records if not r.get("risk")]
    if not needs_analysis:
        return records

    spinner_text = ["Analyzing commands..."]

    def on_progress(current: int, total: int, cmd: str) -> None:
        truncated = cmd[:40] + "…" if len(cmd) > 40 else cmd
        spinner_text[0] = f"Analyzing {current}/{total}: {truncated}"

    with Live(console=console, refresh_per_second=10) as live:
        def refresh() -> None:
            live.update(
                Panel(
                    Spinner("dots", text=spinner_text[0]),
                    title="[bold cyan]ShellGuard — Analyzing",
                    border_style="cyan",
                )
            )

        # Monkey-patch on_progress to refresh live display
        def on_progress_live(current: int, total: int, cmd: str) -> None:
            on_progress(current, total, cmd)
            refresh()

        refresh()
        records = ensure_risk_labels(records, cfg, on_progress=on_progress_live)

    return records


def run_tui(cfg: Config) -> None:
    """Launch the interactive TUI."""
    console.clear()
    console.print(
        Panel(
            "[bold cyan]ShellGuard[/bold cyan] — Terminal Security Monitor\n"
            "[dim]Loading command history...[/dim]",
            border_style="cyan",
        )
    )

    records = read_history_merged(cfg.max_history_display)

    if not records:
        console.print(
            Panel(
                "[yellow]No command history found.[/yellow]\n\n"
                "Make sure the shell hook is installed:\n"
                "  [bold]bash install.sh[/bold]",
                title="ShellGuard",
                border_style="yellow",
            )
        )
        return

    # Run analysis
    records = _analyze_with_progress(records, cfg)

    last_answer: Optional[str] = None

    while True:
        console.clear()

        # Build and print the command table
        table = _build_table(records)
        console.print(
            Panel(
                table,
                title=f"[bold cyan]ShellGuard · {len(records)} commands[/bold cyan]",
                border_style="cyan",
            )
        )

        # Show last answer if any
        if last_answer:
            console.print(
                Panel(
                    escape(last_answer),
                    title="[bold green]Answer[/bold green]",
                    border_style="green",
                )
            )

        # Check config
        if not cfg.api_key:
            console.print(
                "[dim]Note: No API key configured. Run [bold]bash install.sh[/bold] to configure.[/dim]"
            )

        # Interactive prompt
        console.print()
        console.print("[bold cyan]Ask[/bold cyan] [dim](type a question, 'r' to refresh, 'q' to quit)[/dim]")
        try:
            user_input = input("Ask > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() in ("r", "refresh"):
            # Reload and re-analyze
            records = read_history_merged(cfg.max_history_display)
            records = _analyze_with_progress(records, cfg)
            last_answer = None
            continue

        if not cfg.api_key:
            last_answer = "[错误] 未配置 API Key，请运行 bash install.sh 进行配置。"
            continue

        # Answer the question
        console.print("[dim]Thinking...[/dim]")
        history_ctx = _build_history_context(records)
        last_answer = answer_question(cfg.base_url, cfg.api_key, cfg.model, user_input, history_ctx)


def run_ask(cfg: Config, question: str) -> None:
    """Non-interactive single Q&A."""
    if not cfg.api_key:
        console.print("[red]Error:[/red] No API key configured. Run [bold]bash install.sh[/bold].")
        sys.exit(1)

    records = read_history_merged(cfg.max_history_display)
    if not records:
        console.print("[yellow]No command history found.[/yellow]")
        sys.exit(0)

    with console.status("[cyan]Analyzing and answering...[/cyan]"):
        records = ensure_risk_labels(records, cfg)
        history_ctx = _build_history_context(records)
        answer = answer_question(cfg.base_url, cfg.api_key, cfg.model, question, history_ctx)

    console.print(Panel(escape(answer), title="[bold green]Answer[/bold green]", border_style="green"))
