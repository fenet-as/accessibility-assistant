"""SQLite persistence: anonymous query logs, escalations, job alerts and accommodation requests.

WAL mode lets many readers run alongside one writer, which covers several uvicorn
workers on one host. For multiple hosts, swap this module for a Postgres implementation
with the same public methods.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

from assistant.domain.knowledge import compute_kb_version

SCHEMA = """
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message TEXT NOT NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL,
    topic TEXT,
    mode TEXT DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_query_logs_status ON query_logs(status);
CREATE INDEX IF NOT EXISTS idx_query_logs_topic ON query_logs(topic);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    contact TEXT NOT NULL,
    category TEXT DEFAULT 'all',
    consent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accommodations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    accommodations_json TEXT NOT NULL,
    contact_channel TEXT NOT NULL,
    contact_value TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    room_url TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    assigned_to TEXT,
    language TEXT DEFAULT 'en',
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sms_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact TEXT NOT NULL,
    direction TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    provider_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT DEFAULT 'Addis Ababa',
    country TEXT DEFAULT 'ET',
    employment_type TEXT DEFAULT 'FULL_TIME',
    alternate_name TEXT,
    qualifications TEXT,
    accommodations_json TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    source_url TEXT DEFAULT '',
    verified_at TEXT DEFAULT '',
    closing_date TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS job_alert_state (
    contact_hash TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    contact TEXT NOT NULL,
    last_notified_job_id TEXT DEFAULT '',
    consent INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS course_chunks (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    course TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    title TEXT NOT NULL,
    section TEXT NOT NULL,
    anchor TEXT DEFAULT '',
    url TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    text TEXT NOT NULL,
    translations_json TEXT NOT NULL DEFAULT '{}',
    keywords_en TEXT DEFAULT '',
    keywords_am TEXT DEFAULT '',
    synonyms_json TEXT NOT NULL DEFAULT '[]',
    content_hash TEXT NOT NULL DEFAULT '',
    revision INTEGER DEFAULT 1,
    raw_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_course_chunks_scope ON course_chunks(scope);
CREATE INDEX IF NOT EXISTS idx_course_chunks_lesson ON course_chunks(scope, lesson_id);

CREATE TABLE IF NOT EXISTS kb_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    kb_version TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO kb_meta (id, kb_version, revision) VALUES (1, '', 0);

CREATE TABLE IF NOT EXISTS channel_prefs (
    contact_hash TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'auto',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'New chat',
    course_id TEXT NOT NULL DEFAULT 'course:va-1',
    language TEXT NOT NULL DEFAULT 'auto',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    language TEXT DEFAULT '',
    provider TEXT DEFAULT '',
    answer_source TEXT DEFAULT '',
    source_type TEXT DEFAULT '',
    cache_hit INTEGER DEFAULT 0,
    citations_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conv ON conversation_messages(conversation_id, created_at);
"""


def anonymize(session_id: str) -> str:
    """Session ids can embed phone numbers or chat ids (SMS, Telegram); only a hash is stored."""
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Additive migrations for existing SQLite files."""
        job_cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        for column, ddl in (
            ("source_url", "ALTER TABLE jobs ADD COLUMN source_url TEXT DEFAULT ''"),
            ("verified_at", "ALTER TABLE jobs ADD COLUMN verified_at TEXT DEFAULT ''"),
            ("closing_date", "ALTER TABLE jobs ADD COLUMN closing_date TEXT DEFAULT ''"),
            ("status", "ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'active'"),
        ):
            if column not in job_cols:
                conn.execute(ddl)
        esc_cols = {row[1] for row in conn.execute("PRAGMA table_info(escalations)").fetchall()}
        for column, ddl in (
            ("assigned_to", "ALTER TABLE escalations ADD COLUMN assigned_to TEXT"),
            ("language", "ALTER TABLE escalations ADD COLUMN language TEXT DEFAULT 'en'"),
            ("topic", "ALTER TABLE escalations ADD COLUMN topic TEXT"),
        ):
            if column not in esc_cols:
                conn.execute(ddl)
        sub_cols = {row[1] for row in conn.execute("PRAGMA table_info(subscriptions)").fetchall()}
        if "consent" not in sub_cols:
            conn.execute("ALTER TABLE subscriptions ADD COLUMN consent INTEGER DEFAULT 0")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _insert(self, sql: str, params: tuple) -> int:
        with self._connect() as conn:
            return conn.execute(sql, params).lastrowid

    def log_query(
        self,
        session_id: str,
        message: str,
        language: str,
        status: str,
        topic: Optional[str] = None,
        mode: str = "normal",
    ) -> None:
        self._insert(
            "INSERT INTO query_logs (session_id, message, language, status, topic, mode) VALUES (?, ?, ?, ?, ?, ?)",
            (anonymize(session_id), message, language, status, topic, mode),
        )

    def log_escalation(
        self,
        ticket_id: str,
        session_id: str,
        room_url: str,
        *,
        language: str = "en",
        topic: str = "",
        status: str = "open",
    ) -> None:
        self._insert(
            "INSERT INTO escalations (ticket_id, session_id, room_url, status, language, topic) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, anonymize(session_id), room_url, status, language, topic),
        )

    def update_escalation(self, ticket_id: str, *, status: Optional[str] = None, assigned_to: Optional[str] = None) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT ticket_id FROM escalations WHERE ticket_id = ?", (ticket_id,)).fetchone()
            if not row:
                return False
            if status is not None:
                conn.execute("UPDATE escalations SET status = ? WHERE ticket_id = ?", (status, ticket_id))
            if assigned_to is not None:
                conn.execute("UPDATE escalations SET assigned_to = ? WHERE ticket_id = ?", (assigned_to, ticket_id))
            return True

    def get_escalation(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ticket_id, session_id, room_url, status, assigned_to, language, topic, created_at "
                "FROM escalations WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()
            return dict(row) if row else None

    def log_sms_message(self, contact: str, direction: str, body: str, status: str = "queued", provider_id: str = "") -> int:
        return self._insert(
            "INSERT INTO sms_messages (contact, direction, body, status, provider_id) VALUES (?, ?, ?, ?, ?)",
            (contact, direction, body[:500], status, provider_id),
        )

    def update_sms_status(self, provider_id: str, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE sms_messages SET status = ? WHERE provider_id = ?",
                (status, provider_id),
            )
            return cur.rowcount > 0

    def add_subscription(self, channel: str, contact: str, category: str = "all", consent: bool = False) -> int:
        return self._insert(
            "INSERT INTO subscriptions (channel, contact, category, consent) VALUES (?, ?, ?, ?)",
            (channel, contact, category, 1 if consent else 0),
        )

    def list_subscriptions(self, *, consented_only: bool = True) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            sql = "SELECT id, channel, contact, category, consent FROM subscriptions"
            if consented_only:
                sql += " WHERE consent = 1"
            rows = conn.execute(sql).fetchall()
            return [dict(row) for row in rows]

    def remove_subscription(self, channel: str, contact: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM subscriptions WHERE channel = ? AND contact = ?",
                (channel, contact),
            )
            return cur.rowcount

    def set_alert_state(self, channel: str, contact: str, last_job_id: str, consent: bool = True) -> None:
        contact_hash = anonymize(f"{channel}:{contact}")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO job_alert_state (contact_hash, channel, contact, last_notified_job_id, consent, updated_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(contact_hash) DO UPDATE SET last_notified_job_id = excluded.last_notified_job_id, "
                "consent = excluded.consent, updated_at = CURRENT_TIMESTAMP",
                (contact_hash, channel, contact, last_job_id, 1 if consent else 0),
            )

    def get_alert_state(self, channel: str, contact: str) -> Optional[Dict[str, Any]]:
        contact_hash = anonymize(f"{channel}:{contact}")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT channel, contact, last_notified_job_id, consent FROM job_alert_state WHERE contact_hash = ?",
                (contact_hash,),
            ).fetchone()
            return dict(row) if row else None

    def add_accommodation(self, job_id: str, accommodations: List[str], channel: str, value: str) -> int:
        return self._insert(
            "INSERT INTO accommodations (job_id, accommodations_json, contact_channel, contact_value) "
            "VALUES (?, ?, ?, ?)",
            (job_id, json.dumps(accommodations), channel, value),
        )

    def save_job(self, job: Dict[str, Any]) -> None:
        """Insert or replace a job listing in SQLite."""
        accommodations = job.get("accommodationsOffered", [])
        company_name = job.get("hiringOrganization", {}).get("name", "")
        location = job.get("jobLocation", {}).get("address", {}).get("addressLocality", "")
        country = job.get("jobLocation", {}).get("address", {}).get("addressCountry", "ET")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs "
                "(id, title, company_name, description, location, country, employment_type, alternate_name, "
                "qualifications, accommodations_json, raw_json, source_url, verified_at, closing_date, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job["id"],
                    job.get("title", ""),
                    company_name,
                    job.get("description", ""),
                    location,
                    country,
                    job.get("employmentType", "FULL_TIME"),
                    job.get("alternateName"),
                    job.get("qualifications", ""),
                    json.dumps(accommodations),
                    json.dumps(job),
                    job.get("source_url", ""),
                    job.get("verified_at", ""),
                    job.get("closing_date", job.get("validThrough", "")),
                    job.get("status", "active"),
                ),
            )

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all active job postings."""
        with self._connect() as conn:
            rows = conn.execute("SELECT raw_json FROM jobs ORDER BY created_at ASC").fetchall()
            return [json.loads(row["raw_json"]) for row in rows]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single job posting by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT raw_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return json.loads(row["raw_json"]) if row else None

    def delete_job(self, job_id: str) -> bool:
        """Delete a job posting by ID."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cur.rowcount > 0

    def count_jobs(self) -> int:
        """Return total count of jobs stored in the database."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    @staticmethod
    def _chunk_row(c: Dict[str, Any]) -> tuple:
        return (
            c["id"],
            c["scope"],
            c["course"],
            c.get("lesson_id", ""),
            c["title"],
            c["section"],
            c.get("anchor", ""),
            c["url"],
            c.get("language", "en"),
            c["text"],
            json.dumps(c.get("translations", {})),
            c.get("keywords_en", ""),
            c.get("keywords_am", ""),
            json.dumps(c.get("synonyms", [])),
            c.get("content_hash", ""),
            c.get("revision", 1),
            json.dumps(c),
        )

    def save_course_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Store or update course curriculum chunks in SQLite (does not bump kb_meta)."""
        with self._connect() as conn:
            for c in chunks:
                conn.execute(
                    "INSERT OR REPLACE INTO course_chunks ("
                    "id, scope, course, lesson_id, title, section, anchor, url, language, text, "
                    "translations_json, keywords_en, keywords_am, synonyms_json, content_hash, revision, raw_json, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    self._chunk_row(c),
                )

    def list_course_chunks(
        self, scope: Optional[str] = None, lesson_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve course chunks directly from SQLite."""
        with self._connect() as conn:
            sql = "SELECT raw_json FROM course_chunks"
            params: List[Any] = []
            clauses = []
            if scope:
                clauses.append("scope = ?")
                params.append(scope)
            if lesson_id:
                clauses.append("lesson_id = ?")
                params.append(lesson_id)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY rowid ASC"
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [json.loads(row["raw_json"]) for row in rows]

    def count_course_chunks(self, scope: Optional[str] = None) -> int:
        """Count total course chunks stored in SQLite."""
        with self._connect() as conn:
            if scope:
                return conn.execute("SELECT COUNT(*) FROM course_chunks WHERE scope = ?", (scope,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM course_chunks").fetchone()[0]

    def delete_course_chunks(self, scope: str, lesson_id: Optional[str] = None) -> int:
        """Delete course chunks by course scope and optional lesson ID."""
        with self._connect() as conn:
            if lesson_id:
                cur = conn.execute("DELETE FROM course_chunks WHERE scope = ? AND lesson_id = ?", (scope, lesson_id))
            elif scope == "%":
                cur = conn.execute("DELETE FROM course_chunks")
            else:
                cur = conn.execute("DELETE FROM course_chunks WHERE scope = ?", (scope,))
            return cur.rowcount

    def get_kb_revision(self) -> int:
        """Monotonic revision shared across workers; bumps on every corpus write."""
        with self._connect() as conn:
            row = conn.execute("SELECT revision FROM kb_meta WHERE id = 1").fetchone()
            return int(row["revision"]) if row else 0

    def get_kb_version(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT kb_version FROM kb_meta WHERE id = 1").fetchone()
            return row["kb_version"] if row else ""

    def replace_lesson_chunks(
        self,
        remove_ids: Set[str],
        new_chunks: List[Dict[str, Any]],
    ) -> str:
        """Atomically remove old lesson rows and insert replacements; bump kb_meta. Returns kb_version."""
        with self._connect() as conn:
            for chunk_id in remove_ids:
                conn.execute("DELETE FROM course_chunks WHERE id = ?", (chunk_id,))
            for c in new_chunks:
                conn.execute(
                    "INSERT OR REPLACE INTO course_chunks ("
                    "id, scope, course, lesson_id, title, section, anchor, url, language, text, "
                    "translations_json, keywords_en, keywords_am, synonyms_json, content_hash, revision, raw_json, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    self._chunk_row(c),
                )
            rows = conn.execute("SELECT raw_json FROM course_chunks ORDER BY rowid ASC").fetchall()
            all_chunks = [json.loads(row["raw_json"]) for row in rows]
            kb_version = compute_kb_version(all_chunks)
            conn.execute(
                "UPDATE kb_meta SET kb_version = ?, revision = revision + 1, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (kb_version,),
            )
            return kb_version

    def replace_all_course_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Replace the entire course corpus in one transaction; bump kb_meta. Returns kb_version."""
        with self._connect() as conn:
            conn.execute("DELETE FROM course_chunks")
            for c in chunks:
                conn.execute(
                    "INSERT INTO course_chunks ("
                    "id, scope, course, lesson_id, title, section, anchor, url, language, text, "
                    "translations_json, keywords_en, keywords_am, synonyms_json, content_hash, revision, raw_json, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    self._chunk_row(c),
                )
            kb_version = compute_kb_version(chunks)
            conn.execute(
                "UPDATE kb_meta SET kb_version = ?, revision = revision + 1, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (kb_version,),
            )
            return kb_version

    def set_channel_language(self, channel: str, contact: str, language: str) -> None:
        """Persist a channel language preference keyed by a hashed contact id."""
        contact_hash = anonymize(f"{channel}:{contact}")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO channel_prefs (contact_hash, channel, language, updated_at) "
                "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(contact_hash) DO UPDATE SET language = excluded.language, "
                "updated_at = CURRENT_TIMESTAMP",
                (contact_hash, channel, language),
            )

    def get_channel_language(self, channel: str, contact: str) -> Optional[str]:
        contact_hash = anonymize(f"{channel}:{contact}")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT language FROM channel_prefs WHERE contact_hash = ?",
                (contact_hash,),
            ).fetchone()
            return row["language"] if row else None

    def analytics_summary(self, top_n: int = 5) -> Dict[str, Any]:
        with self._connect() as conn:
            def scalar(sql: str) -> int:
                return conn.execute(sql).fetchone()[0]

            def grouped(column: str) -> Dict[str, int]:
                rows = conn.execute(f"SELECT {column}, COUNT(*) FROM query_logs GROUP BY {column}")
                return {row[0]: row[1] for row in rows}

            statuses = grouped("status")
            top_topics = conn.execute(
                "SELECT topic, COUNT(*) AS n FROM query_logs WHERE status = 'answered' "
                "GROUP BY topic ORDER BY n DESC LIMIT ?",
                (top_n,),
            ).fetchall()
            unanswered = conn.execute(
                "SELECT message FROM query_logs WHERE status = 'not_found' ORDER BY id DESC LIMIT ?",
                (top_n,),
            ).fetchall()

            return {
                "total_queries": scalar("SELECT COUNT(*) FROM query_logs"),
                "languages": grouped("language"),
                "resolutions": statuses,
                "top_topics": [{"topic": row["topic"], "count": row["n"]} for row in top_topics],
                "curriculum_gaps": {
                    "unresolved_count": statuses.get("not_found", 0),
                    "sample_unanswered_topics": [row["message"] for row in unanswered],
                },
                "career_gateway": {
                    "total_active_jobs": scalar("SELECT COUNT(*) FROM jobs"),
                    "total_accommodations_requested": scalar("SELECT COUNT(*) FROM accommodations"),
                    "total_alert_subscribers": scalar("SELECT COUNT(*) FROM subscriptions"),
                },
                "escalations": scalar("SELECT COUNT(*) FROM escalations"),
            }

    # --- Chat conversations (Phase 2 persistence) ---

    def create_conversation(
        self,
        conversation_id: str,
        owner_id: str,
        *,
        title: str = "New chat",
        course_id: str = "course:va-1",
        language: str = "auto",
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, owner_id, title, course_id, language) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, owner_id, title, course_id, language),
            )
        return self.get_conversation(conversation_id, owner_id)  # type: ignore[return-value]

    def get_conversation(self, conversation_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND owner_id = ?",
                (conversation_id, owner_id),
            ).fetchone()
            return dict(row) if row else None

    def list_conversations(self, owner_id: str, *, limit: int = 100, q: str = "") -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if q.strip():
                like = f"%{q.strip()}%"
                rows = conn.execute(
                    "SELECT DISTINCT c.* FROM conversations c "
                    "LEFT JOIN conversation_messages m ON m.conversation_id = c.id "
                    "WHERE c.owner_id = ? AND (c.title LIKE ? OR m.content LIKE ?) "
                    "ORDER BY c.updated_at DESC LIMIT ?",
                    (owner_id, like, like, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE owner_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (owner_id, limit),
                ).fetchall()
            return [dict(r) for r in rows]

    def rename_conversation(self, conversation_id: str, owner_id: str, title: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND owner_id = ?",
                (title.strip() or "New chat", conversation_id, owner_id),
            )
            return cur.rowcount > 0

    def delete_conversation(self, conversation_id: str, owner_id: str) -> bool:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM conversation_messages WHERE conversation_id IN "
                "(SELECT id FROM conversations WHERE id = ? AND owner_id = ?)",
                (conversation_id, owner_id),
            )
            cur = conn.execute(
                "DELETE FROM conversations WHERE id = ? AND owner_id = ?",
                (conversation_id, owner_id),
            )
            return cur.rowcount > 0

    def touch_conversation(self, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )

    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        *,
        language: str = "",
        provider: str = "",
        answer_source: str = "",
        source_type: str = "",
        cache_hit: bool = False,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversation_messages "
                "(id, conversation_id, role, content, language, provider, answer_source, source_type, "
                "cache_hit, citations_json, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    language,
                    provider,
                    answer_source,
                    source_type,
                    1 if cache_hit else 0,
                    json.dumps(citations or []),
                    json.dumps(metadata or {}),
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
            row = conn.execute(
                "SELECT * FROM conversation_messages WHERE id = ?", (message_id,)
            ).fetchone()
            return self._message_row(row)

    def list_messages(self, conversation_id: str, owner_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            owned = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND owner_id = ?",
                (conversation_id, owner_id),
            ).fetchone()
            if not owned:
                return []
            rows = conn.execute(
                "SELECT * FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at ASC, rowid ASC",
                (conversation_id,),
            ).fetchall()
            return [self._message_row(r) for r in rows]

    @staticmethod
    def _message_row(row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["cache_hit"] = bool(data.get("cache_hit"))
        try:
            data["citations"] = json.loads(data.pop("citations_json") or "[]")
        except json.JSONDecodeError:
            data["citations"] = []
        try:
            data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
        except json.JSONDecodeError:
            data["metadata"] = {}
        return data
