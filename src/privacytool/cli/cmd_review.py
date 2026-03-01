"""privacytool review — interactive review of scan findings."""

from __future__ import annotations

import typer
from rich.console import Console

from privacytool.core import config as cfg, db
from privacytool.dashboard.views import console as dash_console, records_table

console = Console()


def review_cmd() -> None:
    """Interactively review discovered records and mark them pending or skip."""
    db.init_db(cfg.db_path())
    records = db.get_records(cfg.db_path(), status="discovered")

    if not records:
        console.print("[green]No new discovered records to review.[/green]")
        return

    console.print(records_table(records, title="Discovered Records — Review"))
    console.print("\nFor each record, enter [cyan]a[/cyan]=accept (set pending) or [cyan]s[/cyan]=skip.\n")

    for rec in records:
        choice = console.input(
            f"Record [bold]#{rec.id}[/bold] [{rec.site}] — (a)ccept / (s)kip / (q)uit: "
        ).strip().lower()
        if choice == "q":
            break
        if choice == "a" and rec.id is not None:
            db.update_status(cfg.db_path(), rec.id, "pending")
            console.print(f"  [green]#{rec.id} marked pending[/green]")
        else:
            console.print(f"  [dim]#{rec.id} skipped[/dim]")

    console.print("\n[cyan]Review complete. Run 'privacytool act' to submit removal requests.[/cyan]")
