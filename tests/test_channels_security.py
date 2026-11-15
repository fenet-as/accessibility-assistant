"""Milestone 7: webhook secret, escalation notify, SMS segmentation, log redaction."""

from unittest.mock import MagicMock, patch

from assistant.channels.sms import split_segments
from assistant.services.analytics import redact_question
from assistant.services.escalation import EscalationService


def test_telegram_webhook_rejects_bad_secret(container):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from assistant.api.app import create_app
    from assistant.container import build_container

    settings = replace(container.settings, telegram_webhook_secret="s3cret")
    client = TestClient(create_app(build_container(settings, provider=container.provider)))
    assert client.post("/api/telegram/webhook", json={"update_id": 1}).status_code == 401
    assert client.post(
        "/api/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    ).status_code == 200


def test_staff_notification_uses_staff_chat(tmp_path):
    from assistant.infrastructure.database import Database

    db = Database(tmp_path / "esc.db")
    service = EscalationService(db, "https://meet.jit.si", telegram_bot_token="tok", staff_chat_id="99")
    with patch("assistant.services.escalation.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = MagicMock(status_code=200)
        client_cls.return_value = client
        ticket = service.create("tg-1", language="am", topic="AI")
        assert ticket.status == "open"
        assert client.post.called
        payload = client.post.call_args.kwargs["json"]
        assert payload["chat_id"] == "99"
        assert ticket.ticket_id in payload["text"]


def test_claim_and_close_ticket(tmp_path):
    from assistant.infrastructure.database import Database

    db = Database(tmp_path / "esc.db")
    service = EscalationService(db, "https://meet.jit.si")
    ticket = service.create("s1", language="en")
    claimed = service.claim(ticket.ticket_id, "tutor-a")
    assert claimed and claimed.status == "assigned"
    closed = service.close(ticket.ticket_id)
    assert closed and closed.status == "closed"


def test_amharic_sms_segments_use_70_char_limit():
    text = "ይህ " * 40
    segments = split_segments(text.strip())
    assert len(segments) > 1
    assert all(len(s) <= 70 for s in segments)


def test_question_redaction_masks_phone_and_email():
    assert "[phone]" in redact_question("Call me at +251911223344 please")
    assert "[email]" in redact_question("Reach me at learner@example.com")
    assert redact_question("secret", mode="off") == ""
