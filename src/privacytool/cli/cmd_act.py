"""privacytool act — execute removal actions."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from privacytool.core import config as cfg, db
from privacytool.core.runner import run_act

console = Console()


def act_cmd(
    target: Optional[str] = typer.Option(None, "--target", help="engine | broker | all"),
    mode: str = typer.Option("assisted", "--mode", "-m", help="assisted | auto"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without submitting"),
    pii_profile: str = typer.Option("default", "--pii-profile", "-p"),
) -> None:
    """Execute removal or opt-out actions for pending records."""
    if dry_run:
        console.print("[yellow][DRY-RUN] No submissions will be made.[/yellow]")

    # Auto mode needs the profile to fill forms
    profile = None
    if mode == "auto":
        passphrase = typer.prompt("Enter master passphrase (needed for auto form-fill)", hide_input=True)
        try:
            profile = cfg.load_profile(pii_profile, passphrase)
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[red]Error loading profile: {exc}[/red]")
            raise typer.Exit(1)

    db.init_db(cfg.db_path())
    records = db.get_records(cfg.db_path(), status="pending", target_type=target)

    if not records:
        console.print("[dim]No pending records found for the selected target.[/dim]")
        return

    console.print(f"[cyan]{len(records)} pending record(s) to act on.[/cyan]")

    # Build connector map keyed by site name
    from privacytool.connectors.engines.google import GoogleConnector
    from privacytool.connectors.engines.bing import BingConnector
    from privacytool.connectors.engines.duckduckgo import DuckDuckGoConnector
    from privacytool.connectors.engines.yandex import YandexConnector
    from privacytool.connectors.engines.yahoo import YahooConnector
    from privacytool.connectors.brokers.loader import load_brokers

    engine_connectors = [
        GoogleConnector(), BingConnector(), DuckDuckGoConnector(),
        YandexConnector(), YahooConnector(),
    ]
    broker_connectors = load_brokers(
        mode_override=mode,  # type: ignore[arg-type]
        profile=profile,
    )

    connectors_map = {c.name: c for c in engine_connectors + broker_connectors}

    try:
        results = run_act(connectors_map, records, cfg.db_path(), dry_run)
    finally:
        if mode == "auto":
            from privacytool.connectors.brokers.webdriver_session import quit_driver
            quit_driver()

    successes = sum(1 for r in results if r.success)
    failures = sum(1 for r in results if not r.success)
    console.print(
        f"\n[green]Actions complete:[/green] {successes} succeeded, [red]{failures} failed[/red]"
    )
