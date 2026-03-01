"""Google search connector using SerpAPI and/or Google Custom Search API."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime

import requests

from privacytool.connectors.base import BaseConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord

log = get_logger(__name__)

_SERP_API_URL = "https://serpapi.com/search"
_GCSE_API_URL = "https://www.googleapis.com/customsearch/v1"

# Google removal request URLs
_CACHE_REMOVAL_URL = "https://search.google.com/search-console/remove-outdated-content"
_PERSONAL_INFO_REMOVAL = "https://support.google.com/websearch/troubleshooter/9685456"


def _hash_url(url: str) -> str:
    """Return a SHA-256 hex digest of the URL for safe storage."""
    return hashlib.sha256(url.encode()).hexdigest()


class GoogleConnector(BaseConnector):
    """Discover PII via SerpAPI/Google CSE and generate removal request packets."""

    name = "google"
    mode = "assisted"

    def __init__(self) -> None:
        self._serp_key = os.environ.get("SERP_API_KEY", "")
        self._cse_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
        self._cse_id = os.environ.get("GOOGLE_CSE_ID", "")

    def discover(self, profile: PiiProfile, dry_run: bool = False) -> list[TrackedRecord]:
        records: list[TrackedRecord] = []
        for term in profile.search_terms():
            results = self._search(term, dry_run)
            for url in results:
                records.append(
                    TrackedRecord(
                        target_type="engine",
                        site=self.name,
                        url=_hash_url(url),
                        action_type="deindex",
                        discovered_on=datetime.utcnow().isoformat(timespec="seconds"),
                        notes=f"Found via Google search (url_hash stored)",
                    )
                )
        return records

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would open Google cache removal: {_CACHE_REMOVAL_URL}",
                dry_run=True,
            )
        # Google cache removal must be done via web UI — guide the user.
        return ActionResult(
            success=True,
            message=(
                f"Open {_CACHE_REMOVAL_URL} to request cache removal. "
                f"For personal info removal see {_PERSONAL_INFO_REMOVAL}"
            ),
        )

    def _search(self, query: str, dry_run: bool) -> list[str]:
        if dry_run:
            log.info("[DRY-RUN] Would search Google for term")
            return []
        if self._serp_key:
            return self._serp_search(query)
        if self._cse_key and self._cse_id:
            return self._cse_search(query)
        log.warning("No Google API key configured — skipping Google search")
        return []

    def _serp_search(self, query: str) -> list[str]:
        try:
            resp = requests.get(
                _SERP_API_URL,
                params={"q": query, "api_key": self._serp_key, "num": 10},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return [r.get("link", "") for r in data.get("organic_results", []) if r.get("link")]
        except Exception as exc:
            log.warning("SerpAPI request failed: %s", exc)
            return []

    def _cse_search(self, query: str) -> list[str]:
        try:
            resp = requests.get(
                _GCSE_API_URL,
                params={"q": query, "key": self._cse_key, "cx": self._cse_id, "num": 10},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item.get("link", "") for item in data.get("items", []) if item.get("link")]
        except Exception as exc:
            log.warning("Google CSE request failed: %s", exc)
            return []
