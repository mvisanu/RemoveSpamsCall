"""PII validation and normalisation utilities."""

from __future__ import annotations

import re
from typing import Optional

import phonenumbers


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def normalize_phone(raw: str, default_region: str = "US") -> Optional[str]:
    """Return the E.164 representation of *raw*, or ``None`` if unparseable."""
    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None


def parse_comma_list(value: str) -> list[str]:
    """Split a comma-separated string and strip whitespace."""
    return [item.strip() for item in value.split(",") if item.strip()]


def pii_env_to_dict(raw_env: str) -> dict[str, str]:
    """Parse key=value lines from a PII env file into a dictionary."""
    result: dict[str, str] = {}
    for line in raw_env.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"')
    return result
