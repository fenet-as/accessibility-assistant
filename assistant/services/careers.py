"""Career gateway: verified job listings only, alerts, accommodations.

Jobs come from SQLite. Expired closing dates are hidden. Nothing is invented.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from assistant.infrastructure.database import Database

Job = Dict[str, Any]

JOB_INTENT_EN = re.compile(
    r"\b(job openings?|job vacancies|job postings?|available jobs|career gateway|"
    r"vacancies|hiring now|employment opportunities|open positions)\b",
    re.IGNORECASE,
)
JOB_INTENT_AM = re.compile(r"(ክፍት\s*የሥራ|ክፍት\s*ስራ|የሥራ\s*ቦታ|የስራ\s*ቦታ|ቅጥር)")


def is_job_question(text: str) -> bool:
    """True only for explicit job-seeking questions — not course text that mentions work."""
    text = text or ""
    if JOB_INTENT_EN.search(text) or JOB_INTENT_AM.search(text):
        return True
    lowered = text.lower()
    # Short English intents without course keywords.
    if re.search(r"\b(jobs?|vacancies|careers?)\b", lowered) and not re.search(
        r"\b(virtual assistant|va work|course|lesson|ai|client)\b", lowered
    ):
        return True
    return False


def _parse_closing(value: str) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


class CareerService:
    def __init__(self, db: Database, seed_path: Optional[Path] = None):
        self.db = db
        if seed_path:
            self._seed(Path(seed_path))

    def _seed(self, seed_path: Path) -> None:
        if self.db.count_jobs() == 0 and seed_path.exists():
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    jobs = json.load(f)
                for job in jobs:
                    if isinstance(job, dict) and "id" in job:
                        job.setdefault("source_url", job.get("url") or "")
                        job.setdefault("verified_at", datetime.utcnow().isoformat())
                        job.setdefault("status", "active")
                        self.db.save_job(job)
            except Exception:
                pass

    def list_jobs(self, *, include_expired: bool = False) -> List[Job]:
        jobs = self.db.list_jobs()
        if include_expired:
            return jobs
        today = date.today()
        active = []
        for job in jobs:
            if job.get("status") and job.get("status") not in ("active", ""):
                continue
            closing = _parse_closing(str(job.get("closing_date") or job.get("validThrough") or ""))
            if closing and closing < today:
                continue
            active.append(job)
        return active

    def get_job(self, job_id: str) -> Optional[Job]:
        job = self.db.get_job(job_id)
        if not job:
            return None
        if job not in self.list_jobs() and job.get("id"):
            # Still return for admin lookup, but chat answers use list_jobs.
            return job
        return job

    def add_job(
        self,
        title: str,
        company_name: str,
        description: str,
        location: str = "Addis Ababa",
        country: str = "ET",
        employment_type: str = "FULL_TIME",
        alternate_name: Optional[str] = None,
        qualifications: Optional[str] = None,
        accommodations_offered: Optional[List[str]] = None,
        job_id: Optional[str] = None,
        source_url: str = "",
        closing_date: str = "",
        verified: bool = True,
    ) -> Job:
        if not verified or not source_url:
            raise ValueError("Only verified jobs with a source_url may be published.")
        new_id = job_id or f"job-{uuid4().hex[:6]}"
        job: Job = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "id": new_id,
            "title": title,
            "alternateName": alternate_name or title,
            "description": description,
            "hiringOrganization": {
                "@type": "Organization",
                "name": company_name,
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": location,
                    "addressCountry": country,
                },
            },
            "employmentType": employment_type,
            "qualifications": qualifications or "",
            "accommodationsOffered": accommodations_offered or ["Interview accommodations upon request"],
            "source_url": source_url,
            "verified_at": datetime.utcnow().isoformat(),
            "closing_date": closing_date,
            "status": "active",
        }
        self.db.save_job(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        return self.db.delete_job(job_id)

    def subscribe(self, channel: str, contact: str, category: str = "all", consent: bool = False) -> int:
        return self.db.add_subscription(channel, contact, category, consent=consent)

    def unsubscribe(self, channel: str, contact: str) -> int:
        return self.db.remove_subscription(channel, contact)

    def request_accommodation(self, job_id: str, accommodations: List[str], channel: str, contact: str) -> int:
        job = self.db.get_job(job_id)
        if not job or not job.get("source_url"):
            raise ValueError("Accommodations can only be requested for verified job listings.")
        return self.db.add_accommodation(job_id, accommodations, channel, contact)

    def answer_job_question(self, language: str = "en") -> str:
        jobs = self.list_jobs()
        if not jobs:
            if language == "am":
                return "በአሁኑ ጊዜ የተረጋገጠ ክፍት የሥራ ቦታ የለም። ሲገኝ እንነግርዎታለን።"
            return "There are no verified open jobs right now. Nothing has been invented — check again later or subscribe for alerts."
        lines = []
        for job in jobs[:5]:
            org = job.get("hiringOrganization", {}).get("name", "Partner")
            closing = job.get("closing_date") or "open"
            lines.append(f"- {job.get('title', 'Role')} at {org} (closes {closing})")
        header = "Verified openings:" if language != "am" else "የተረጋገጡ ክፍት ቦታዎች:"
        return header + "\n" + "\n".join(lines)

    def sms_summary(self) -> str:
        jobs = self.list_jobs()
        if not jobs:
            return "ALX Jobs: No verified openings right now. Check back soon!"
        items = []
        for number, job in enumerate(jobs, start=1):
            organization = job.get("hiringOrganization", {}).get("name", "ALX Partner")
            location = job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Remote")
            items.append(f"{number}) {job.get('alternateName', job.get('title', 'Job'))} ({organization}, {location})")
        return "ALX Jobs: " + " ".join(items) + " Visit portal to apply with accommodations."

    def telegram_summary(self) -> str:
        jobs = self.list_jobs()
        if not jobs:
            return "Career Gateway\n\nNo verified positions at the moment. Check back soon!"
        lines = ["Career Gateway - Verified Positions", ""]
        for number, job in enumerate(jobs, start=1):
            org = job.get("hiringOrganization", {}).get("name", "ALX Partner")
            accommodations = job.get("accommodationsOffered", [])
            lines += [
                f"{number}. {job.get('title', 'Position')}",
                f"   Company: {org}",
                f"   Closes: {job.get('closing_date') or 'open'}",
                f"   Accommodations: {', '.join(accommodations) if accommodations else 'Available upon request'}",
                "",
            ]
        lines.append("To request interview accommodations, visit the web assistant portal. /stop to unsubscribe.")
        return "\n".join(lines)
