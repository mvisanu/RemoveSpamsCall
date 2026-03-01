"""Unit tests for the job runner — dry-run mode and connector wiring."""

from privacytool.core.models import ActionResult, TrackedRecord
from privacytool.core.runner import run_act, run_discover


class _MockConnector:
    name = "mock_engine"

    def discover(self, profile, dry_run=False):
        if dry_run:
            return []
        return [TrackedRecord(target_type="engine", site="mock_engine", action_type="deindex")]

    def act(self, record, dry_run=False):
        return ActionResult(success=True, message="mock ok", dry_run=dry_run)


def test_run_discover_dry_run(tmp_db, sample_profile):
    connector = _MockConnector()
    records = run_discover([connector], sample_profile, tmp_db, dry_run=True)
    assert records == []  # dry_run skips discover on mock


def test_run_discover_live(tmp_db, sample_profile):
    connector = _MockConnector()
    records = run_discover([connector], sample_profile, tmp_db, dry_run=False)
    assert len(records) == 1
    assert records[0].site == "mock_engine"
    assert records[0].id is not None


def test_run_act_dry_run(tmp_db, sample_profile):
    connector = _MockConnector()
    rec = TrackedRecord(target_type="engine", site="mock_engine", action_type="deindex", id=1)
    results = run_act({"mock_engine": connector}, [rec], tmp_db, dry_run=True)
    assert len(results) == 1
    assert results[0].dry_run is True


def test_run_act_unknown_site(tmp_db):
    rec = TrackedRecord(target_type="engine", site="unknown_site", action_type="deindex", id=99)
    results = run_act({}, [rec], tmp_db, dry_run=False)
    assert results == []
