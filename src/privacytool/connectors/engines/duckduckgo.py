"""DuckDuckGo search connector."""

from __future__ import annotations

import hashlib
from datetime import datetime

import requests

from privacytool.connectors.base import BaseConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord

log = get_logger(__name__)

_DDG_URL = "https://html.duckduckgo.com/html/"
_DDG_REMOVAL_INFO = "https://duckduckgo.com/duckduckgo-help-pages/results/sources/"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class DuckDuckGoConnector(BaseConnector):
    name = "duckduckgo"
    mode = "assisted"

    def discover(self, profile: PiiProfile, dry_run: bool = False) -> list[TrackedRecord]:
        records: list[TrackedRecord] = []
        for term in profile.search_terms():
            urls = self._search(term, dry_run)
            for url in urls:
                records.append(
                    TrackedRecord(
                        target_type="engine",
                        site=self.name,
                        url=_hash_url(url),
                        action_type="deindex",
                        discovered_on=datetime.utcnow().isoformat(timespec="seconds"),
                        notes="Found via DuckDuckGo search (url_hash stored)",
                    )
                )
        return records

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        msg = (
            "DuckDuckGo sources from other search engines. "
            f"Request removal from the source site and see {_DDG_REMOVAL_INFO}"
        )
        if dry_run:
            return ActionResult(success=True, message=f"[DRY-RUN] {msg}", dry_run=True)
        return ActionResult(success=True, message=msg)

    def _search(self, query: str, dry_run: bool) -> list[str]:
        if dry_run:
            log.info("[DRY-RUN] Would search DuckDuckGo for term")
            return []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; privacytool/0.1; +local)"}
            resp = requests.post(
                _DDG_URL,
                data={"q": query, "kl": "us-en"},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            import re
            urls = re.findall(r'href="(https?://[^"&]+)"', resp.text)
            return [u for u in urls if "duckduckgo.com" not in u][:10]
        except Exception as exc:
            log.warning("DuckDuckGo search failed: %s", exc)
            return []
