"""Career gateway: job listings (schema.org/JobPosting), job alerts and interview accommodations."""

import json
from pathlib import Path
from typing import Any, Dict, List

from assistant.infrastructure.database import Database

Job = Dict[str, Any]


class CareerService:
    def __init__(self, db: Database, jobs_path: Path):
        self.db = db
        with open(jobs_path, "r", encoding="utf-8") as f:
            self._jobs: List[Job] = json.load(f)

    def list_jobs(self) -> List[Job]:
        return self._jobs

    def subscribe(self, channel: str, contact: str, category: str = "all") -> int:
        return self.db.add_subscription(channel, contact, category)

    def request_accommodation(self, job_id: str, accommodations: List[str], channel: str, contact: str) -> int:
        return self.db.add_accommodation(job_id, accommodations, channel, contact)

    def sms_summary(self) -> str:
        items = []
        for number, job in enumerate(self._jobs, start=1):
            organization = job["hiringOrganization"]["name"]
            location = job["jobLocation"]["address"]["addressLocality"]
            items.append(f"{number}) {job.get('alternateName', job['title'])} ({organization}, {location})")
        return "ALX Jobs: " + " ".join(items) + " Visit portal to apply with accommodations."

    def telegram_summary(self) -> str:
        lines = ["💼 <b>Career Gateway - Available Positions</b>", ""]
        for number, job in enumerate(self._jobs, start=1):
            lines += [
                f"{number}. <b>{job['title']}</b>",
                f"   • Company: {job['hiringOrganization']['name']}",
                f"   • Accommodations: {', '.join(job['accommodationsOffered'])}",
                "",
            ]
        lines.append("<i>To request interview accommodations, visit the web assistant portal.</i>")
        return "\n".join(lines)
