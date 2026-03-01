"""privacytool followups — list records due for follow-up."""

from __future__ import annotations

from privacytool.core import config as cfg, db
from privacytool.dashboard.views import print_followups


def followups_cmd() -> None:
    """List all records where the 30-day follow-up deadline has passed."""
    db.init_db(cfg.db_path())
    records = db.get_followups(cfg.db_path())
    print_followups(records)
