"""Career gateway: job listings (schema.org/JobPosting), job alerts and interview accommodations."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from assistant.infrastructure.database import Database

Job = Dict[str, Any]


class CareerService:
    def __init__(self, db: Database, jobs_path: Path):
        self.db = db
        self.jobs_path = Path(jobs_path)
        self._jobs: List[Job] = []
        self._load()

    def _load(self) -> None:
        if self.jobs_path.exists():
            try:
                with open(self.jobs_path, "r", encoding="utf-8") as f:
                    self._jobs = json.load(f)
            except Exception:
                self._jobs = []
        else:
            self._jobs = []

    def _save(self) -> None:
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.jobs_path, "w", encoding="utf-8") as f:
            json.dump(self._jobs, f, indent=2, ensure_ascii=False)

    def list_jobs(self) -> List[Job]:
        return list(self._jobs)

    def get_job(self, job_id: str) -> Optional[Job]:
        for job in self._jobs:
            if job.get("id") == job_id:
                return job
        return None

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
        self._jobs.append(job)
        self._save()
        return job

    def delete_job(self, job_id: str) -> bool:
        initial_len = len(self._jobs)
        self._jobs = [j for j in self._jobs if j.get("id") != job_id]
        if len(self._jobs) < initial_len:
            self._save()
            return True
        return False

    def subscribe(self, channel: str, contact: str, category: str = "all") -> int:
        return self.db.add_subscription(channel, contact, category)

    def request_accommodation(self, job_id: str, accommodations: List[str], channel: str, contact: str) -> int:
        return self.db.add_accommodation(job_id, accommodations, channel, contact)

    def sms_summary(self) -> str:
        if not self._jobs:
            return "ALX Jobs: No active openings right now. Check back soon!"
        items = []
        for number, job in enumerate(self._jobs, start=1):
            organization = job.get("hiringOrganization", {}).get("name", "ALX Partner")
            location = job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Remote")
            items.append(f"{number}) {job.get('alternateName', job.get('title', 'Job'))} ({organization}, {location})")
        return "ALX Jobs: " + " ".join(items) + " Visit portal to apply with accommodations."

    def telegram_summary(self) -> str:
        if not self._jobs:
            return "💼 <b>Career Gateway</b>\n\nNo active positions at the moment. Check back soon!"
        lines = ["💼 <b>Career Gateway - Available Positions</b>", ""]
        for number, job in enumerate(self._jobs, start=1):
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
