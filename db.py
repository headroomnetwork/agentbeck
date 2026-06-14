"""Agent Beck — storage layer (SQLite + FTS5).

Deliberately dependency-light: stdlib sqlite3 only. The whole DB is one file
(agentbeck.db). Swap this module for Postgres + pgvector later once the idea
is proven — nothing else in the app needs to change much.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from security import (
    SecretPatternError,
    dump_warning_map,
    load_warning_map,
    merge_warning_maps,
    sanitize_tags_field,
    sanitize_text_field,
)

DB_PATH = os.environ.get("AGENTBECK_DB", os.path.join(os.path.dirname(__file__), "agentbeck.db"))
SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_bugs.json")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and migrate existing DBs forward."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            error        TEXT NOT NULL,
            fix          TEXT NOT NULL,
            journey      TEXT DEFAULT '',
            category     TEXT DEFAULT 'bug_fix',
            environment  TEXT DEFAULT '',
            tags         TEXT DEFAULT '',
            source       TEXT DEFAULT 'agent',
            confirmations INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL,
            provenance   TEXT DEFAULT '',
            handle       TEXT DEFAULT '',
            deletion_token_hash TEXT DEFAULT '',
            deleted      INTEGER NOT NULL DEFAULT 0,
            content_warnings TEXT NOT NULL DEFAULT '{}'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts
        USING fts5(error, fix, tags, journey, content='reports', content_rowid='id');

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            action      TEXT NOT NULL,
            report_id   INTEGER,
            handle      TEXT DEFAULT '',
            ip_hash     TEXT DEFAULT '',
            outcome     TEXT DEFAULT '',
            prev_hash   TEXT NOT NULL,
            hash        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS comments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id   INTEGER NOT NULL,
            journey     TEXT NOT NULL,
            source      TEXT DEFAULT 'mcp-agent',
            created_at  TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        );

        -- Phase 12 control plane (CP-01/03/04). FROZEN CONTRACT — three models
        -- (Phases 13/14/15) build against these exact columns in parallel.
        -- A raw API key is NEVER stored here; only key_ref (env var NAME or
        -- keyfile PATH). key_ref is the only secret-adjacent field and it is a
        -- reference, not a secret (Prime Directive law 3 / CONTEXT decision).
        CREATE TABLE IF NOT EXISTS crawlers (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            label          TEXT NOT NULL,
            driver         TEXT NOT NULL DEFAULT 'kimi-cli',
            endpoint       TEXT DEFAULT '',
            key_ref        TEXT DEFAULT '',
            worklist       TEXT NOT NULL DEFAULT '[]',
            schedule       TEXT DEFAULT '',
            schedule_kind  TEXT NOT NULL DEFAULT 'interval',
            budget_ceiling REAL DEFAULT 0.5,
            enabled        INTEGER NOT NULL DEFAULT 1,
            paused         INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activity_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            crawler_id  INTEGER,
            run_id      TEXT NOT NULL,
            ts          TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            domain      TEXT DEFAULT '',
            received    INTEGER DEFAULT 0,
            ingested    INTEGER DEFAULT 0,
            deduped     INTEGER DEFAULT 0,
            rejected    INTEGER DEFAULT 0,
            detail      TEXT DEFAULT '{}',
            FOREIGN KEY(crawler_id) REFERENCES crawlers(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS cost_ledger (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            crawler_id     INTEGER,
            run_id         TEXT NOT NULL,
            ts             TEXT NOT NULL,
            estimated_cost REAL NOT NULL DEFAULT 0,
            workers        INTEGER DEFAULT 0,
            domains_count  INTEGER DEFAULT 0,
            model          TEXT DEFAULT '',
            FOREIGN KEY(crawler_id) REFERENCES crawlers(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            kind         TEXT NOT NULL,
            crawler_id   INTEGER,
            message      TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY(crawler_id) REFERENCES crawlers(id) ON DELETE SET NULL
        );
        """
    )
    # Migrate: add provenance column if missing (v0 → v0.1)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(reports)").fetchall()]
    if "provenance" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN provenance TEXT DEFAULT ''")
    # Migrate: ownership columns for Phase 2 (transparency & auditability)
    if "handle" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN handle TEXT DEFAULT ''")
    if "deletion_token_hash" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN deletion_token_hash TEXT DEFAULT ''")
    if "deleted" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
    if "content_warnings" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN content_warnings TEXT NOT NULL DEFAULT '{}'")
    
    # Migrate: Phase 3 (The Context Pivot)
    if "journey" not in cols:
        conn.execute("ALTER TABLE reports ADD COLUMN journey TEXT DEFAULT ''")
        conn.execute("ALTER TABLE reports ADD COLUMN category TEXT DEFAULT 'bug_fix'")
        # Rebuild FTS table to include journey
        conn.execute("DROP TABLE IF EXISTS reports_fts")
        conn.execute(
            """
            CREATE VIRTUAL TABLE reports_fts
            USING fts5(error, fix, tags, journey, content='reports', content_rowid='id');
            """
        )
        conn.execute("INSERT INTO reports_fts(reports_fts) VALUES('rebuild')")


    # Migrate: Phase 4 (Many-to-Many Platform)
    # The comments table is handled by the CREATE TABLE IF NOT EXISTS block above.
    # Just to be safe, we check if it exists:
    res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'").fetchone()
    if not res:
        conn.execute(
            """
            CREATE TABLE comments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id   INTEGER NOT NULL,
                journey     TEXT NOT NULL,
                source      TEXT DEFAULT 'mcp-agent',
                created_at  TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
            )
            """
        )

