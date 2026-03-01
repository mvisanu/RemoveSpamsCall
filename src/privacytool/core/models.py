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

    # --- Auto-mode fields (only used when auto_supported: true) ---
    # URL template to search for the user's listing.
    # Supports {first_name}, {last_name}, {city}, {state} interpolation.
    search_url_template: str = ""
    # CSS selector for result items on the search results page.
    result_selector: str = ""
    # CSS selector for the opt-out form container.
    form_selector: str = ""
    # Mapping of field purpose -> comma-separated CSS selector fallback chain.
    # Supported keys: first_name, last_name, email, city, state, address, phone, dob
    form_fields: dict = field(default_factory=dict)
    # CSS selector for the form's submit button.
    submit_selector: str = ""
    # CSS selector that appears on the page after a confirmed removal.
    confirmation_selector: str = ""
    # Strategy to verify success: "page_text" | "url_change" | "element"
    confirmation_strategy: str = "page_text"
    # Substring to look for in page source when confirmation_strategy="page_text".
    confirmation_text: str = ""
    # Per-step Selenium timeout in seconds.
    auto_timeout: int = 15
