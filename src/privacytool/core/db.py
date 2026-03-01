"""SQLite database layer — schema, CRUD, status transitions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from privacytool.core.models import TrackedRecord, RecordStatus


_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT    NOT NULL,
    site            TEXT    NOT NULL,
    url             TEXT    NOT NULL DEFAULT '',
    discovered_on   TEXT    NOT NULL,
    action_type     TEXT,
    status          TEXT    NOT NULL DEFAULT 'discovered',
    confirmation_id TEXT    NOT NULL DEFAULT '',
    last_attempt    TEXT    NOT NULL DEFAULT '',
    follow_up_due   TEXT    NOT NULL DEFAULT '',
    follow_up_count INTEGER NOT NULL DEFAULT 0,
    notes           TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_status        ON records(status);
CREATE INDEX IF NOT EXISTS idx_follow_up_due ON records(follow_up_due);
CREATE INDEX IF NOT EXISTS idx_site          ON records(site);
"""

_FOLLOW_UP_DAYS = 30


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    """Create tables if they don't already exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def insert_record(db_path: str, record: TrackedRecord) -> int:
    """Insert *record* and return the new row id."""
    follow_up_due = (
        datetime.utcnow() + timedelta(days=_FOLLOW_UP_DAYS)
    ).isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO records
               (target_type, site, url, discovered_on, action_type,
                status, confirmation_id, last_attempt, follow_up_due,
                follow_up_count, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.target_type,
                record.site,
                record.url,
                record.discovered_on,
                record.action_type,
                record.status,
                record.confirmation_id,
                record.last_attempt,
                follow_up_due,
                record.follow_up_count,
                record.notes,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def update_status(
    db_path: str,
    record_id: int,
    status: RecordStatus,
    confirmation_id: str = "",
    notes: str = "",
) -> None:
    last_attempt = datetime.utcnow().isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        conn.execute(
            """UPDATE records
               SET status=?, confirmation_id=?, last_attempt=?, notes=notes||?
               WHERE id=?""",
            (status, confirmation_id, last_attempt, f"\n{notes}" if notes else "", record_id),
        )
        if status in ("submitted", "failed"):
            conn.execute(
                "UPDATE records SET follow_up_count=follow_up_count+1 WHERE id=?",
                (record_id,),
            )


def get_records(
    db_path: str,
    status: Optional[RecordStatus] = None,
    target_type: Optional[str] = None,
) -> list[TrackedRecord]:
    sql = "SELECT * FROM records WHERE 1=1"
    params: list[str] = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if target_type:
        sql += " AND target_type=?"
        params.append(target_type)
    sql += " ORDER BY discovered_on DESC"
    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(r) for r in rows]


def get_followups(db_path: str) -> list[TrackedRecord]:
    """Return records where follow_up_due <= now and status is not terminal."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    terminal = ("resolved", "confirmed")
    placeholders = ",".join("?" * len(terminal))
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM records WHERE follow_up_due<=? AND status NOT IN ({placeholders})",
            [now, *terminal],
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def get_all_records(db_path: str) -> list[TrackedRecord]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM records ORDER BY discovered_on DESC").fetchall()
    return [_row_to_record(r) for r in rows]


def _row_to_record(row: sqlite3.Row) -> TrackedRecord:
    return TrackedRecord(
        id=row["id"],
        target_type=row["target_type"],
        site=row["site"],
        url=row["url"],
        discovered_on=row["discovered_on"],
        action_type=row["action_type"],
        status=row["status"],
        confirmation_id=row["confirmation_id"],
        last_attempt=row["last_attempt"],
        follow_up_due=row["follow_up_due"],
        follow_up_count=row["follow_up_count"],
        notes=row["notes"],
    )
