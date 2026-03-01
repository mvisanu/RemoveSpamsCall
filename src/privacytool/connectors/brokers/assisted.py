"""Assisted-mode broker connector — guides the user through manual opt-out steps."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from privacytool.connectors.brokers.base_broker import BaseBrokerConnector
from privacytool.core.models import ActionResult, TrackedRecord

console = Console()


class AssistedBrokerConnector(BaseBrokerConnector):
    """Prints step-by-step instructions for manual opt-out."""

    mode = "assisted"

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        steps = self.entry.steps or [
            f"Go to {self.entry.opt_out_url}",
            "Search for your name and location",
            "Follow the site's opt-out / removal process",
            "Confirm via email if required",
        ]

        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would display {len(steps)} opt-out steps for {self.entry.name}",
                dry_run=True,
            )

        lines = [f"[bold]{self.entry.name}[/bold]  —  {self.entry.opt_out_url}\n"]
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step}")

        console.print(
            Panel(
                "\n".join(lines),
                title="[cyan]Opt-Out Steps[/cyan]",
                border_style="cyan",
            )
        )
        confirmed = console.input("\n[yellow]Mark as submitted? (y/N):[/yellow] ")
        if confirmed.strip().lower() == "y":
            return ActionResult(
                success=True,
                message="User confirmed submission",
                confirmation_id="manual-confirmed",
            )
        return ActionResult(success=False, message="User did not confirm submission")
