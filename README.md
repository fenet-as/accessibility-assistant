# ALX Accessibility Assistant & Live Help

> **Track 3: Multilingual Assistant and Live Help** · ALX Digital Bridge Accessibility Hackathon 2026
> A drop-in, WCAG 2.2 AA assistant for Savanna: grounded Amharic/English tutoring, one-click human help, Telegram and SMS channels, and a career gateway.

## What it does

| Requirement | How it is met |
|---|---|
| Amharic + English tutor, text and voice | Ethiopic detection, browser speech input and read-aloud in the widget |
| Answers only from course content, with citations | BM25 retrieval + rejection threshold; out-of-scope questions return `not_found` and offer a human |
| Web embed, Telegram, low-bandwidth SMS | `<alx-assistant>` Shadow DOM widget, Telegram webhook/poller, SMS endpoint with 160/70-char segmenting |
| Accessible chat | `role="log"` live region, `lang`/`dir` per message, full keyboard use, Escape restores focus |
| One-click human help, learner-controlled screen share | `/api/escalate` creates a logged ticket and an unguessable Jitsi room the learner opens themselves |
| Pluggable AI | `AI_PROVIDER=faq` (offline, free) or `cloud` (Gemini, auto-falls back to offline) |
| Career gateway | schema.org/JobPosting feed, job alerts, interview accommodation requests (no disclosure required) |
| Extra credit | Simple Mode; teacher analytics with no learner identities |
| Integration levels | L1 script tag, L2 REST + OpenAPI (`/docs`), L3 JobPosting JSON-LD and an LTI 1.3 manifest |

## Run it

