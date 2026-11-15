"""
WER/CER harness for Whisper accuracy by language.

Expects real human-recorded clips (never fabricated):
  evaluation/stt_reference/<lang>/*.webm|*.wav
  matching sibling *.txt with the reference transcript.

Writes evaluation/STT_REPORT.md. Languages without clips are reported as "not measured".
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
REF_ROOT = Path(__file__).resolve().parent / "stt_reference"
REPORT_PATH = Path(__file__).resolve().parent / "STT_REPORT.md"
SUPPORTED = ("en", "am", "ti", "om", "so", "ar")
AUDIO_EXTS = (".webm", ".wav", ".ogg", ".mp3", ".m4a")


def normalize_text(text: str, language: str) -> List[str]:
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\u1200-\u137F\u0600-\u06FF\s]", " ", text, flags=re.UNICODE)
    return [t for t in text.split() if t]


def levenshtein(a: List[str], b: List[str]) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def char_tokens(text: str) -> List[str]:
    return list(re.sub(r"\s+", "", (text or "").lower()))


def wer(ref: str, hyp: str, language: str) -> float:
    r = normalize_text(ref, language)
    h = normalize_text(hyp, language)
    if not r:
        return 0.0 if not h else 1.0
    return levenshtein(r, h) / len(r)


def cer(ref: str, hyp: str) -> float:
    r = char_tokens(ref)
    h = char_tokens(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return levenshtein(r, h) / len(r)


@dataclass
class ClipResult:
    language: str
    path: str
    reference: str
    hypothesis: str
    wer: float
    cer: float
    error: Optional[str] = None


def discover_clips() -> Dict[str, List[Tuple[Path, Path]]]:
    found: Dict[str, List[Tuple[Path, Path]]] = {lang: [] for lang in SUPPORTED}
    if not REF_ROOT.exists():
        return found
    for lang in SUPPORTED:
        folder = REF_ROOT / lang
        if not folder.is_dir():
            continue
        for audio in sorted(folder.iterdir()):
            if audio.suffix.lower() not in AUDIO_EXTS:
                continue
            ref = audio.with_suffix(".txt")
            if ref.exists():
                found[lang].append((audio, ref))
    return found


def transcribe_clip(audio: Path, language: str, api_key: str) -> str:
    from assistant.infrastructure.speech import transcribe_audio

    mime = {
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
    }.get(audio.suffix.lower(), "audio/webm")
    text, _used, _warn = transcribe_audio(
        audio.read_bytes(),
        filename=audio.name,
        mime_type=mime,
        language_hint=language,
        api_key=api_key,
    )
    return text


def run(api_key: Optional[str] = None) -> str:
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("WHISPER_API_KEY") or ""
    clips = discover_clips()
    results: List[ClipResult] = []
    lines = [
        "# STT Accuracy Report",
        "",
        "Accuracy is measured only for languages with human-recorded reference clips.",
        "No fabricated audio or invented WER percentages.",
        "",
    ]

    any_clips = any(clips[lang] for lang in SUPPORTED)
    if not any_clips:
        lines += [
            "## Status",
            "",
            "No reference clips found under `evaluation/stt_reference/<lang>/`.",
            "All languages: **not measured**.",
            "",
            "To measure: add `clip.webm` + `clip.txt` per language, set `OPENAI_API_KEY`, then run:",
            "",
            "```",
            "python -m evaluation.stt_wer",
            "```",
            "",
        ]
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        return "\n".join(lines)

    if not key:
        lines += [
            "## Status",
            "",
            "Reference clips exist but `OPENAI_API_KEY` / `WHISPER_API_KEY` is not set.",
            "Transcription was **not** run. Accuracy remains **not measured**.",
            "",
        ]
        for lang in SUPPORTED:
            n = len(clips[lang])
            lines.append(f"- **{lang}**: {n} clip(s) on disk, not measured (no API key)")
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "\n".join(lines)

    sys.path.insert(0, str(ROOT))
    for lang in SUPPORTED:
        for audio, ref_path in clips[lang]:
            reference = ref_path.read_text(encoding="utf-8").strip()
            try:
                hyp = transcribe_clip(audio, lang, key)
                results.append(
                    ClipResult(
                        language=lang,
                        path=str(audio.relative_to(ROOT)),
                        reference=reference,
                        hypothesis=hyp,
                        wer=wer(reference, hyp, lang),
                        cer=cer(reference, hyp),
                    )
                )
            except Exception as exc:  # noqa: BLE001 — report per-clip failure honestly
                results.append(
                    ClipResult(
                        language=lang,
                        path=str(audio.relative_to(ROOT)),
                        reference=reference,
                        hypothesis="",
                        wer=1.0,
                        cer=1.0,
                        error=str(exc),
                    )
                )

    lines.append("## Per-language summary")
    lines.append("")
    lines.append("| Language | Clips | Mean WER | Mean CER | Notes |")
    lines.append("|----------|------:|---------:|---------:|-------|")
    for lang in SUPPORTED:
        lang_results = [r for r in results if r.language == lang]
        if not lang_results and not clips[lang]:
            lines.append(f"| {lang} | 0 | — | — | not measured |")
            continue
        if not lang_results:
            lines.append(f"| {lang} | {len(clips[lang])} | — | — | not measured |")
            continue
        mean_wer = sum(r.wer for r in lang_results) / len(lang_results)
        mean_cer = sum(r.cer for r in lang_results) / len(lang_results)
        errors = sum(1 for r in lang_results if r.error)
        note = f"{errors} error(s)" if errors else "measured"
        lines.append(
            f"| {lang} | {len(lang_results)} | {mean_wer:.3f} | {mean_cer:.3f} | {note} |"
        )

    lines += ["", "## Per-clip detail", ""]
    for r in results:
        lines.append(f"### `{r.path}`")
        lines.append(f"- WER: {r.wer:.3f}  CER: {r.cer:.3f}")
        if r.error:
            lines.append(f"- Error: {r.error}")
        else:
            lines.append(f"- Reference: {r.reference}")
            lines.append(f"- Hypothesis: {r.hypothesis}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute Whisper WER/CER from reference clips")
    parser.add_argument("--api-key", default="", help="Override OPENAI_API_KEY")
    args = parser.parse_args()
    print(run(api_key=args.api_key or None))
    print(f"\nWrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
