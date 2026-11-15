"""Milestone 6: rate limiter, budget thresholds, inflight dedupe."""

from assistant.infrastructure.rate_limit import RateLimiter


def test_memory_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(session_per_min=2, ip_per_min=100, stt_per_min=2)
    assert limiter.check(session_id="s1", ip="1.1.1.1").allowed
    assert limiter.check(session_id="s1", ip="1.1.1.1").allowed
    blocked = limiter.check(session_id="s1", ip="1.1.1.1")
    assert not blocked.allowed
    assert blocked.retry_after >= 1


def test_stt_limit_is_separate():
    limiter = RateLimiter(session_per_min=100, ip_per_min=100, stt_per_min=1)
    assert limiter.check(ip="2.2.2.2", kind="stt").allowed
    assert not limiter.check(ip="2.2.2.2", kind="stt").allowed


def test_budget_warning_and_exhausted():
    limiter = RateLimiter(daily_token_budget=100)
    limiter.record_budget(tokens=90)
    assert limiter.budget_snapshot()["level"] == "warning"
    limiter.record_budget(tokens=20)
    assert limiter.budget_exhausted()


def test_inflight_dedupe_leader_follower():
    limiter = RateLimiter()
    leader, event = limiter.acquire_inflight("k1")
    assert leader is True and event is not None
    follower, wait = limiter.acquire_inflight("k1")
    assert follower is False and wait is event
    limiter.release_inflight("k1")
    assert wait.is_set()


def test_health_exposes_rate_limit(client):
    body = client.get("/api/health").json()
    assert "rate_limit" in body
    assert body["rate_limit"]["backend"] in ("memory", "redis", "memory_fallback")
