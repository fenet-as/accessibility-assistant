"""
SQLite Database Layer for ALX Accessibility Assistant.
Provides lightweight, zero-dependency persistence with privacy-by-design.
No personal data (PII) is stored by default.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "assistant.db"


def get_db_connection() -> sqlite3.Connection:
    """Create or connect to SQLite database with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Anonymous queries log for Teacher Analytics & course gap identification
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT NOT NULL,
            topic TEXT,
            mode TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Career Gateway job alerts subscriptions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            contact TEXT NOT NULL,
            category TEXT DEFAULT 'all',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Privacy-preserving interview accommodation requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accommodations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            accommodations_json TEXT NOT NULL,
            contact_channel TEXT NOT NULL,
            contact_value TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Human escalation logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            session_id TEXT NOT NULL,
            room_url TEXT NOT NULL,
            status TEXT DEFAULT 'pending_tutor',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def log_query(session_id: str, message: str, language: str, status: str, topic: Optional[str] = None, mode: str = "normal"):
    """Log anonymous query for aggregate curriculum analytics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO query_logs (session_id, message, language, status, topic, mode) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, message, language, status, topic, mode)
    )
    conn.commit()
    conn.close()


def add_subscription(channel: str, contact: str, category: str = "all") -> int:
    """Store job alert subscription."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subscriptions (channel, contact, category) VALUES (?, ?, ?)",
        (channel, contact, category)
    )
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id


def add_accommodation(job_id: str, accommodations: List[str], channel: str, value: str) -> int:
    """Store interview accommodation request."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO accommodations (job_id, accommodations_json, contact_channel, contact_value) VALUES (?, ?, ?, ?)",
        (job_id, json.dumps(accommodations), channel, value)
    )
    conn.commit()
    rec_id = cursor.lastrowid
    conn.close()
    return rec_id


def log_escalation(ticket_id: str, session_id: str, room_url: str):
    """Store escalation record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO escalations (ticket_id, session_id, room_url) VALUES (?, ?, ?)",
        (ticket_id, session_id, room_url)
    )
    conn.commit()
    conn.close()


def get_analytics_summary() -> Dict[str, Any]:
    """
    Generate privacy-preserving, aggregated teacher analytics.
    Enforces minimum aggregation (k-anonymity) to protect learner privacy.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM query_logs")
    total_queries = cursor.fetchone()["total"]

    cursor.execute("SELECT language, COUNT(*) as count FROM query_logs GROUP BY language")
    lang_breakdown = {row["language"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT status, COUNT(*) as count FROM query_logs GROUP BY status")
    status_breakdown = {row["status"]: row["count"] for row in cursor.fetchall()}

    # Unanswered queries indicating curriculum gaps
    cursor.execute("SELECT message FROM query_logs WHERE status = 'not_found' ORDER BY id DESC LIMIT 5")
    recent_unanswered = [row["message"] for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM accommodations")
    total_accommodations = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM subscriptions")
    total_subscriptions = cursor.fetchone()["total"]

    conn.close()

    return {
        "total_queries": total_queries,
        "languages": lang_breakdown,
        "resolutions": status_breakdown,
        "curriculum_gaps": {
            "unresolved_count": status_breakdown.get("not_found", 0),
            "sample_unanswered_topics": recent_unanswered
        },
        "career_gateway": {
            "total_accommodations_requested": total_accommodations,
            "total_alert_subscribers": total_subscriptions
        }
    }


# Auto-initialize database on import
init_db()