**Local (Windows PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env          # optional: defaults run fully offline
python -m uvicorn assistant.api.main:app --reload --port 8000
```

macOS/Linux: `source venv/bin/activate` and `cp .env.example .env`.

**Docker (what judges should use)**

```bash
docker compose up --build                        # API + widget on http://localhost:8000
docker compose --profile telegram up --build     # also run the Telegram bot
```

**Other commands**

```bash
python -m pytest                        # full test suite
python -m assistant.ingest              # rebuild chunks.json from the Savanna concept page
python -m assistant.channels.telegram   # Telegram bot via long-polling (needs TELEGRAM_BOT_TOKEN)
```

## Where to click

| URL | What |
|---|---|
| http://localhost:8000/ | Savanna lesson with the assistant embedded |
| http://localhost:8000/a11y-audit | Live axe-core WCAG 2.2 AA gate |
| http://localhost:8000/docs | OpenAPI (Level 2) |
| http://localhost:8000/sms-simulator | Feature-phone SMS simulator |
| http://localhost:8000/analytics | Teacher analytics (anonymous) |
| http://localhost:8000/admin/ingest | Add, test and delete courses |

## Architecture

Clean architecture: dependencies point inwards, and every channel goes through the same services.

```
              Web widget        Telegram        SMS gateway / simulator
                   │                │                    │
   api/ (FastAPI routers)     channels/telegram.py  channels/sms.py      ← delivery: HTTP + channel formats
                   └────────────────┼────────────────────┘
                              container.py                              ← composition root, built once
                                    │
   services/  tutor · escalation · careers · analytics · course_admin   ← use cases
                                    │
   domain/    models · messages (am/en) · language · ports (AIProvider) ← pure, no I/O
                                    ▲
   infrastructure/  retrieval (BM25) · chunk_store · database (SQLite) · providers (faq, gemini)
```

```
accessibility-assistant/
├── assistant/
│   ├── config.py              typed settings from env / .env
│   ├── container.py           wires every service once (shared by API, Telegram, SMS)
│   ├── domain/                entities, bilingual copy, language detection, AIProvider interface
│   ├── services/              tutor (+ answer cache), escalation, careers, analytics, course_admin
│   ├── infrastructure/        BM25 index, chunk store, SQLite, AI providers
│   ├── ingest/                Markdown/HTML parsers, Savanna page parser, `python -m assistant.ingest`
│   ├── channels/              sms.py, telegram.py
│   ├── api/                   app factory, routers/, schemas, dependencies, pages/ (HTML tools)
│   ├── widget/                assistant.js (drop-in web component), axe.min.js
│   └── data/                  chunks.json, jobs.json, faq_translations.json (SQLite db created at runtime)
├── tests/                     pytest suite; runs against a temp DB and a copy of chunks.json
├── savanna-static/            ALX's frozen Savanna pages (host for the widget)
├── docs/                      design docs, WCAG 2.2 AA report
├── Dockerfile, docker-compose.yml
└── requirements.txt, requirements-dev.txt, .env.example
```

### Built for 3,000+ concurrent learners

- **Several workers, one source of truth.** Run `WEB_CONCURRENCY` uvicorn workers. When a course is ingested, every worker notices that `chunks.json` changed and rebuilds its index on its next request. Writes are atomic, so no worker ever reads a half-written file.
- **Fast retrieval.** The BM25 index is an inverted index built once per corpus version, so a query only touches documents that contain its terms. The index is replaced in one step, never edited in place.
- **No answer cache (for now).** Every answer is retrieved and generated fresh, so it always reflects the current knowledge base. A cache keyed by `kb_version` can be added once retrieval quality is settled.

### Offline-first chatbot

- **Service Worker** (`/widget/sw.js`) caches the widget shell, `assistant.js`, `offline.js`, fonts/UI assets and course packs. Chat and escalate stay network-only.
- **Course packs** (`GET /api/offline/pack?scope=…`) ship chunks, the same BM25 index the server uses, languages, UI strings and system messages. `kb_version` / pack format drive cache invalidation (`GET /api/offline/pack/meta`).
- **IndexedDB** (via `offline.js`) stores packs, conversation history, unanswered questions and pending sync items with dedupe keys.
- **Offline answers** are extractive/local only — never cloud AI. Unknown questions return `not_found` and can be queued; syncing queued personal questions requires explicit consent on reconnect.
- **UI** shows Online / Offline / Synchronizing, Local answer vs Cloud answer badges, and Download for offline (with quota errors handled).

### Multilingual engine (en, am, ti, om, so, ar)

- **One config** in `assistant/domain/language.py`: names, scripts (Ethiopic / Latin / Arabic), direction, speech tags, marker words and UI copy. Exposed as `GET /api/languages`.
- **Detection with confidence** mixes script ratios and distinctive words (so Amharic vs Tigrinya, or English vs Oromo/Somali, are not decided by Unicode alone). The widget language picker overrides detection and is sent as `language` on `/api/chat`.
- **Widget** localizes launcher, placeholders, buttons, loading and errors; sets `dir="rtl"` for Arabic; loads `Noto Sans Ethiopic` and `Noto Sans Arabic`. Voice input and read-aloud check browser support and show a note when a language has no speech service; typing always remains available.
- **Offline answers** use curated translations in `faq_translations.json` / chunk `translations`. Missing translations are never invented: the original course text is shown with a clear notice. Cloud translation APIs are not called in offline (`faq`) mode.

### Knowledge base and retrieval

- **Schema v2** (`assistant/domain/knowledge.py`). Each chunk is one section of one lesson of one course: `scope` (course id), `course`, `lesson_id`, `title` (lesson), `section`, `anchor`, `url`, `language`, `text`, `translations` (`{"am": ...}`), `keywords_en`/`keywords_am`, `synonyms`, `content_hash` and `revision`. The file also records `kb_version`, a hash of every chunk, shown in `/api/health`. Old list-format files still load.
- **Ingestion** validates every chunk before anything is indexed (a 400 lists all problems), drops sections that repeat earlier content, keeps anchors unique (`#topic`, `#topic-2`) and uses stable ids (`course--lesson--anchor`). Re-sending a lesson only rewrites what changed, bumps `revision` on edited sections and leaves other lessons and courses alone. `DELETE /api/admin/courses/{course}/lessons/{lesson}` removes one lesson.
- **Ranking** keeps BM25 and adds coverage, section/lesson title, keyword and synonym, and exact-phrase signals. Course and lesson filters (`scope`, optional `lesson` in `/api/chat`) choose candidates before scoring. Amharic text keeps every Ethiopic letter, splits on Ethiopic punctuation, merges homophone letters (ሥ/ስ, ሐ/ኀ/ሀ, ዐ/አ, ፀ/ጸ) and strips common prefixes and suffixes.
- **Confidence.** At 0.6 or above the assistant answers. Between 0.35 and 0.6 it widens retrieval and answers only if several sections together cover the question; otherwise it returns `needs_clarification` with suggested sections. Below 0.35 it returns `not_found` and offers a human tutor. Only the selected passages (at most 3) reach the AI provider, and only the sections actually used are cited.
- **Evaluation.** `python -m evaluation.run` compares the previous engine with the current one on `evaluation/dataset.json` and writes [`evaluation/REPORT.md`](evaluation/REPORT.md). `tests/test_retrieval_evaluation.py` fails if quality drops.
- **Non-blocking analytics.** Web chat logs happen in a background task after the response is sent. SQLite runs in WAL mode with a busy timeout, so readers never block the writer.
- **3G-friendly.** GZip on JSON and on the widget script.
- **Next steps beyond one host:** replace `infrastructure/database.py` with Postgres (same method names), move `chunks.json` to object storage or a database, put a CDN in front of `/widget`, and add per-session rate limiting at the reverse proxy.

### Privacy and security

- Session ids are SHA-256 hashed before storage, so phone numbers and Telegram chat ids are never stored in readable form.
- Learner text is escaped before it is rendered in Telegram HTML, the analytics dashboard and the SMS simulator.
- Course management (`/api/admin/*`) requires the `X-Admin-Token` header when `ADMIN_TOKEN` is set.
- Screen sharing never starts automatically: the learner confirms, then opens the room themselves.

## Configuration

Every setting is optional. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `faq` | `faq` offline, or `cloud` (Gemini with offline fallback) |
| `GEMINI_API_KEY` | – | Required for `cloud` |
| `ADMIN_TOKEN` | – | Protects course ingestion and deletion |
| `CORS_ORIGINS` | `*` | Sites allowed to embed the widget |
| `WEB_CONCURRENCY` | `4` | Worker processes (Docker) |
| `TELEGRAM_BOT_TOKEN` | – | Enables the Telegram channel |
| `JITSI_BASE_URL` | `https://meet.jit.si` | Public or self-hosted Jitsi |
| `DATABASE_PATH`, `CHUNKS_PATH` | `assistant/data/…` | Storage locations |

## Embedding (Level 1)

```html
<script src="https://YOUR-HOST/widget/assistant.js"
        data-api="https://YOUR-HOST/api" data-lang="auto" data-source="course:va-1" defer></script>
```

See [INSTALL.md](INSTALL.md) for REST examples and the LTI 1.3 manifest.

## Accessibility gate

axe-core 4.10 runs against the widget and its Shadow DOM at `/a11y-audit`. The current result is 0 critical and 0 serious issues. The WCAG 2.2 AA conformance report is in [docs/WCAG_2.2_AA_Report.md](docs/WCAG_2.2_AA_Report.md). Manual checks with NVDA, TalkBack, keyboard only and 200% zoom must still be repeated with the co-designer before submission.

## License

Submitted to the ALX Digital Bridge Accessibility Hackathon 2026, under the open licence ALX names at kick-off.
