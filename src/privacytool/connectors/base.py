"""Abstract base class for all connectors (search engines and data brokers)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord


class BaseConnector(ABC):
    """All connectors must implement discover() and act()."""

    name: str = ""
    mode: Literal["assisted", "auto"] = "assisted"

    @abstractmethod
    def discover(self, profile: PiiProfile, dry_run: bool = False) -> list[TrackedRecord]:
        """Search for PII exposure and return a list of records found."""
        ...

    @abstractmethod
    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        """Execute a removal/opt-out action for the given record."""
        ...
