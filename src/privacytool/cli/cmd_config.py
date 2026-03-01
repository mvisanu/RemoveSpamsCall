"""privacytool config — set config values and switch profiles."""

from __future__ import annotations

import typer
from rich.console import Console

from privacytool.core import config as cfg

config_app = typer.Typer(help="Manage configuration and PII profiles.")
console = Console()


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key to set"),
    value: str = typer.Argument(..., help="Value to assign"),
) -> None:
    """Set a configuration value in the .env file."""
    env_path = cfg.Path(".env") if hasattr(cfg, "Path") else __import__("pathlib").Path(".env")
    import pathlib
    env_path = pathlib.Path(".env")
    lines: list[str] = []
    found = False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"[green]Set {key} in .env[/green]")


@config_app.command("use-profile")
def config_use_profile(
    name: str = typer.Argument(..., help="Profile name to activate"),
) -> None:
    """Switch the active PII profile."""
    profiles = cfg.list_profiles()
    if name not in profiles:
        console.print(f"[red]Profile '{name}' not found. Available: {profiles}[/red]")
        raise typer.Exit(1)
    # Write active profile selection to a small config file
    import pathlib
    selection_path = cfg.app_dir() / "active_profile"
    selection_path.write_text(name, encoding="utf-8")
    console.print(f"[green]Active profile set to '{name}'[/green]")


@config_app.command("list-profiles")
def config_list_profiles() -> None:
    """List all available PII profiles."""
    profiles = cfg.list_profiles()
    if not profiles:
        console.print("[dim]No profiles found. Run 'privacytool init' first.[/dim]")
        return
    for p in profiles:
        console.print(f"  • {p}")
