"""Unit tests for the database layer."""

from privacytool.core import db
from privacytool.core.models import TrackedRecord


def test_init_creates_table(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "records" in tables
    conn.close()


def test_insert_and_retrieve(tmp_db):
    rec = TrackedRecord(target_type="engine", site="google", action_type="deindex")
    row_id = db.insert_record(tmp_db, rec)
    assert row_id is not None and row_id > 0

    records = db.get_records(tmp_db)
    assert len(records) == 1
    assert records[0].site == "google"
    assert records[0].status == "discovered"


def test_update_status(tmp_db):
    rec = TrackedRecord(target_type="broker", site="whitepages", action_type="optout")
    row_id = db.insert_record(tmp_db, rec)
    db.update_status(tmp_db, row_id, "submitted", confirmation_id="conf-123")

    records = db.get_records(tmp_db, status="submitted")
    assert len(records) == 1
    assert records[0].confirmation_id == "conf-123"
    assert records[0].follow_up_count == 1


def test_filter_by_status(tmp_db):
    db.insert_record(tmp_db, TrackedRecord(target_type="engine", site="bing", action_type="deindex"))
    db.insert_record(tmp_db, TrackedRecord(target_type="broker", site="spokeo", action_type="optout"))

    records = db.get_records(tmp_db, status="discovered")
    assert len(records) == 2

    records_engine = db.get_records(tmp_db, target_type="engine")
    assert len(records_engine) == 1
    assert records_engine[0].site == "bing"


def test_get_followups(tmp_db):
    from datetime import datetime, timedelta
    old_due = (datetime.utcnow() - timedelta(days=1)).isoformat(timespec="seconds")
    rec = TrackedRecord(target_type="engine", site="google", action_type="deindex")
    row_id = db.insert_record(tmp_db, rec)
    import sqlite3
    with sqlite3.connect(tmp_db) as conn:
        conn.execute("UPDATE records SET follow_up_due=? WHERE id=?", (old_due, row_id))

    followups = db.get_followups(tmp_db)
    assert any(r.id == row_id for r in followups)
