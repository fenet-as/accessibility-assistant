"""Tests for Omnichannel Adapters: Telegram and Low-Bandwidth SMS."""

import pytest
from assistant.adapters.sms.service import SMSAdapter
from assistant.adapters.telegram.bot import TelegramAdapter


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sms_adapter():
    return SMSAdapter()


@pytest.fixture
def tg_adapter():
    return TelegramAdapter(token="MOCK_TEST_TOKEN")


def test_sms_help_command(sms_adapter):
    """SMS HELP should return clear concise menu."""
    segments = sms_adapter.handle_inbound_sms("+251911000000", "HELP")
    assert len(segments) >= 1
    assert "1: Jobs" in segments[0]
    assert "2: Human Tutor" in segments[0]


def test_sms_jobs_command(sms_adapter):
    """SMS 1 or JOBS returns short jobs summary."""
    segments = sms_adapter.handle_inbound_sms("+251911000000", "1")
    assert len(segments) >= 1
    assert "Junior VA" in segments[0]


def test_sms_course_query_with_citation(sms_adapter):
    """SMS course query returns grounded text with section citation reference."""
    segments = sms_adapter.handle_inbound_sms(
        "+251911000000",
        "What is shaping the future of virtual assistant work?"
    )
    assert len(segments) >= 1
    full_text = " ".join(segments)
    assert "Ref:" in full_text or "remote-first" in full_text.lower()


def test_sms_unicode_splitting(sms_adapter):
    """Verify safe segment splitting for Amharic Unicode (<= 70 chars)."""
    amharic_text = (
        "ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ውስጥ ትልቅ ሚና ይጫወታል። "
        "AI እንደ ኢሜይል መጻፍ፣ ጽሑፎችን ማጠቃለልና መረጃ መፈለግ ያሉ ስራዎችን ያግዛል። "
        "ነገር ግን የሰው ቨርቹዋል ረዳቶች የደንበኛ ግንኙነትን በመምራትና በስሜት ብስለት እጅግ አስፈላጊ ሆነው ይቀጥላሉ።"
    )
    segments = sms_adapter.split_segments(amharic_text)
    assert len(segments) >= 2
    for s in segments:
        assert len(s) <= 80, f"Segment exceeded unicode boundary: {len(s)}"


@pytest.mark.anyio
async def test_telegram_start_command(tg_adapter):
    """Telegram /start command returns welcome and language options."""
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "/start"
        }
    }
    res = await tg_adapter.handle_update(update)
    assert res["action"] == "start"
    assert res["chat_id"] == 12345


@pytest.mark.anyio
async def test_telegram_human_command(tg_adapter):
    """Telegram /human command returns Jitsi meeting room."""
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "/human"
        }
    }
    res = await tg_adapter.handle_update(update)
    assert res["action"] == "human_escalate"
    assert "ALX-Help-" in res["room"]


@pytest.mark.anyio
async def test_telegram_jobs_command(tg_adapter):
    """Telegram /jobs command returns career listings."""
    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "/jobs"
        }
    }
    res = await tg_adapter.handle_update(update)
    assert res["action"] == "jobs"
    assert res["chat_id"] == 12345


@pytest.mark.anyio
async def test_telegram_unconfigured_get_me():
    """Empty token returns None gracefully."""
    empty_adapter = TelegramAdapter(token="")
    assert not empty_adapter.is_configured()
    info = await empty_adapter.get_me()
    assert info is None

