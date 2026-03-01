"""Base class for data broker connectors."""

from __future__ import annotations

from datetime import datetime

from privacytool.connectors.base import BaseConnector
from privacytool.core.models import BrokerEntry, PiiProfile, TrackedRecord


class BaseBrokerConnector(BaseConnector):
    """Broker connectors are instantiated from a BrokerEntry YAML config."""

    def __init__(self, entry: BrokerEntry) -> None:
        self.entry = entry
        self.name = entry.id

    def discover(self, profile: PiiProfile, dry_run: bool = False) -> list[TrackedRecord]:
        """All brokers produce a single 'pending' record — user must verify manually."""
        return [
            TrackedRecord(
                target_type="broker",
                site=self.entry.id,
                url=self.entry.opt_out_url,
                action_type="optout",
                discovered_on=datetime.utcnow().isoformat(timespec="seconds"),
                notes=f"Broker: {self.entry.name} | Category: {self.entry.category}",
            )
        ]
