# Voice / Whisper / Chat test notes

## Automated

| Suite | Command | Coverage |
|-------|---------|----------|
| VoiceRecorder (Node) | `node --test tests/js/voice_recorder.test.mjs` | pause/resume chunk accumulation, discard, permission guard, illegal transitions |
| Pytest wrapper | `pytest tests/test_voice_recorder_js.py` | runs Node suite when `node` is present |
| Speech API | `pytest tests/test_speech.py` | validation, timings, timeout mapping, event-loop non-blocking, ti/om warning |
| Follow-ups | `pytest tests/test_followup_language.py` | language-switch parser, regenerate cache bypass |
| Live Whisper | `pytest tests/test_speech.py -m live` | requires key + `tests/fixtures/whisper_en.wav` |

## Manual checklist

| Step | Expected | Result |
|------|----------|--------|
| Open widget, click mic before `/health` returns | Recording bar appears; no hang | _(fill after manual pass)_ |
| Pause → speak → resume → pause → stop (3 pauses) | Single transcript; no lost audio | |
| Discard mid-recording | Chunks cleared; input restored | |
| Deny mic permission | Clear permission-denied message (no silent Web Speech fallback) | |
| Offline + mic | Mic disabled / network message; no fake Whisper | |
| Review panel: edit, replay, retry, send | Transcript editable; replay uses kept blob | |
| Double-submit Enter | Only one request (Send disabled while in flight) | |
| Fallback answer badge | Shows "Fallback answer", not "Cloud answer" | |
| Regenerate online | Fresh answer; offline shows AI unavailable note | |
| TTS play / pause / stop across bubbles | No overlapping speech; other buttons reset | |

## Accuracy (WER/CER)

Measured only from `evaluation/stt_reference/<lang>/` human clips. See `evaluation/STT_REPORT.md` after `python -m evaluation.stt_wer`.

Languages without clips: **not measured** (never invent a percentage).

## Latency

With the API running and clips present: `python -m evaluation.voice_latency`. See `evaluation/VOICE_LATENCY_REPORT.md`.

## Environment

| Variable | Role |
|----------|------|
| `OPENAI_API_KEY` / `WHISPER_API_KEY` | Server Whisper |
| `STT_TIMEOUT_SECONDS` | Whisper client timeout (default 30) |
| `AI_PROVIDER=cloud` | Enable Gemini (set in `.env`; do not leave as `faq` for demos) |
| `GEMINI_API_KEY` | Gemini answers |
| `MAX_OUTPUT_TOKENS` | Default 600 |

## Real API testing status

| Feature | Tested with real API? |
|---------|----------------------|
| Whisper | Only when key + human clip exist (`-m live` / `stt_wer`) |
| Gemini | Only when `GEMINI_API_KEY` set and `AI_PROVIDER=cloud` |
| Offline pack / FAQ | Unit + offline path (no cloud claim) |
