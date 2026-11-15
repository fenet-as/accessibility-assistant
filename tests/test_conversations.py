"""Conversation persistence API (device-owned via X-Owner-Id)."""

from __future__ import annotations


def test_conversation_crud_and_messages(client):
    headers = {"X-Owner-Id": "device-test-owner-1"}
    created = client.post(
        "/api/conversations",
        json={"course_id": "course:va-1", "language": "en", "title": "New chat"},
        headers=headers,
    )
    assert created.status_code == 200
    conv = created.json()
    assert conv["id"].startswith("conv_")
    assert conv["owner_id"] == "device-test-owner-1"
    assert conv["title"] == "New chat"

    listed = client.get("/api/conversations", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert any(c["id"] == conv["id"] for c in body["conversations"])
    assert "groups" in body

    turned = client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={
            "user_message": "What is a virtual assistant?",
            "assistant_message": "A VA supports clients remotely.",
            "language": "en",
            "provider": "faq",
            "answer_source": "local",
            "source_type": "faq",
            "cache_hit": False,
            "citations": [{"title": "VA", "section": "Intro", "url": "#"}],
        },
        headers=headers,
    )
    assert turned.status_code == 200
    turn = turned.json()
    assert turn["user"]["role"] == "user"
    assert turn["assistant"]["role"] == "assistant"
    assert turn["conversation"]["title"].startswith("What is a virtual assistant")

    got = client.get(f"/api/conversations/{conv['id']}", headers=headers)
    assert got.status_code == 200
    detail = got.json()
    assert len(detail["messages"]) == 2

    renamed = client.patch(
        f"/api/conversations/{conv['id']}",
        json={"title": "VA basics"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "VA basics"

    search = client.get("/api/conversations", params={"q": "VA basics"}, headers=headers)
    assert search.status_code == 200
    assert any(c["id"] == conv["id"] for c in search.json()["conversations"])

    other = client.get(f"/api/conversations/{conv['id']}", headers={"X-Owner-Id": "someone-else"})
    assert other.status_code == 404

    deleted = client.delete(f"/api/conversations/{conv['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/conversations/{conv['id']}", headers=headers).status_code == 404


def test_conversations_require_owner_header(client):
    assert client.get("/api/conversations").status_code == 400
    assert client.post("/api/conversations", json={}).status_code == 400
