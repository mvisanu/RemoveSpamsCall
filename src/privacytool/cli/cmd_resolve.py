"""privacytool resolve — mark a record as resolved."""

from __future__ import annotations

import typer
from rich.console import Console

from privacytool.core import config as cfg, db

console = Console()


def resolve_cmd(
    record_id: int = typer.Argument(..., help="ID of the record to resolve"),
    notes: str = typer.Option("", "--notes", "-n", help="Optional notes"),
) -> None:
    """Mark a tracked record as resolved."""
    db.init_db(cfg.db_path())
    db.update_status(cfg.db_path(), record_id, "resolved", notes=notes)
    console.print(f"[green]Record #{record_id} marked as resolved.[/green]")
