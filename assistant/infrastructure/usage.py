"""In-process AI usage accounting (cache hits, provider calls, approximate tokens)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class UsageCounters:
    cache_hits: int = 0
    cache_misses: int = 0
    provider_requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    faq_answers: int = 0
    cloud_answers: int = 0
    local_answers: int = 0
    estimated_cost_usd: float = 0.0
    fallbacks: int = 0
    fallback_reasons: Dict[str, int] = field(default_factory=dict)
    latency_samples_ms: List[float] = field(default_factory=list)
    stt_success: int = 0
    stt_errors: int = 0
    stt_error_reasons: Dict[str, int] = field(default_factory=dict)
    stt_latency_samples_ms: List[float] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        samples = sorted(self.latency_samples_ms)
        p50 = p95 = None
        if samples:
            p50 = samples[len(samples) // 2]
            p95 = samples[min(len(samples) - 1, int(len(samples) * 0.95))]
        stt_samples = sorted(self.stt_latency_samples_ms)
        stt_p50 = stt_p95 = None
        if stt_samples:
            stt_p50 = stt_samples[len(stt_samples) // 2]
            stt_p95 = stt_samples[min(len(stt_samples) - 1, int(len(stt_samples) * 0.95))]
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "provider_requests": self.provider_requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "faq_answers": self.faq_answers,
            "cloud_answers": self.cloud_answers,
            "local_answers": self.local_answers,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "fallbacks": self.fallbacks,
            "fallback_reasons": dict(self.fallback_reasons),
            "gemini_latency_ms": {"p50": p50, "p95": p95, "samples": len(samples)},
            "stt": {
                "success": self.stt_success,
                "errors": self.stt_errors,
                "error_reasons": dict(self.stt_error_reasons),
                "latency_ms": {"p50": stt_p50, "p95": stt_p95, "samples": len(stt_samples)},
            },
        }


class UsageTracker:
    """Thread-safe counters for observability and hackathon demos."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters = UsageCounters()

    def record_cache_hit(self) -> None:
        with self._lock:
            self._counters.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._counters.cache_misses += 1

    def record_provider_request(self, provider: str) -> None:
        with self._lock:
            self._counters.provider_requests += 1
            if provider == "offline_faq":
                self._counters.faq_answers += 1
            elif provider == "cloud_gemini":
                self._counters.cloud_answers += 1
            elif provider == "local_model":
                self._counters.local_answers += 1

    def record_tokens(self, *, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0) -> None:
        with self._lock:
            self._counters.input_tokens += max(0, input_tokens)
            self._counters.output_tokens += max(0, output_tokens)
            self._counters.estimated_cost_usd += max(0.0, cost_usd)
        # Optional budget sink attached by the composition root.
        sink = getattr(self, "budget_sink", None)
        if sink:
            sink(tokens=max(0, input_tokens) + max(0, output_tokens), cost_usd=max(0.0, cost_usd))

    def record_fallback(self, reason: str) -> None:
        with self._lock:
            self._counters.fallbacks += 1
            key = reason or "unknown"
            self._counters.fallback_reasons[key] = self._counters.fallback_reasons.get(key, 0) + 1

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            samples = self._counters.latency_samples_ms
            samples.append(round(latency_ms, 1))
            if len(samples) > 500:
                del samples[: len(samples) - 500]

    def record_stt_success(self) -> None:
        with self._lock:
            self._counters.stt_success += 1

    def record_stt_error(self, reason: str) -> None:
        with self._lock:
            self._counters.stt_errors += 1
            key = reason or "unknown"
            self._counters.stt_error_reasons[key] = self._counters.stt_error_reasons.get(key, 0) + 1

    def record_stt_latency(self, latency_ms: float) -> None:
        with self._lock:
            samples = self._counters.stt_latency_samples_ms
            samples.append(round(latency_ms, 1))
            if len(samples) > 500:
                del samples[: len(samples) - 500]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._counters.as_dict()
