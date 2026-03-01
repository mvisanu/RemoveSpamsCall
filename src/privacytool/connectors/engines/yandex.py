"""Yandex search connector."""

from __future__ import annotations

import hashlib
from datetime import datetime

import requests

from privacytool.connectors.base import BaseConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, PiiProfile, TrackedRecord

log = get_logger(__name__)

_YANDEX_URL = "https://yandex.com/search/"
_YANDEX_REMOVAL_URL = "https://yandex.com/support/search/how-to-remove.html"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


class YandexConnector(BaseConnector):
    name = "yandex"
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
                        notes="Found via Yandex search (url_hash stored)",
                    )
                )
        return records

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would open Yandex removal: {_YANDEX_REMOVAL_URL}",
                dry_run=True,
            )
        return ActionResult(
            success=True,
            message=f"Visit {_YANDEX_REMOVAL_URL} to request content removal from Yandex.",
        )

    def _search(self, query: str, dry_run: bool) -> list[str]:
        if dry_run:
            log.info("[DRY-RUN] Would search Yandex for term")
            return []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; privacytool/0.1; +local)"}
            resp = requests.get(
                _YANDEX_URL,
                params={"text": query, "lr": "213"},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            import re
            urls = re.findall(r'href="(https?://[^"]+)"', resp.text)
            return [u for u in urls if "yandex.com" not in u and "yandex.ru" not in u][:10]
        except Exception as exc:
            log.warning("Yandex search failed: %s", exc)
            return []
