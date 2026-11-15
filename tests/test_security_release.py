"""Milestone 9: security headers, no secrets in frontend, health honesty."""

from pathlib import Path

from assistant.config import PACKAGE_DIR


def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("referrer-policy")


def test_widget_contains_no_api_keys():
    widget_dir = PACKAGE_DIR / "widget"
    forbidden = ("sk-", "AIza", "GEMINI_API_KEY", "OPENAI_API_KEY", "WHISPER_API_KEY", "TELEGRAM_BOT_TOKEN")
    for path in widget_dir.glob("*.js"):
        if path.name.endswith(".min.js"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, f"{path.name} must not contain {token}"


def test_health_reports_dependencies_honestly(client):
    body = client.get("/api/health").json()
    assert body["status"] == "healthy"
    assert "kb_version" in body
    assert "speech" in body
    assert "rate_limit" in body
    assert "usage" in body
    assert body["connectivity"]["backend"] == "ok"
    assert "gemini" in body["ai"]
    assert body["services"]["backend"] == "ok"
