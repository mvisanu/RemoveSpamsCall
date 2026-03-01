"""privacytool export — export all records to CSV or JSON."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from privacytool.core import config as cfg, db

console = Console()


def export_cmd(
    fmt: Annotated[str, typer.Option("--format", "-f", help="csv | json")] = "csv",
    output: Annotated[str, typer.Option("--output", "-o", help="Output file base name")] = "export",
) -> None:
    """Export all tracked records to CSV or JSON.  PII is never included in exports."""
    db.init_db(cfg.db_path())
    records = db.get_all_records(cfg.db_path())

    if not records:
        console.print("[dim]No records to export.[/dim]")
        return

    # Sanitize: drop the url field (may be a hash, but we omit it for safety)
    rows = []
    for rec in records:
        d = asdict(rec)
        d.pop("url", None)   # exclude url hashes from exports
        d.pop("notes", None) # notes may contain partial PII context
        rows.append(d)

    if fmt == "csv":
        out_path = Path(f"{output}.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        console.print(f"[green]Exported {len(rows)} records to {out_path}[/green]")

    elif fmt == "json":
        out_path = Path(f"{output}.json")
        out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        console.print(f"[green]Exported {len(rows)} records to {out_path}[/green]")

    else:
        console.print(f"[red]Unknown fmt '{fmt}'. Use csv or json.[/red]")
        raise typer.Exit(1)
