"""Integration tests for the CLI (no network calls)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from privacytool.cli.main import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "privacytool" in result.output.lower() or "Usage" in result.output


def test_status_empty_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "tracker.db")
    monkeypatch.setenv("PRIVACYTOOL_DB_PATH", db_file)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


def test_followups_empty(tmp_path, monkeypatch):
    db_file = str(tmp_path / "tracker.db")
    monkeypatch.setenv("PRIVACYTOOL_DB_PATH", db_file)
    result = runner.invoke(app, ["followups"])
    assert result.exit_code == 0


def test_export_empty(tmp_path, monkeypatch):
    db_file = str(tmp_path / "tracker.db")
    monkeypatch.setenv("PRIVACYTOOL_DB_PATH", db_file)
    result = runner.invoke(app, ["export", "--format", "json", "--output", str(tmp_path / "out")])
    assert result.exit_code == 0


def test_resolve_nonexistent(tmp_path, monkeypatch):
    db_file = str(tmp_path / "tracker.db")
    monkeypatch.setenv("PRIVACYTOOL_DB_PATH", db_file)
    # Resolving a non-existent ID should not crash
    result = runner.invoke(app, ["resolve", "9999"])
    assert result.exit_code == 0
