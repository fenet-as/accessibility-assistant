"""Telegram and low-bandwidth SMS channels."""

import pytest

from assistant.channels.sms import UNICODE_LIMIT, SMSAdapter, normalize_ethiopian_phone, split_segments
from assistant.channels.telegram import TelegramAdapter


@pytest.fixture
def sms(container):
    return SMSAdapter(container)


@pytest.fixture
def telegram(container):
    adapter = TelegramAdapter(container, token="MOCK_TEST_TOKEN")
    adapter.sent = []
    adapter.answered_callbacks = []

    async def fake_send(chat_id, text, reply_markup=None):
        adapter.sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return True

    async def fake_answer_cb(callback_id, text=None):
        adapter.answered_callbacks.append({"id": callback_id, "text": text})
        return True

    adapter.send_message = fake_send
    adapter.answer_callback_query = fake_answer_cb
    return adapter


def message(text, chat_id=12345):
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def callback(data, chat_id=12345, query_id="cb-default"):
    return {"callback_query": {"id": query_id, "data": data, "message": {"chat": {"id": chat_id}}}}


def test_sms_help_menu(sms):
    segments = sms.handle_inbound_sms("+251911000000", "HELP")
    assert "1: Jobs" in segments[0]
    assert "2: Human Tutor" in segments[0]


def test_sms_jobs_come_from_job_catalog(sms):
    text = " ".join(sms.handle_inbound_sms("+251911000000", "1"))
    assert "Junior VA" in text
    assert "Digital Coordinator" in text


def test_sms_human_request_creates_ticket(sms):
    segments = sms.handle_inbound_sms("+251911000000", "2")
    assert "ticket HELP-" in segments[0]


def test_sms_course_question_cites_section(sms):
    text = " ".join(sms.handle_inbound_sms("+251911000000", "What is shaping the future of virtual assistant work?"))
    assert "Ref:" in text


def test_sms_unicode_splitting():
    amharic = (
        "ሰው ሰራሽ አስተዋይነት (AI) በቨርቹዋል ረዳቶች ሥራ ውስጥ ትልቅ ሚና ይጫወታል። "
        "AI እንደ ኢሜይል መጻፍ፣ ጽሑፎችን ማጠቃለልና መረጃ መፈለግ ያሉ ስራዎችን ያግዛል።"
    )
    segments = split_segments(amharic)
    assert len(segments) >= 2
    assert all(len(s) <= UNICODE_LIMIT for s in segments)


@pytest.mark.anyio
async def test_telegram_start(telegram):
    res = await telegram.handle_update(message("/start"))
    assert res == {"action": "start", "chat_id": 12345}
    assert telegram.sent[0]["reply_markup"] is not None


@pytest.mark.anyio
async def test_telegram_human_escalation(telegram):
    res = await telegram.handle_update(message("/human"))
    assert res["action"] == "human_escalate"
    assert "ALX-Help-" in res["room"]


@pytest.mark.anyio
async def test_telegram_jobs_command_and_button(telegram):
    assert (await telegram.handle_update(message("/jobs")))["action"] == "jobs"
    assert (await telegram.handle_update(callback("jobs_view", query_id="cb-jobs-123")))["action"] == "jobs"
    assert "Junior Virtual Assistant" in telegram.sent[0]["text"]
    assert any(cb["id"] == "cb-jobs-123" for cb in telegram.answered_callbacks)


@pytest.mark.anyio
async def test_telegram_language_choice_is_remembered(telegram):
    await telegram.handle_update(callback("lang_am"))
    res = await telegram.handle_update(message("What is shaping the future of virtual assistant work?"))
    assert res["action"] == "answer"
    assert telegram.sent[-1]["text"].startswith("የቨርቹዋል ረዳት")


@pytest.mark.anyio
async def test_telegram_escapes_learner_text(telegram):
    await telegram.handle_update(message("<b>bake</b> a cake & bread?"))
    assert "<b>bake" not in telegram.sent[-1]["text"]


@pytest.mark.anyio
async def test_telegram_unconfigured_get_me(container):
    adapter = TelegramAdapter(container, token="")
    assert not adapter.is_configured()
    assert await adapter.get_me() is None


def test_sms_ethiopian_phone_normalization():
    assert normalize_ethiopian_phone("0911223344") == "+251911223344"
    assert normalize_ethiopian_phone("0711223344") == "+251711223344"
    assert normalize_ethiopian_phone("251911223344") == "+251911223344"
    assert normalize_ethiopian_phone("+251911223344") == "+251911223344"


def test_sms_inbound_api_universal(client):
    """POST /api/sms/inbound accepts JSON and form webhooks from African gateways."""
    res_json = client.post("/api/sms/inbound", json={"from": "0911223344", "text": "HELP"})
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert data_json["status"] == "success"
    assert data_json["sender"] == "+251911223344"
    assert len(data_json["segments"]) >= 1

    res_form = client.post("/api/sms/inbound", data={"From": "0711223344", "Body": "1"})
    assert res_form.status_code == 200
    data_form = res_form.json()
    assert data_form["status"] == "success"
    assert data_form["sender"] == "+251711223344"
    assert "Junior VA" in data_form["segments"][0]


def test_sms_inbound_telerivet(client):
    """Telerivet uses from_number, content, and expects a messages array in response."""
    res_get = client.get("/api/sms/inbound")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "ok"

    res = client.post("/api/sms/inbound", data={
        "event": "incoming_message",
        "from_number": "+251911998877",
        "content": "HELP",
        "secret": "my_telerivet_secret"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["sender"] == "+251911998877"
    assert "messages" in data
    assert len(data["messages"]) >= 1
    assert "content" in data["messages"][0]
