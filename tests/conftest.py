"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from privacytool.core import db
from privacytool.core.models import PiiProfile


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    """Return a path to a freshly initialised SQLite database in a temp dir."""
    db_file = str(tmp_path / "test.db")
    db.init_db(db_file)
    return db_file


@pytest.fixture
def sample_profile() -> PiiProfile:
    return PiiProfile(
        name="testuser",
        full_name="Jane Doe",
        emails=["jane@example.com"],
        phones=["+18005551234"],
        addresses=["123 Main St, Springfield, IL 62701"],
        usernames=["jane_doe_99"],
        dob="1985-04-12",
    )
