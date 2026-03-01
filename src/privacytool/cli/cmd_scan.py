"""privacytool scan — discover PII exposure across engines and brokers."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from privacytool.core import config as cfg, db
from privacytool.core.runner import run_discover
from privacytool.dashboard.views import make_progress, print_scan_summary

console = Console()


def scan_cmd(
    pii_profile: str = typer.Option("default", "--pii-profile", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without saving"),
    engines_only: bool = typer.Option(False, "--engines-only"),
    brokers_only: bool = typer.Option(False, "--brokers-only"),
) -> None:
    """Scan search engines and data brokers for PII exposure."""
    passphrase = typer.prompt("Enter master passphrase", hide_input=True)

    try:
        profile = cfg.load_profile(pii_profile, passphrase)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)

    db.init_db(cfg.db_path())

    # Build connector list
    connectors = []
    if not brokers_only:
        from privacytool.connectors.engines.google import GoogleConnector
        from privacytool.connectors.engines.bing import BingConnector
        from privacytool.connectors.engines.duckduckgo import DuckDuckGoConnector
        from privacytool.connectors.engines.yandex import YandexConnector
        from privacytool.connectors.engines.yahoo import YahooConnector
        connectors.extend([
            GoogleConnector(),
            BingConnector(),
            DuckDuckGoConnector(),
            YandexConnector(),
            YahooConnector(),
        ])

    if not engines_only:
        from privacytool.connectors.brokers.loader import load_brokers
        connectors.extend(load_brokers())

    if dry_run:
        console.print("[yellow][DRY-RUN] No data will be saved to the database.[/yellow]")

    with make_progress() as progress:
        task = progress.add_task("Scanning...", total=len(connectors))
        all_records = []
        for connector in connectors:
            progress.update(task, description=f"Scanning [cyan]{connector.name}[/cyan]...")
            try:
                records = connector.discover(profile, dry_run)
                for rec in records:
                    if not dry_run:
                        rec.id = db.insert_record(cfg.db_path(), rec)
                all_records.extend(records)
            except Exception as exc:
                console.print(f"[red]Error scanning {connector.name}: {exc}[/red]")
            progress.advance(task)

    print_scan_summary(all_records)
