"""Shared dataclasses used across the entire application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class PiiProfile:
    """Decrypted PII profile — lives in memory only, never persisted in plaintext."""

    name: str  # profile identifier, not the person's name
    full_name: str = ""
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)   # E.164 normalised
    addresses: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    dob: str = ""  # ISO-8601 date string

    def search_terms(self) -> list[str]:
        """Return all terms to search for (used by engine connectors)."""
        terms: list[str] = []
        if self.full_name:
            terms.append(self.full_name)
        terms.extend(self.emails)
        terms.extend(self.phones)
        terms.extend(self.usernames)
        return terms


RecordStatus = Literal[
    "discovered", "pending", "submitted", "confirmed", "resolved", "failed"
]

ActionType = Literal["deindex", "optout", "letter"]

TargetType = Literal["engine", "broker", "letter"]


@dataclass
class TrackedRecord:
    """A single PII exposure tracked in the database."""

    target_type: TargetType
    site: str
    url: str = ""
    discovered_on: str = field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )
    action_type: ActionType | None = None
    status: RecordStatus = "discovered"
    confirmation_id: str = ""
    last_attempt: str = ""
    follow_up_due: str = ""
    follow_up_count: int = 0
    notes: str = ""
    id: int | None = None  # set after DB insert


@dataclass
class ActionResult:
    """Result returned by a connector's act() method."""

    success: bool
    confirmation_id: str = ""
    message: str = ""
    dry_run: bool = False


@dataclass
class BrokerEntry:
    """Structured entry loaded from brokers.yaml."""

    id: str
    name: str
    url: str
    opt_out_url: str
    mode: Literal["assisted", "auto"]
    steps: list[str] = field(default_factory=list)
    auto_supported: bool = False
    jurisdiction: str = "US"
    category: str = "people-search"
    notes: str = ""
