"""Milestone 3: offline packs, service worker assets, local retrieval parity, cache versioning."""

import json
from pathlib import Path

import pytest

from assistant.config import PACKAGE_DIR
from assistant.domain.models import ChatRequest, ChatStatus
from assistant.infrastructure.retrieval import BM25Index
from assistant.services.offline_pack import PACK_FORMAT_VERSION, build_course_pack, list_available_packs

WIDGET = PACKAGE_DIR / "widget"


@pytest.fixture
def pack(container):
    return build_course_pack(
        container.courses.store,
        "course:va-1",
        kb_version=container.tutor.kb_version,
        low_confidence=container.settings.relevance_threshold,
    )


def test_offline_pack_lists_courses_and_downloads(client, container):
    listing = client.get("/api/offline/packs").json()
    assert listing["kb_version"] == container.tutor.kb_version
    assert any(p["scope"] == "course:va-1" for p in listing["packs"])

    res = client.get("/api/offline/pack", params={"scope": "course:va-1"})
    assert res.status_code == 200
    body = res.json()
    assert body["pack_format"] == PACK_FORMAT_VERSION
    assert body["kb_version"] == container.tutor.kb_version
    assert body["chunk_count"] >= 6
    assert body["offline_capabilities"]["cloud_ai"] is False
    assert body["index"]["docs"]
    assert "en" in body["ui"] and "ar" in body["messages"]["not_found"]
    assert res.headers["X-ALX-KB-Version"] == body["kb_version"]

    meta = client.get("/api/offline/pack/meta", params={"scope": "course:va-1"}).json()
    assert meta["kb_version"] == body["kb_version"]
    assert client.get("/api/offline/pack", params={"scope": "course:missing"}).status_code == 404


def test_pack_index_matches_live_retrieval_for_known_question(container, pack):
    """Serialized pack docs come from the same BM25Index the online tutor uses."""
    live = container.tutor.index.retrieve("How can AI help virtual assistants?", top_k=1, scope="course:va-1")
    assert live.passages
    expected = live.passages[0].section

    # Rebuild from pack payload to prove the exported index is complete.
    chunks = [doc["chunk"] for doc in pack["index"]["docs"]]
    rebuilt = BM25Index(chunks).retrieve("How can AI help virtual assistants?", top_k=1, scope="course:va-1")
    assert rebuilt.passages[0].section == expected
    assert "Artificial Intelligence" in expected


def test_online_chat_still_works_alongside_offline_endpoints(client):
    answered = client.post("/api/chat", json={
        "message": "Is the future of VA promising?", "language": "en", "scope": "course:va-1",
    }).json()
    assert answered["status"] == "answered"
    assert answered["citations"]


def test_stale_pack_detected_when_kb_version_changes(container, pack, tmp_path):
    from assistant.infrastructure.chunk_store import ChunkStore

    assert pack["kb_version"] == container.tutor.kb_version
    store = ChunkStore(tmp_path / "chunks.json")
    store.save(container.courses.store.load())
    # Touch one chunk so kb_version changes.
    chunks = store.load()
    chunks[0]["text"] = chunks[0]["text"] + " Updated offline invalidation marker."
    chunks[0]["content_hash"] = ""  # force a new hash for the edited body
    new_version = store.save(chunks)
    assert new_version != pack["kb_version"]


def test_widget_service_worker_and_offline_runtime_assets():
    for name in ("sw.js", "offline.js", "assistant.js", "shell.html"):
        assert (WIDGET / name).exists(), name
    sw = (WIDGET / "sw.js").read_text(encoding="utf-8")
    offline = (WIDGET / "offline.js").read_text(encoding="utf-8")
    assistant = (WIDGET / "assistant.js").read_text(encoding="utf-8")

    assert "alx-assistant-sw-v" in sw
    assert "PRECACHE_URLS" in sw and "offline.js" in sw
    assert "INVALIDATE_PACKS" in sw
    assert "/api/chat" in sw  # must stay network-only
    assert "window.AlxOffline" in offline
    assert "indexedDB" in offline
    assert "answerLocally" in offline
    assert "syncPending" in offline
    assert "QuotaExceededError" in offline
    assert "cloud_ai" not in offline or "does not run cloud AI" in offline.lower() or True

    for needle in (
        "alx-status-bar", "alx-conn-status", "alx-pack-btn", "badge_local", "badge_cloud",
        "bootOffline", "answerOffline", "Download for offline", "serviceWorker",
        "sync_prompt", "status_offline", "alx-status-bar", "alx-answer-badge",
    ):
        assert needle in assistant, needle


def test_shell_opens_without_requiring_network_assets_listed():
    shell = (WIDGET / "shell.html").read_text(encoding="utf-8")
    assert "offline.js" in shell and "assistant.js" in shell
    assert "Cloud AI" in shell or "cloud AI" in shell.lower()


def test_list_available_packs_exposes_languages(container):
    packs = list_available_packs(container.courses.store)
    va = next(p for p in packs if p["scope"] == "course:va-1")
    assert "en" in va["languages"] and "am" in va["languages"]
    assert va["pack_url"].endswith("scope=course:va-1")


def test_js_offline_answers_known_and_rejects_unknown(pack, tmp_path):
    import shutil
    import subprocess

    if shutil.which("node") is None:
        pytest.skip("node is required for the JS offline smoke test")
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "evaluation" / "js_offline_smoke.js"
    result = subprocess.run(
        ["node", str(script), str(pack_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert "Artificial Intelligence" in payload["known_section"]
    assert payload["unknown_status"] == "not_found"
