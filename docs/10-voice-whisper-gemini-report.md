# Voice, Whisper, Gemini and Chat — Final Report

## Root causes (Phase 1)

1. **Slow mic startup** — `probeServerStt().finally(initVoiceInput)` blocked the click handler on `/health`; every press re-opened `getUserMedia`.
2. **Lost audio on pause** — no pause/resume; second click stopped and uploaded; `audioChunks = []` on every start.
3. **Upload race** — `stopListening()` at end of transcription could cancel a newer recording.
4. **Whisper blocked chat** — sync OpenAI SDK inside `async` `/api/transcribe` stalled the event loop; new client per request.
5. **Weak Gemini answers** — local `.env` often had `AI_PROVIDER=faq`; `max_output_tokens=250`; follow-ups only expanded below high confidence; no language-switch intent.
6. **UI honesty** — fallback answers labeled "cloud"; no submit guard, copy/retry/regenerate, or TTS pause controller.

## Files modified / added

| Area | Files |
|------|-------|
| Recording engine | `assistant/widget/voice-recorder.js` (new), `assistant/widget/assistant.js`, `shell.html`, `sw.js` |
| Whisper | `assistant/infrastructure/speech.py`, `assistant/api/routers/speech.py`, `assistant/config.py`, `assistant/infrastructure/usage.py` |
| Gemini / tutor | `assistant/services/tutor.py`, `assistant/infrastructure/providers/gemini.py`, `assistant/infrastructure/token_budget.py`, `assistant/domain/models.py` |
| Tests | `tests/js/voice_recorder.test.mjs`, `tests/test_voice_recorder_js.py`, `tests/test_speech.py`, `tests/test_followup_language.py` |
| Evaluation | `evaluation/stt_wer.py`, `evaluation/voice_latency.py`, `evaluation/stt_reference/README.md`, `evaluation/STT_REPORT.md` |
| Docs | `docs/08-voice-test-notes.md`, `docs/10-voice-whisper-gemini-report.md`, `.env.example` |

## Improvements

- VoiceRecorder state machine with pause/resume, persistent sequenced chunks, permission guard, level meter, 60s active-time limit.
- Mic wired immediately; `/health` probe is background-only.
- Whisper via `run_in_threadpool`, shared OpenAI client + timeout, `verbose_json` detected language, typed errors, `timings` + `Server-Timing`, STT usage metrics.
- Review panel: edit / replay / retry / send; blob kept until discard.
- Language-switch follow-ups; always expand short follow-ups; `regenerate` bypasses cache; output tokens default 600; history trim 6 turns / 600 tokens.
- Typing indicator, submit guard, copy / regenerate, fallback badge, TTS play/pause/resume/stop with no overlap; mic disabled offline.

## Before / after metrics

| Metric | Before | After |
|--------|--------|-------|
| Mic click blocked on `/health` | Yes | No |
| Pause/resume keeps audio | No | Yes (Node suite) |
| `/api/chat` during Whisper | Blocked (sync SDK) | Concurrent (`run_in_threadpool`; pytest asserts health &lt; 0.3s during 350ms fake Whisper) |
| Transcribe response timings | Absent | `timings` + `Server-Timing` |
| Fallback badge | Shown as cloud | `fallback` class + label |
| Max output tokens (default) | 250 | 600 |

Client mic-ready / upload timings are logged to the browser console as `[alx-voice] timings` during real use. Aggregate latency requires reference clips + running server (`python -m evaluation.voice_latency`).

## Accuracy by language

See `evaluation/STT_REPORT.md`. **All languages: not measured** until human-recorded clips exist under `evaluation/stt_reference/<lang>/`. No fabricated WER/CER.

## Automated tests

- **213 passed** (`pytest tests/ -m "not live"`), plus Node VoiceRecorder **9/9**.
- Live Whisper / Gemini tests run only when credentials and clips/keys are present; otherwise skipped with an explicit reason.

## Manual tests

Checklist in `docs/08-voice-test-notes.md` — fill after a browser pass on the demo machine.

## Limitations

- WER/CER needs native-speaker recordings (not generated).
- ti/om still use Whisper auto-detect (no dedicated language id).
- TTS quality depends on OS voices; unsupported languages show an honest message.
- Cloud Whisper and Gemini do not work offline (explicitly disabled / labeled).

## Environment variables

`OPENAI_API_KEY` / `WHISPER_API_KEY`, `STT_TIMEOUT_SECONDS`, `AI_PROVIDER=cloud`, `GEMINI_API_KEY`, `MAX_OUTPUT_TOKENS`, `STT_MAX_BYTES`, `STT_MAX_SECONDS`.

**Action for demos:** set `AI_PROVIDER=cloud` in `.env` (do not commit secrets).

## Real API coverage

| Feature | Real API exercised in CI/local? |
|---------|----------------------------------|
| Whisper | Only with key + human clip (`-m live` / `stt_wer`) |
| Gemini | Only with `GEMINI_API_KEY` and `AI_PROVIDER=cloud` |
| Recording engine | Fake MediaRecorder in Node (no browser mic in CI) |