def init_db() -> None:
    conn = _connect()
    try:
        _ensure_schema(conn)
        conn.commit()
        # Seed only if empty, so it's useful on day one (genesis block).
        count = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
        if count == 0:
            _seed(conn)
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    if not os.path.exists(SEED_PATH):
        return
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        bugs = json.load(f)
    for b in bugs:
        _insert(conn, b, seeded=True)
    conn.commit()


def _row_to_report(row: Optional[sqlite3.Row], conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    data = dict(row)
    data["content_warnings"] = load_warning_map(data.get("content_warnings"))
    
    # Fetch comments if conn is provided
    data["comments"] = []
    if conn and "id" in data:
        c_rows = conn.execute(
            "SELECT id, journey, source, created_at FROM comments WHERE report_id = ? ORDER BY id ASC", 
            (data["id"],)
        ).fetchall()
        data["comments"] = [dict(c) for c in c_rows]
        
    return data


def _sanitize_report_payload(data: Dict[str, Any], *, seeded: bool = False) -> Dict[str, Any]:
    """Sanitize inbound report data before it is written."""
    warnings: Dict[str, list[str]] = {}

    error, error_warnings = sanitize_text_field(data.get("error", ""), "error")
    if error_warnings:
        warnings["error"] = error_warnings

    fix, fix_warnings = sanitize_text_field(data.get("fix", ""), "fix")
    if fix_warnings:
        warnings["fix"] = fix_warnings

    journey, journey_warnings = sanitize_text_field(data.get("journey", ""), "journey")
    if journey_warnings:
        warnings["journey"] = journey_warnings

    category, category_warnings = sanitize_text_field(data.get("category", "bug_fix"), "category")
    if category_warnings:
        warnings["category"] = category_warnings

    environment, env_warnings = sanitize_text_field(data.get("environment", ""), "environment")
    if env_warnings:
        warnings["environment"] = env_warnings

    source, source_warnings = sanitize_text_field(data.get("source", "seed" if seeded else "agent"), "source")
    if source_warnings:
        warnings["source"] = source_warnings

    provenance, provenance_warnings = sanitize_text_field(data.get("provenance", ""), "provenance")
    if provenance_warnings:
        warnings["provenance"] = provenance_warnings

    handle, handle_warnings = sanitize_text_field(data.get("handle", ""), "handle")
    if handle_warnings:
        warnings["handle"] = handle_warnings

    tags, tag_warnings = sanitize_tags_field(data.get("tags", ""))
    if tag_warnings:
        warnings["tags"] = tag_warnings

    return {
        "error": error,
        "fix": fix,
        "journey": journey,
        "category": category,
        "environment": environment,
        "tags": tags,
        "source": source,
        "provenance": provenance,
        "handle": handle,
        "confirmations": int(data.get("confirmations", 0)),
        "content_warnings": dump_warning_map(warnings),
    }


def _sanitize_report_patch(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize fields supplied to PATCH /reports/{id}."""
    clean: Dict[str, Any] = {}
    warnings: Dict[str, list[str]] = {}

    if "fix" in fields:
        clean["fix"], field_warnings = sanitize_text_field(fields.get("fix", ""), "fix")
        if field_warnings:
            warnings["fix"] = field_warnings
    if "journey" in fields:
        clean["journey"], field_warnings = sanitize_text_field(fields.get("journey", ""), "journey")
        if field_warnings:
            warnings["journey"] = field_warnings
    if "category" in fields:
        clean["category"], field_warnings = sanitize_text_field(fields.get("category", "bug_fix"), "category")
        if field_warnings:
            warnings["category"] = field_warnings
    if "environment" in fields:
        clean["environment"], field_warnings = sanitize_text_field(fields.get("environment", ""), "environment")
        if field_warnings:
            warnings["environment"] = field_warnings
    if "tags" in fields:
        clean["tags"], field_warnings = sanitize_tags_field(fields.get("tags", ""))
        if field_warnings:
            warnings["tags"] = field_warnings

    if warnings:
        clean["content_warnings"] = dump_warning_map(warnings)
    return clean


def prepare_report_data(data: Dict[str, Any], *, seeded: bool = False) -> Dict[str, Any]:
    """Public wrapper for report sanitization."""
    return _sanitize_report_payload(data, seeded=seeded)


def prepare_report_patch(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Public wrapper for PATCH sanitization."""
    return _sanitize_report_patch(fields)


def _insert(conn: sqlite3.Connection, data: Dict[str, Any], seeded: bool = False) -> Dict[str, Any]:
    """Insert a report. Returns {"rowid": int, "token": str}. Seeds get no token
    (they are not owned by any contributor); agent submissions get a one-time
    deletion token whose SHA-256 is stored at rest."""
    clean = _sanitize_report_payload(data, seeded=seeded)
    now = datetime.now(timezone.utc).isoformat()
    token = "" if seeded else secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode()).hexdigest() if token else ""
    cur = conn.execute(
        """INSERT INTO reports (error, fix, journey, category, environment, tags, source, confirmations, created_at, provenance, handle, deletion_token_hash, content_warnings)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            clean["error"],
            clean["fix"],
            clean["journey"],
            clean["category"],
            clean["environment"],
            clean["tags"],
            clean["source"],
            clean["confirmations"],
            now,
            clean["provenance"],
            clean["handle"],
            token_hash,
            clean["content_warnings"],
        ),
    )
    rowid = cur.lastrowid
    conn.execute(
        "INSERT INTO reports_fts (rowid, error, fix, tags, journey) VALUES (?, ?, ?, ?, ?)",
        (rowid, clean["error"], clean["fix"], clean["tags"], clean["journey"]),
    )
    
    for c in data.get("comments", []):
        conn.execute(
            "INSERT INTO comments (report_id, journey, source, created_at) VALUES (?, ?, ?, ?)",
            (rowid, c.get("journey", ""), c.get("source", "mcp-agent"), now)
        )
        
    return {"rowid": rowid, "token": token}


def add_report(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = _connect()
    try:
        result = _insert(conn, data)
        conn.commit()
    finally:
        conn.close()
    report = get_report(result["rowid"])
    # The plaintext deletion token is exposed exactly once, here, on creation.
    report["deletion_token"] = result["token"]
    return report


def _token_ok(stored_hash: str, token: str) -> bool:
    return bool(stored_hash) and bool(token) and hashlib.sha256(token.encode()).hexdigest() == stored_hash


def delete_report(report_id: int, token: str) -> str:
    """Soft-delete: remove the served content but keep the row + audit history.
    Returns 'not_found', 'forbidden', or 'deleted'."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT deletion_token_hash, deleted FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        if not row:
            return "not_found"
        if not _token_ok(row["deletion_token_hash"], token):
            return "forbidden"
        conn.execute(
            "UPDATE reports SET deleted=1, error='[deleted]', fix='[deleted by owner]', tags='' WHERE id=?",
            (report_id,),
        )
        conn.execute("DELETE FROM reports_fts WHERE rowid=?", (report_id,))
        conn.commit()
        return "deleted"
    finally:
        conn.close()


def edit_report(report_id: int, token: str, fields: Dict[str, Any]) -> str:
    """Edit a report's fix/environment/tags. Returns 'not_found', 'forbidden', or 'edited'."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT deletion_token_hash, deleted FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        if not row:
            return "not_found"
        if not _token_ok(row["deletion_token_hash"], token):
            return "forbidden"
        clean = _sanitize_report_patch(fields)
        new_fix = clean.get("fix")
        new_journey = clean.get("journey")
        new_cat = clean.get("category")
        new_env = clean.get("environment")
        new_tags = clean.get("tags") if "tags" in clean else None
        sets, params = [], []
        if new_fix is not None:
            sets.append("fix=?"); params.append(new_fix)
        if new_journey is not None:
            sets.append("journey=?"); params.append(new_journey)
        if new_cat is not None:
            sets.append("category=?"); params.append(new_cat)
        if new_env is not None:
            sets.append("environment=?"); params.append(new_env)
        if new_tags is not None:
            sets.append("tags=?"); params.append(new_tags)
        if sets:
            params.append(report_id)
            conn.execute(f"UPDATE reports SET {', '.join(sets)} WHERE id=?", params)
            cur = conn.execute("SELECT error, fix, tags, journey, content_warnings FROM reports WHERE id=?", (report_id,)).fetchone()
            conn.execute("DELETE FROM reports_fts WHERE rowid=?", (report_id,))
            conn.execute(
                "INSERT INTO reports_fts (rowid, error, fix, tags, journey) VALUES (?, ?, ?, ?, ?)",
                (report_id, cur["error"], cur["fix"], cur["tags"], cur["journey"]),
            )
            if clean.get("content_warnings"):
                merged = merge_warning_maps(load_warning_map(cur["content_warnings"]), load_warning_map(clean["content_warnings"]))
                conn.execute(
                    "UPDATE reports SET content_warnings=? WHERE id=?",
                    (dump_warning_map(merged), report_id),
                )
        conn.commit()
        return "edited"
    finally:
        conn.close()


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return _row_to_report(row, conn)
    finally:
        conn.close()


def _fts_query(q: str) -> str:
    # Turn free text into a safe FTS5 OR-query. Quote each token so error
    # strings full of punctuation (e.g. "No module named 'x'") don't blow up.
    tokens = re.findall(r"[A-Za-z0-9_]+", q)
    return " OR ".join('"{}"'.format(t) for t in tokens)


def search(q: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    conn = _connect()
    try:
        match = _fts_query(q)
        if not match:
            total = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE deleted=0").fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM reports WHERE deleted=0 ORDER BY confirmations DESC, created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return {"total": total, "results": [_row_to_report(r, conn) for r in rows if r]}
        
        total = conn.execute(
            """
            SELECT COUNT(*) AS c FROM reports_fts
            JOIN reports ON reports.id = reports_fts.rowid
            WHERE reports_fts MATCH ? AND reports.deleted = 0
            """,
            (match,)
        ).fetchone()["c"]

        rows = conn.execute(
            """
            SELECT reports.*, bm25(reports_fts) AS score,
                   (julianday('now') - julianday(reports.created_at)) AS days_old
            FROM reports_fts
            JOIN reports ON reports.id = reports_fts.rowid
            WHERE reports_fts MATCH ? AND reports.deleted = 0
            ORDER BY (score - reports.confirmations * 0.5 + days_old * 0.1) ASC
            LIMIT ? OFFSET ?
            """,
            (match, limit, offset),
        ).fetchall()
        return {"total": total, "results": [_row_to_report(r, conn) for r in rows if r]}
    finally:
        conn.close()


def confirm(report_id: int) -> Optional[Dict[str, Any]]:
    """An agent reports 'this fix worked for me' — the core trust signal."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE reports SET confirmations = confirmations + 1 WHERE id = ?",
            (report_id,),
        )
        conn.commit()
        return get_report(report_id)
    finally:
        conn.close()


def recent(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE deleted=0").fetchone()["c"]
        rows = conn.execute(
            "SELECT * FROM reports WHERE deleted=0 ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return {"total": total, "results": [_row_to_report(r, conn) for r in rows if r]}
    finally:
        conn.close()


def _normalize(text: str) -> str:
    """Collapse whitespace and lowercase for dedup comparison."""
    return " ".join(text.lower().split())


def _normalize_tags(tags: str) -> str:
    """Lowercase, dedup, and clean tag strings."""
    seen = set()
    out = []
    for t in tags.lower().split():
        t = t.strip("#,.;:!?")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return " ".join(out)


def find_duplicate(error: str) -> Optional[Dict[str, Any]]:
    """Return an existing report whose normalized error matches exactly."""
    normalized_error, _ = sanitize_text_field(error, "error")
    normalized = _normalize(normalized_error)
    conn = _connect()
    try:
        # FTS5 can't do exact normalized matches, so scan recent 200 reports.
        rows = conn.execute(
            "SELECT * FROM reports WHERE deleted=0 ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        for row in rows:
            if _normalize(row["error"]) == normalized:
                return _row_to_report(row, conn)
        return None
    finally:
        conn.close()

def add_comment(report_id: int, journey: str, source: str = "mcp-agent") -> Dict[str, Any]:
    """Append a comment/context block to an existing report."""
    conn = _connect()
    try:
        # Check if report exists and isn't deleted
        row = conn.execute("SELECT id FROM reports WHERE id=? AND deleted=0", (report_id,)).fetchone()
        if not row:
            raise ValueError(f"Report {report_id} not found")
        
        clean_journey, _ = sanitize_text_field(journey, "journey")
        clean_source, _ = sanitize_text_field(source, "source")
        now = datetime.now(timezone.utc).isoformat()
        
        cur = conn.execute(
            "INSERT INTO comments (report_id, journey, source, created_at) VALUES (?, ?, ?, ?)",
            (report_id, clean_journey, clean_source, now)
        )
        conn.commit()
        
        return {
            "id": cur.lastrowid,
            "report_id": report_id,
            "journey": clean_journey,
            "source": clean_source,
            "created_at": now
        }
    finally:
        conn.close()


def stats() -> Dict[str, Any]:
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM reports WHERE deleted=0").fetchone()["c"]
        confirmed = conn.execute(
            "SELECT COALESCE(SUM(confirmations),0) AS c FROM reports WHERE deleted=0"
        ).fetchone()["c"]
        # Source mix (seed / agent / swarm / ...) so growth is auditable — which
        # records were hand-seeded, shared back by a live agent, or machine-harvested.
        by_source = {
            row["source"]: row["c"]
            for row in conn.execute(
                "SELECT COALESCE(NULLIF(source,''),'unknown') AS source, COUNT(*) AS c "
                "FROM reports WHERE deleted=0 GROUP BY source"
            ).fetchall()
        }
        last_created = conn.execute(
            "SELECT MAX(created_at) AS m FROM reports WHERE deleted=0"
        ).fetchone()["m"]
        return {
            "reports": total,
            "confirmations": confirmed,
            "by_source": by_source,
            "last_report_at": last_created,
        }
    finally:
        conn.close()


# --- Phase 2: tamper-evident audit log + privacy-preserving IP hashing ---


def _daily_salt() -> str:
    """Rotating daily salt — same IP hashes differently each day, so same-day
    rate limiting works but long-term tracking does not."""
    base = os.environ.get("AGENTBECK_SALT", "agentbeck")
    return base + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def hash_ip(ip: str) -> str:
    """Non-reversible, daily-salted hash of an IP. Never stores or returns the raw IP."""
    if not ip:
        return ""
    return hashlib.sha256((ip + _daily_salt()).encode("utf-8")).hexdigest()[:16]


def _entry_hash(ts, action, report_id, handle, ip_hash, outcome, prev_hash) -> str:
    """SHA-256 over the canonical form of an audit entry, chained off prev_hash."""
    canonical = json.dumps(
        {
            "ts": ts,
            "action": action,
            "report_id": report_id,
            "handle": handle,
            "ip_hash": ip_hash,
            "outcome": outcome,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_audit(action, report_id=None, handle="", ip_hash="", outcome="") -> Dict[str, Any]:
    """Append one tamper-evident entry to the audit log. Each entry chains off
    the previous entry's hash (the first chains off the literal "GENESIS")."""
    conn = _connect()
    try:
        last = conn.execute(
            "SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = last["hash"] if last else "GENESIS"
        ts = datetime.now(timezone.utc).isoformat()
        h = _entry_hash(ts, action, report_id, handle, ip_hash, outcome, prev_hash)
        conn.execute(
            "INSERT INTO audit_log (ts, action, report_id, handle, ip_hash, outcome, prev_hash, hash) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, action, report_id, handle, ip_hash, outcome, prev_hash, h),
        )
        conn.commit()
        return {"ts": ts, "action": action, "report_id": report_id, "hash": h, "prev_hash": prev_hash}
    finally:
        conn.close()


def audit_entries(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def audit_for_report(report_id: int) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE report_id = ? ORDER BY id ASC", (report_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def audit_for_handle(handle: str) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE handle = ? AND handle != '' ORDER BY id ASC",
            (handle,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def verify_chain() -> Dict[str, Any]:
    """Recompute the hash chain end to end. Detects any after-the-fact edit."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
        prev = "GENESIS"
        for r in rows:
            expected = _entry_hash(
                r["ts"], r["action"], r["report_id"], r["handle"], r["ip_hash"], r["outcome"], prev
            )
            if r["prev_hash"] != prev or r["hash"] != expected:
                return {"ok": False, "broken_at": r["id"], "entries": len(rows)}
            prev = r["hash"]
        return {"ok": True, "broken_at": None, "entries": len(rows)}
    finally:
        conn.close()
