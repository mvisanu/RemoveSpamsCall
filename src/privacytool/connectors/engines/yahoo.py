"""Yahoo search connector."""

from __future__ import annotations

import hashlib
from datetime import datetime

import requests

from privacytool.connectors.base import BaseConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord

log = get_logger(__name__)

_YAHOO_URL = "https://search.yahoo.com/search"
_YAHOO_REMOVAL_URL = "https://help.yahoo.com/kb/SLN38655.html"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class YahooConnector(BaseConnector):
    name = "yahoo"
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
                        notes="Found via Yahoo search (url_hash stored)",
                    )
                )
        return records

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would open Yahoo removal: {_YAHOO_REMOVAL_URL}",
                dry_run=True,
            )
        return ActionResult(
            success=True,
            message=f"Visit {_YAHOO_REMOVAL_URL} to request content removal from Yahoo Search.",
        )

    def _search(self, query: str, dry_run: bool) -> list[str]:
        if dry_run:
            log.info("[DRY-RUN] Would search Yahoo for term")
            return []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; privacytool/0.1; +local)"}
            resp = requests.get(
                _YAHOO_URL,
                params={"p": query},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            import re
            urls = re.findall(r'href="(https?://[^"]+)"', resp.text)
            return [u for u in urls if "yahoo.com" not in u][:10]
        except Exception as exc:
            log.warning("Yahoo search failed: %s", exc)
            return []
