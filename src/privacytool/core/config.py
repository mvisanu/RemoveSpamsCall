"""Application configuration — .env loading, profile management, paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from privacytool.core import crypto, pii as pii_utils
from privacytool.core.models import PiiProfile


_APP_DIR = Path.home() / ".privacytool"
_PROFILES_DIR = Path("profiles")  # relative to CWD (project root)


def app_dir() -> Path:
    """Return (and create) the application data directory."""
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    return _APP_DIR


def db_path() -> str:
    """Return the SQLite database path, respecting PRIVACYTOOL_DB_PATH env var."""
    return os.environ.get("PRIVACYTOOL_DB_PATH", str(app_dir() / "tracker.db"))


def load_env() -> None:
    """Load .env into os.environ (safe no-op if not found)."""
    load_dotenv(override=False)


def profile_path(profile_name: str) -> Path:
    return _PROFILES_DIR / f"{profile_name}.pii.enc"


def list_profiles() -> list[str]:
    if not _PROFILES_DIR.exists():
        return []
    return [p.stem.replace(".pii", "") for p in _PROFILES_DIR.glob("*.pii.enc")]


def save_profile(profile: PiiProfile, passphrase: str) -> None:
    """Serialize a PiiProfile to env-file format and encrypt it to disk."""
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f'FULL_NAME="{profile.full_name}"',
        f'EMAILS="{",".join(profile.emails)}"',
        f'PHONES="{",".join(profile.phones)}"',
        f'ADDRESSES="{",".join(profile.addresses)}"',
        f'USERNAMES="{",".join(profile.usernames)}"',
        f'DOB="{profile.dob}"',
    ]
    plaintext = "\n".join(lines)
    crypto.encrypt_file(str(profile_path(profile.name)), plaintext, passphrase)


def load_profile(profile_name: str, passphrase: str) -> PiiProfile:
    """Decrypt and deserialize a PiiProfile from disk."""
    path = profile_path(profile_name)
    if not path.exists():
        raise FileNotFoundError(f"Profile '{profile_name}' not found at {path}")
    plaintext = crypto.decrypt_file(str(path), passphrase)
    data = pii_utils.pii_env_to_dict(plaintext)

    emails_raw = pii_utils.parse_comma_list(data.get("EMAILS", ""))
    phones_raw = pii_utils.parse_comma_list(data.get("PHONES", ""))

    valid_emails = [e for e in emails_raw if pii_utils.validate_email(e)]
    valid_phones = []
    for raw in phones_raw:
        normalized = pii_utils.normalize_phone(raw)
        if normalized:
            valid_phones.append(normalized)

    return PiiProfile(
        name=profile_name,
        full_name=data.get("FULL_NAME", ""),
        emails=valid_emails,
        phones=valid_phones,
        addresses=pii_utils.parse_comma_list(data.get("ADDRESSES", "")),
        usernames=pii_utils.parse_comma_list(data.get("USERNAMES", "")),
        dob=data.get("DOB", ""),
    )
