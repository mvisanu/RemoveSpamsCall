"""privacytool init — first-time setup wizard."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from privacytool.core import config as cfg
from privacytool.core import db
from privacytool.core.models import PiiProfile
from privacytool.core.pii import normalize_phone, parse_comma_list, validate_email

console = Console()


def init_cmd() -> None:
    """Run the first-time setup wizard to create a PII profile and initialize the database."""
    console.print(
        Panel(
            "[bold cyan]Welcome to privacytool[/bold cyan]\n\n"
            "This wizard will create an encrypted PII profile and set up the local database.\n"
            "Your data never leaves this machine.",
            title="Setup Wizard",
            border_style="cyan",
        )
    )

    # Passphrase
    passphrase = typer.prompt(
        "Choose a master passphrase (used to encrypt your PII profile)",
        hide_input=True,
    )
    confirm = typer.prompt("Confirm passphrase", hide_input=True)
    if passphrase != confirm:
        typer.echo("Passphrases do not match. Aborting.")
        raise typer.Exit(1)

    # PII fields
    full_name = typer.prompt("Full name (as it appears online)")

    emails_raw = typer.prompt("Email addresses (comma-separated)", default="")
    emails: list[str] = []
    for e in parse_comma_list(emails_raw):
        if validate_email(e):
            emails.append(e)
        else:
            console.print(f"  [yellow]Skipping invalid email: {e}[/yellow]")

    phones_raw = typer.prompt("Phone numbers (comma-separated)", default="")
    phones: list[str] = []
    for p in parse_comma_list(phones_raw):
        normalized = normalize_phone(p)
        if normalized:
            phones.append(normalized)
        else:
            console.print(f"  [yellow]Cannot normalize phone: {p} — skipping[/yellow]")

    addresses = parse_comma_list(typer.prompt("Addresses (comma-separated)", default=""))
    usernames = parse_comma_list(typer.prompt("Usernames / handles (comma-separated)", default=""))
    dob = typer.prompt("Date of birth (YYYY-MM-DD, optional)", default="")

    profile = PiiProfile(
        name="default",
        full_name=full_name,
        emails=emails,
        phones=phones,
        addresses=addresses,
        usernames=usernames,
        dob=dob,
    )

    cfg.save_profile(profile, passphrase)
    console.print("[green]Profile 'default' encrypted and saved.[/green]")

    db.init_db(cfg.db_path())
    console.print(f"[green]Database initialized at {cfg.db_path()}[/green]")

    # Write skeleton .env if not present
    env_path = Path(".env")
    if not env_path.exists():
        example = Path(".env.example")
        if example.exists():
            env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            console.print(
                "[green].env created from .env.example — fill in your API keys.[/green]"
            )

    console.print(
        Panel(
            "[bold green]Setup complete![/bold green]\n\n"
            "Next steps:\n"
            "  1. Edit [cyan].env[/cyan] to add your API keys (SERP_API_KEY, etc.)\n"
            "  2. Run [cyan]privacytool scan --pii-profile default[/cyan] to discover PII\n"
            "  3. Run [cyan]privacytool review[/cyan] to approve findings\n"
            "  4. Run [cyan]privacytool act[/cyan] to submit removal requests",
            border_style="green",
        )
    )
