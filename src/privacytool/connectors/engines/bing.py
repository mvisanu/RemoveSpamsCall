"""Bing search connector using public web search."""

from __future__ import annotations

import hashlib
from datetime import datetime

import requests

from privacytool.connectors.base import BaseConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord

log = get_logger(__name__)

_BING_SEARCH_URL = "https://www.bing.com/search"
_BING_REMOVAL_URL = "https://www.bing.com/webmaster/tools/contentremoval"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class BingConnector(BaseConnector):
    name = "bing"
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
                        notes="Found via Bing search (url_hash stored)",
                    )
                )
        return records

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would open Bing content removal: {_BING_REMOVAL_URL}",
                dry_run=True,
            )
        return ActionResult(
            success=True,
            message=f"Open {_BING_REMOVAL_URL} in Bing Webmaster Tools to request content removal.",
        )

    def _search(self, query: str, dry_run: bool) -> list[str]:
        if dry_run:
            log.info("[DRY-RUN] Would search Bing for term")
            return []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; privacytool/0.1; +local)"}
            resp = requests.get(
                _BING_SEARCH_URL,
                params={"q": query},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            # Minimal extraction — a real implementation would parse the HTML
            import re
            urls = re.findall(r'href="(https?://[^"]+)"', resp.text)
            # Filter to likely result URLs (exclude bing itself)
            return [u for u in urls if "bing.com" not in u][:10]
        except Exception as exc:
            log.warning("Bing search failed: %s", exc)
            return []
