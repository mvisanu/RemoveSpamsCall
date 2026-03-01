"""Structured logging with automatic PII redaction.

Usage:
    from privacytool.core.logger import get_logger
    log = get_logger(__name__)
    log.info("Scanning site %s", site_name)

PII is redacted from all log messages before they are written.
"""

from __future__ import annotations

import logging
import re
import sys


# Patterns to redact from log output
_REDACT_PATTERNS: list[re.Pattern[str]] = [
    # Email addresses
    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    # E.164 and common US phone formats
    re.compile(r"\+?\d[\d\s\-().]{7,}\d"),
]

_REPLACEMENT = "[REDACTED]"


class _PiiRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.msg = _redact(str(record.msg))
        record.args = tuple(_redact(str(a)) for a in record.args) if record.args else ()
        return True


def _redact(text: str) -> str:
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(_REPLACEMENT, text)
    return text


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    handler.addFilter(_PiiRedactingFilter())
    return handler


_root_configured = False


def configure_root_logger(level: str = "INFO") -> None:
    global _root_configured
    if _root_configured:
        return
    root = logging.getLogger("privacytool")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(_build_handler())
    root.propagate = False
    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    configure_root_logger()
    return logging.getLogger(f"privacytool.{name}" if not name.startswith("privacytool") else name)
