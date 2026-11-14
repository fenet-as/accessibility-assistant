"""Career gateway: job listings (schema.org/JobPosting), job alerts and interview accommodations.

Job postings are persisted in SQLite via the Database repository for ACID safety and multi-process
consistency. Initial catalogs can be seeded from a JSON file (e.g. bundled jobs.json) on startup.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from assistant.infrastructure.database import Database

Job = Dict[str, Any]


class CareerService:
    def __init__(self, db: Database, seed_path: Optional[Path] = None):
        self.db = db
        if seed_path:
            self._seed(Path(seed_path))

    def _seed(self, seed_path: Path) -> None:
        """Seed initial jobs from JSON file into SQLite if the table is empty."""
        if self.db.count_jobs() == 0 and seed_path.exists():
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    jobs = json.load(f)
                for job in jobs:
                    if isinstance(job, dict) and "id" in job:
                        self.db.save_job(job)
            except Exception:
                pass

    def list_jobs(self) -> List[Job]:
        return self.db.list_jobs()

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.db.get_job(job_id)

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
    ) -> Job:
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
        }
        self.db.save_job(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        return self.db.delete_job(job_id)

    def subscribe(self, channel: str, contact: str, category: str = "all") -> int:
        return self.db.add_subscription(channel, contact, category)

    def request_accommodation(self, job_id: str, accommodations: List[str], channel: str, contact: str) -> int:
        return self.db.add_accommodation(job_id, accommodations, channel, contact)

    def sms_summary(self) -> str:
        jobs = self.list_jobs()
        if not jobs:
            return "ALX Jobs: No active openings right now. Check back soon!"
        items = []
        for number, job in enumerate(jobs, start=1):
            organization = job.get("hiringOrganization", {}).get("name", "ALX Partner")
            location = job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Remote")
            items.append(f"{number}) {job.get('alternateName', job.get('title', 'Job'))} ({organization}, {location})")
        return "ALX Jobs: " + " ".join(items) + " Visit portal to apply with accommodations."

    def telegram_summary(self) -> str:
        jobs = self.list_jobs()
        if not jobs:
            return "💼 <b>Career Gateway</b>\n\nNo active positions at the moment. Check back soon!"
        lines = ["💼 <b>Career Gateway - Available Positions</b>", ""]
        for number, job in enumerate(jobs, start=1):
            org = job.get("hiringOrganization", {}).get("name", "ALX Partner")
            accommodations = job.get("accommodationsOffered", [])
            lines += [
                f"{number}. <b>{job.get('title', 'Position')}</b>",
                f"   • Company: {org}",
                f"   • Accommodations: {', '.join(accommodations) if accommodations else 'Available upon request'}",
                "",
            ]
        lines.append("<i>To request interview accommodations, visit the web assistant portal.</i>")
        return "\n".join(lines)
