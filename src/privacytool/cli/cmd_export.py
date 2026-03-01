"""privacytool export — export all records to CSV, JSON, or HTML."""

from __future__ import annotations

import csv
import json
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from privacytool.core import config as cfg, db

console = Console()

_STATUS_COLORS = {
    "discovered": "#f59e0b",
    "pending":    "#3b82f6",
    "submitted":  "#06b6d4",
    "confirmed":  "#22c55e",
    "resolved":   "#16a34a",
    "failed":     "#ef4444",
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>privacytool — Removal Tracker</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
    h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; color: #f8fafc; }}
    .subtitle {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 1.5rem; }}
    .summary {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
    .chip {{ background: #1e293b; border: 1px solid #334155; border-radius: 9999px;
             padding: 0.25rem 0.75rem; font-size: 0.8rem; }}
    .chip span {{ font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    thead {{ background: #1e293b; }}
    th {{ padding: 0.6rem 0.75rem; text-align: left; font-weight: 600;
          color: #94a3b8; text-transform: uppercase; font-size: 0.7rem;
          letter-spacing: 0.05em; border-bottom: 1px solid #334155; }}
    td {{ padding: 0.55rem 0.75rem; border-bottom: 1px solid #1e293b; vertical-align: middle; }}
    tr:hover td {{ background: #1e293b; }}
    .badge {{ display: inline-block; padding: 0.15rem 0.55rem; border-radius: 9999px;
              font-size: 0.7rem; font-weight: 600; color: #fff; }}
    .type-engine  {{ color: #818cf8; }}
    .type-broker  {{ color: #fb923c; }}
    .type-letter  {{ color: #34d399; }}
    .ts {{ color: #64748b; font-size: 0.75rem; }}
    .num {{ text-align: right; color: #94a3b8; }}
    @media (max-width: 700px) {{ body {{ padding: 1rem; }} }}
  </style>
</head>
<body>
  <h1>Privacy Removal Tracker</h1>
  <p class="subtitle">Generated {generated} &mdash; {total} record(s) &mdash; PII excluded</p>
  <div class="summary">{summary_chips}</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Type</th>
        <th>Site</th>
        <th>Action</th>
        <th>Status</th>
        <th>Discovered</th>
        <th>Follow-up due</th>
        <th>Attempts</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""


def _status_badge(status: str) -> str:
    color = _STATUS_COLORS.get(status, "#64748b")
    return f'<span class="badge" style="background:{color}">{status}</span>'


def _type_span(target_type: str) -> str:
    return f'<span class="type-{target_type}">{target_type}</span>'


def _build_html(rows: list[dict]) -> str:
    from datetime import datetime

    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    chips = " ".join(
        f'<span class="chip"><span>{count}</span> {status}</span>'
        for status, count in sorted(by_status.items())
    )

    tr_parts = []
    for r in rows:
        tr_parts.append(
            f"<tr>"
            f"<td class='num'>{r['id'] or '—'}</td>"
            f"<td>{_type_span(r['target_type'])}</td>"
            f"<td>{r['site']}</td>"
            f"<td>{r.get('action_type') or '—'}</td>"
            f"<td>{_status_badge(r['status'])}</td>"
            f"<td class='ts'>{(r['discovered_on'] or '')[:10]}</td>"
            f"<td class='ts'>{(r['follow_up_due'] or '')[:10]}</td>"
            f"<td class='num'>{r['follow_up_count']}</td>"
            f"</tr>"
        )

    return _HTML_TEMPLATE.format(
        generated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        total=len(rows),
        summary_chips=chips,
        rows="\n      ".join(tr_parts),
    )


def export_cmd(
    fmt: Annotated[str, typer.Option("--format", "-f", help="csv | json | html")] = "csv",
    output: Annotated[str, typer.Option("--output", "-o", help="Output file base name")] = "export",
    open_browser: Annotated[bool, typer.Option("--open", help="Open in browser after export")] = False,
) -> None:
    """Export all tracked records to CSV, JSON, or HTML.  PII is never included."""
    db.init_db(cfg.db_path())
    records = db.get_all_records(cfg.db_path())

    if not records:
        console.print("[dim]No records to export.[/dim]")
        return

    rows = []
    for rec in records:
        d = asdict(rec)
        d.pop("url", None)    # exclude url hashes
        d.pop("notes", None)  # notes may contain partial PII context
        rows.append(d)

    if fmt == "csv":
        out_path = Path(f"{output}.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    elif fmt == "json":
        out_path = Path(f"{output}.json")
        out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    elif fmt == "html":
        out_path = Path(f"{output}.html")
        out_path.write_text(_build_html(rows), encoding="utf-8")
        if open_browser:
            webbrowser.open(out_path.resolve().as_uri())

    else:
        console.print(f"[red]Unknown format '{fmt}'. Use csv, json, or html.[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Exported {len(rows)} records to {out_path}[/green]")
