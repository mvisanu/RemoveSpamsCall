"""Rich-powered dashboard views: tables, progress bars, and follow-up alerts."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import box

from privacytool.core.models import TrackedRecord

console = Console()

_STATUS_COLORS: dict[str, str] = {
    "discovered": "yellow",
    "pending": "blue",
    "submitted": "cyan",
    "confirmed": "green",
    "resolved": "bright_green",
    "failed": "red",
}


def records_table(records: list[TrackedRecord], title: str = "Tracking Dashboard") -> Table:
    table = Table(title=title, box=box.ROUNDED, show_lines=False, expand=True)
    table.add_column("ID", style="dim", width=5, justify="right")
    table.add_column("Type", width=8)
    table.add_column("Site", width=20)
    table.add_column("Action", width=10)
    table.add_column("Status", width=12)
    table.add_column("Discovered", width=12)
    table.add_column("Follow-up due", width=14)
    table.add_column("Attempts", width=8, justify="right")

    for rec in records:
        color = _STATUS_COLORS.get(rec.status, "white")
        table.add_row(
            str(rec.id or "—"),
            rec.target_type,
            rec.site,
            rec.action_type or "—",
            f"[{color}]{rec.status}[/{color}]",
            rec.discovered_on[:10] if rec.discovered_on else "—",
            rec.follow_up_due[:10] if rec.follow_up_due else "—",
            str(rec.follow_up_count),
        )
    return table


def print_records(records: list[TrackedRecord], title: str = "Tracking Dashboard") -> None:
    if not records:
        console.print("[dim]No records found.[/dim]")
        return
    console.print(records_table(records, title))


def print_followups(records: list[TrackedRecord]) -> None:
    if not records:
        console.print("[green]No follow-ups due.[/green]")
        return
    console.print(
        Panel(
            f"[yellow]{len(records)} record(s) are due for follow-up.[/yellow]",
            title="Follow-up Reminders",
            border_style="yellow",
        )
    )
    console.print(records_table(records, title="Follow-ups Due"))


def print_scan_summary(records: list[TrackedRecord]) -> None:
    by_status: dict[str, int] = {}
    for rec in records:
        by_status[rec.status] = by_status.get(rec.status, 0) + 1

    lines = [f"[bold]Scan complete — {len(records)} record(s) found[/bold]\n"]
    for status, count in sorted(by_status.items()):
        color = _STATUS_COLORS.get(status, "white")
        lines.append(f"  [{color}]{status}[/{color}]: {count}")

    console.print(Panel("\n".join(lines), title="Scan Summary", border_style="cyan"))


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
