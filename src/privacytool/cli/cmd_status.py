"""privacytool status — view the full tracking dashboard."""

from __future__ import annotations

from typing import Optional

import typer

from privacytool.core import config as cfg, db
from privacytool.dashboard.views import console, print_records


def status_cmd(
    status_filter: Optional[str] = typer.Option(None, "--status", "-s"),
    target: Optional[str] = typer.Option(None, "--target", "-t"),
) -> None:
    """Display all tracked records in a Rich table."""
    db.init_db(cfg.db_path())
    records = db.get_records(cfg.db_path(), status=status_filter, target_type=target)
    print_records(records, title="Privacy Removal Tracker")
