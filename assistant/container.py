"""Composition root: builds every service exactly once and wires dependencies.

The API, the Telegram long-poller and the SMS adapter all share one container, so
an ingested course is visible on every channel immediately.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from assistant.config import DATA_DIR, Settings, get_settings
from assistant.domain.ports import AIProvider
from assistant.infrastructure.answer_cache import AnswerCache
from assistant.infrastructure.chunk_store import ChunkStore
from assistant.infrastructure.database import Database
from assistant.infrastructure.providers import build_provider
from assistant.infrastructure.rate_limit import RateLimiter
from assistant.infrastructure.usage import UsageTracker
from assistant.services.analytics import AnalyticsService
from assistant.services.careers import CareerService
from assistant.services.conversations import ConversationService
from assistant.services.course_admin import CourseAdminService
from assistant.services.course_matcher import CourseMatcher
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
    conversations: ConversationService
    cache: AnswerCache
    usage: UsageTracker
    rate_limiter: RateLimiter
    db: Database


def build_container(settings: Optional[Settings] = None, provider: Optional[AIProvider] = None) -> Container:
    settings = settings or get_settings()
    usage = UsageTracker()
    provider = provider or build_provider(settings, usage=usage)
    cache = AnswerCache(settings)
    rate_limiter = RateLimiter(
        settings.redis_url,
        session_per_min=settings.rate_limit_session_per_min,
        ip_per_min=settings.rate_limit_ip_per_min,
        stt_per_min=settings.rate_limit_stt_per_min,
        daily_token_budget=settings.daily_token_budget,
        daily_cost_budget_usd=settings.daily_cost_budget_usd,
    )
    usage.budget_sink = rate_limiter.record_budget
    db = Database(settings.database_path)
    store = ChunkStore(settings.chunks_path, db=db)
    store.seed_from(BUNDLED_CHUNKS)
    careers = CareerService(db, settings.jobs_path)
    course_matcher = CourseMatcher(store)
    tutor = TutorService(
        store,
        provider,
        settings.relevance_threshold,
        cache=cache,
        usage=usage,
        settings=settings,
        rate_limiter=rate_limiter,
        careers=careers,
        course_matcher=course_matcher,
    )
    return Container(
        settings=settings,
        provider=provider,
        tutor=tutor,
        cache=cache,
        usage=usage,
        rate_limiter=rate_limiter,
        db=db,
        escalations=EscalationService(
            db,
            settings.jitsi_base_url,
            telegram_bot_token=settings.telegram_bot_token,
            staff_chat_id=settings.telegram_staff_chat_id,
        ),
        careers=careers,
        analytics=AnalyticsService(db, log_question_text=settings.log_question_text),
        courses=CourseAdminService(
            store,
            tutor,
            max_content_chars=settings.ingest_max_content_chars,
        ),
        conversations=ConversationService(db),
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container()
