"""Central job runner with rate limiting, retry logic, and dry-run support."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, TrackedRecord, PiiProfile

log = get_logger(__name__)

T = TypeVar("T")

_DEFAULT_RATE_DELAY = 2.0  # seconds between requests per connector
_MAX_ATTEMPTS = 3


def rate_limited(delay: float = _DEFAULT_RATE_DELAY) -> Callable:
    """Decorator that sleeps *delay* seconds after each call."""
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            time.sleep(delay)
            return result
        return wrapper
    return decorator


def with_retry(fn: Callable[..., T], *args, **kwargs) -> T:
    """Call *fn* with exponential backoff retry on transient errors."""
    @retry(
        stop=stop_after_attempt(_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((OSError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _inner():
        return fn(*args, **kwargs)
    return _inner()


def run_discover(
    connectors: list,
    profile: PiiProfile,
    db_path: str,
    dry_run: bool,
) -> list[TrackedRecord]:
    """Run discovery across all connectors, return all found records."""
    from privacytool.core import db

    all_records: list[TrackedRecord] = []
    for connector in connectors:
        log.info("Running discovery on %s", connector.name)
        try:
            records = with_retry(connector.discover, profile, dry_run)
            for rec in records:
                if not dry_run:
                    rec.id = db.insert_record(db_path, rec)
                all_records.append(rec)
            log.info("%s: found %d records", connector.name, len(records))
        except Exception as exc:
            log.warning("Connector %s discovery failed: %s", connector.name, exc)
    return all_records


def run_act(
    connectors_map: dict,
    records: list[TrackedRecord],
    db_path: str,
    dry_run: bool,
) -> list[ActionResult]:
    """Execute removal actions for each record via the matching connector."""
    from privacytool.core import db

    results: list[ActionResult] = []
    for record in records:
        connector = connectors_map.get(record.site)
        if not connector:
            log.warning("No connector found for site %s — skipping", record.site)
            continue
        log.info("Acting on record id=%s site=%s dry_run=%s", record.id, record.site, dry_run)
        try:
            result = with_retry(connector.act, record, dry_run)
            if not dry_run and record.id is not None:
                new_status = "submitted" if result.success else "failed"
                db.update_status(
                    db_path, record.id, new_status,
                    confirmation_id=result.confirmation_id,
                    notes=result.message,
                )
            results.append(result)
        except Exception as exc:
            log.warning("Action failed for record id=%s: %s", record.id, exc)
            results.append(ActionResult(success=False, message=str(exc), dry_run=dry_run))
    return results
