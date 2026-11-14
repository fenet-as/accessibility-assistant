"""Composition root: builds every service exactly once and wires dependencies.

The API, the Telegram long-poller and the SMS adapter all share one container, so
an ingested course is visible on every channel immediately.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from assistant.config import DATA_DIR, Settings, get_settings
from assistant.domain.ports import AIProvider
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.database import Database
from assistant.infrastructure.providers import build_provider
from assistant.services.analytics import AnalyticsService
from assistant.services.careers import CareerService
from assistant.services.course_admin import CourseAdminService
from assistant.services.escalation import EscalationService
from assistant.services.tutor import TutorService

BUNDLED_CHUNKS = DATA_DIR / "chunks.json"


@dataclass
class Container:
    settings: Settings
    provider: AIProvider
    tutor: TutorService
    escalations: EscalationService
    careers: CareerService
    analytics: AnalyticsService
    courses: CourseAdminService


def build_container(settings: Optional[Settings] = None, provider: Optional[AIProvider] = None) -> Container:
    settings = settings or get_settings()
    provider = provider or build_provider(settings)
    db = Database(settings.database_path)
    store = ChunkStore(settings.chunks_path)
    store.seed_from(BUNDLED_CHUNKS)
    tutor = TutorService(store, provider, settings.relevance_threshold, db=db)
    return Container(
        settings=settings,
        provider=provider,
        tutor=tutor,
        escalations=EscalationService(db, settings.jitsi_base_url),
        careers=CareerService(db, settings.jobs_path),
        analytics=AnalyticsService(db),
        courses=CourseAdminService(store, tutor),
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container()
