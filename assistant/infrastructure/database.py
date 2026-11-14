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
from typing import Any, Dict, Iterator, List, Optional

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
    status TEXT DEFAULT 'pending_tutor',
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
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

    def log_escalation(self, ticket_id: str, session_id: str, room_url: str) -> None:
        self._insert(
            "INSERT INTO escalations (ticket_id, session_id, room_url) VALUES (?, ?, ?)",
            (ticket_id, anonymize(session_id), room_url),
        )

    def add_subscription(self, channel: str, contact: str, category: str = "all") -> int:
        return self._insert(
            "INSERT INTO subscriptions (channel, contact, category) VALUES (?, ?, ?)",
            (channel, contact, category),
        )

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
                "(id, title, company_name, description, location, country, employment_type, alternate_name, qualifications, accommodations_json, raw_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
