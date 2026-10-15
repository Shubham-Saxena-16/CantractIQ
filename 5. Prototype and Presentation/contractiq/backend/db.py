"""SQLite persistence. Review decisions, obligation updates and context corrections are append-only
(PRD: "save ... in an audit trail without erasing prior decisions")."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone

from .config import DB_PATH

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY, data TEXT NOT NULL, source TEXT NOT NULL, imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS uploads (
    doc_id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_path TEXT, markdown TEXT NOT NULL,
    context TEXT NOT NULL, warnings TEXT NOT NULL, info TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY, doc_id TEXT, source TEXT, severity TEXT, title TEXT, data TEXT NOT NULL,
    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, target_type TEXT NOT NULL, target_id TEXT NOT NULL, doc_id TEXT,
    disposition TEXT, note TEXT, follow_up INTEGER DEFAULT 0, reviewer TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS obligation_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT, obligation_id TEXT NOT NULL, owner TEXT, status TEXT, note TEXT,
    reviewer TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS context_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT NOT NULL, field TEXT NOT NULL, value TEXT,
    reviewer TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, doc_id TEXT, provider TEXT, model TEXT,
    sent_summary TEXT, result TEXT, created_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS review_events_no_update BEFORE UPDATE ON review_events
    BEGIN SELECT RAISE(ABORT, 'review_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_events_no_delete BEFORE DELETE ON review_events
    BEGIN SELECT RAISE(ABORT, 'review_events is append-only'); END;
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = connect()
_conn.executescript(SCHEMA)
_conn.commit()


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        return [dict(r) for r in _conn.execute(sql, params).fetchall()]


def import_tracker(rows: list[dict]) -> None:
    ts = now()
    with _lock:
        for r in rows:
            _conn.execute("INSERT INTO contracts(contract_id, data, source, imported_at) VALUES(?,?,?,?) "
                          "ON CONFLICT(contract_id) DO UPDATE SET data=excluded.data, imported_at=excluded.imported_at",
                          (r["contract_id"], json.dumps(r), "contract_tracker.csv", ts))
        _conn.commit()


def upsert_findings(findings: list[dict]) -> None:
    ts = now()
    with _lock:
        for f in findings:
            _conn.execute("INSERT INTO findings(id, doc_id, source, severity, title, data, first_seen, last_seen) VALUES(?,?,?,?,?,?,?,?) "
                          "ON CONFLICT(id) DO UPDATE SET data=excluded.data, severity=excluded.severity, title=excluded.title, last_seen=excluded.last_seen",
                          (f["id"], f.get("doc_id"), f.get("source"), f.get("severity"), f.get("title"), json.dumps(f), ts, ts))
        _conn.commit()


def add_review(target_type: str, target_id: str, doc_id: str | None, disposition: str | None, note: str | None,
               follow_up: bool, reviewer: str) -> dict:
    cur = execute("INSERT INTO review_events(target_type, target_id, doc_id, disposition, note, follow_up, reviewer, created_at) "
                  "VALUES(?,?,?,?,?,?,?,?)", (target_type, target_id, doc_id, disposition, note, int(follow_up), reviewer, now()))
    return query("SELECT * FROM review_events WHERE id=?", (cur.lastrowid,))[0]


def latest_reviews() -> dict[str, dict]:
    rows = query("SELECT * FROM review_events ORDER BY id")
    out: dict[str, dict] = {}
    for r in rows:
        prev = out.get(r["target_id"], {})
        merged = {**prev, **{k: v for k, v in r.items() if v not in (None, "")}}
        merged["follow_up"] = r["follow_up"]
        merged["history_count"] = prev.get("history_count", 0) + 1
        out[r["target_id"]] = merged
    return out


def review_history(target_id: str) -> list[dict]:
    return query("SELECT * FROM review_events WHERE target_id=? ORDER BY id DESC", (target_id,))


def obligation_overrides() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in query("SELECT * FROM obligation_updates ORDER BY id"):
        cur = out.setdefault(r["obligation_id"], {})
        for k in ("owner", "status", "note", "reviewer", "created_at"):
            if r[k] not in (None, ""):
                cur[k] = r[k]
    return out


def save_upload(doc_id, filename, stored_path, markdown, context, warnings, info):
    execute("INSERT OR REPLACE INTO uploads(doc_id, filename, stored_path, markdown, context, warnings, info, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)", (doc_id, filename, stored_path, markdown, json.dumps(context), json.dumps(warnings),
                                        json.dumps(info), now()))


def list_uploads() -> list[dict]:
    rows = query("SELECT * FROM uploads ORDER BY created_at")
    for r in rows:
        for k in ("context", "warnings", "info"):
            r[k] = json.loads(r[k])
    return rows


def corrections(doc_id: str) -> list[dict]:
    return query("SELECT * FROM context_corrections WHERE doc_id=? ORDER BY id DESC", (doc_id,))


def log_ai(kind, doc_id, provider, model, sent_summary, result):
    execute("INSERT INTO ai_runs(kind, doc_id, provider, model, sent_summary, result, created_at) VALUES(?,?,?,?,?,?,?)",
            (kind, doc_id, provider, model, sent_summary, json.dumps(result)[:20000], now()))
