"""
Post reference clips to a running server and record upload / Whisper timings.

Usage:
  # server must be running, e.g. uvicorn assistant.api.main:app --port 8000
  python -m evaluation.voice_latency --base http://127.0.0.1:8000

Reads clips from evaluation/stt_reference/<lang>/ when present; otherwise skips
with an honest "not measured" note.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

ROOT = Path(__file__).resolve().parents[1]
REF_ROOT = Path(__file__).resolve().parent / "stt_reference"
REPORT_PATH = Path(__file__).resolve().parent / "VOICE_LATENCY_REPORT.md"
AUDIO_EXTS = (".webm", ".wav", ".ogg", ".mp3", ".m4a")


def discover() -> List[Path]:
    clips: List[Path] = []
    if not REF_ROOT.exists():
        return clips
    for path in sorted(REF_ROOT.rglob("*")):
        if path.suffix.lower() in AUDIO_EXTS:
            clips.append(path)
    return clips


def mime_for(path: Path) -> str:
    return {
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
    }.get(path.suffix.lower(), "audio/webm")


def run(base: str) -> str:
    clips = discover()
    lines = [
        "# Voice Latency Report",
        "",
        f"Base URL: `{base}`",
        "",
    ]
    if not clips:
        lines += [
            "No reference clips under `evaluation/stt_reference/`. Latency **not measured**.",
            "",
        ]
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        return "\n".join(lines)

    rows: List[Dict[str, Any]] = []
    with httpx.Client(base_url=base.rstrip("/"), timeout=60.0) as client:
        health = client.get("/api/health")
        lines.append(f"Health: HTTP {health.status_code}")
        if health.status_code == 200:
            speech = (health.json() or {}).get("speech") or {}
            lines.append(f"Server STT: `{speech.get('server_stt')}` provider=`{speech.get('provider')}`")
        lines.append("")

        for clip in clips:
            lang = clip.parent.name if clip.parent.name else "auto"
            payload = clip.read_bytes()
            started = time.perf_counter()
            try:
                res = client.post(
                    "/api/transcribe",
                    files={"audio": (clip.name, payload, mime_for(clip))},
                    data={"language": lang},
                )
                total_ms = round((time.perf_counter() - started) * 1000, 1)
                body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                timings = body.get("timings") or {}
                rows.append({
                    "path": str(clip.relative_to(ROOT)),
                    "bytes": len(payload),
                    "http": res.status_code,
                    "client_total_ms": total_ms,
                    "server_total_ms": timings.get("total_ms"),
                    "whisper_ms": timings.get("whisper_ms"),
                    "receive_ms": timings.get("receive_ms"),
                    "ok": res.status_code == 200,
                })
            except Exception as exc:  # noqa: BLE001
                rows.append({
                    "path": str(clip.relative_to(ROOT)),
                    "bytes": len(payload),
                    "http": 0,
                    "client_total_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": str(exc),
                    "ok": False,
                })

    ok_rows = [r for r in rows if r.get("ok")]
    lines.append("## Summary")
    lines.append("")
    if not ok_rows:
        lines.append("No successful transcriptions. See detail below.")
    else:
        totals = [r["client_total_ms"] for r in ok_rows]
        whisper = [r["whisper_ms"] for r in ok_rows if r.get("whisper_ms") is not None]
        sizes = [r["bytes"] for r in ok_rows]

        def pct(vals: List[float], p: float) -> float:
            if not vals:
                return float("nan")
            ordered = sorted(vals)
            idx = min(len(ordered) - 1, int(len(ordered) * p))
            return ordered[idx]

        lines.append(f"- Clips OK: {len(ok_rows)} / {len(rows)}")
        lines.append(f"- Upload size bytes: mean={statistics.mean(sizes):.0f} p50={pct(sizes, 0.5):.0f}")
        lines.append(
            f"- Client total ms: mean={statistics.mean(totals):.1f} "
            f"p50={pct(totals, 0.5):.1f} p95={pct(totals, 0.95):.1f}"
        )
        if whisper:
            lines.append(
                f"- Whisper ms: mean={statistics.mean(whisper):.1f} "
                f"p50={pct(whisper, 0.5):.1f} p95={pct(whisper, 0.95):.1f}"
            )
    lines += ["", "## Detail", "", "```json", json.dumps(rows, indent=2), "```", ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(run(args.base))
    print(f"\nWrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
