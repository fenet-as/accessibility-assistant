# 01 – Architecture & Decisions

*Status: design agreed, nothing built yet. Reflects decisions D1–D7 below. Savanna-specific details will be revised after the kick-off starter project.*

## 1. Shape of the system

One backend core, three thin channel adapters, and swappable providers behind clean interfaces.

```
  Web widget (script tag, Shadow DOM) ─┐
  Telegram bot adapter ─────────────────┼─►  Core service (FastAPI)
  SMS adapter (real gateway or simulator) ┘        │
                                                    ├─ Conversation router: course | jobs | human
                                                    ├─ Retrieval (keyword, then embeddings)
                                                    ├─ AI provider: cloud | local | offline FAQ
                                                    ├─ Speech provider: browser | server
                                                    ├─ Jobs, alerts, accommodation requests
                                                    ├─ Escalation (staff Telegram group + Jitsi link)
                                                    └─ SQLite (anonymous sessions, no personal data)
```

**Design rule:** every channel sends the same normalised message to the core and receives the same structured reply (text, citations, status, suggested actions). Each adapter only formats that reply for its channel.

## 2. Decisions

| ID | Decision | Choice | Why | Revisit when |
| --- | --- | --- | --- | --- |
| D1 | Backend | **FastAPI (Python)** | Team lead knows Python; best fit for RAG and local models; free OpenAPI docs | Teammates are formed |
| D2 | Widget | **Vanilla JS or Lit, Shadow DOM web component** | Small bundle for 3G; CSS isolation from Bootstrap on Savanna | Starter project shows a conflicting embed model |
| D3 | Retrieval | **Keyword baseline first, then multilingual embeddings** | Baseline works offline; embeddings needed for Amharic question to English passage | After testing on real Amharic questions |
| D4 | AI provider | **Interface with three implementations; cloud for demo, live switch to offline FAQ** | Meets pluggable-AI requirement without lock-in | Cloud free tier and data terms checked |
| D5 | Human handoff | **Escalation posts to a staff Telegram group; Jitsi room link, learner starts sharing** | Cheap, learner-controlled, no custom signalling | Jitsi embedding/auth behaviour verified; organizers name the support team |
| D6 | Storage | **SQLite, anonymous session IDs, no personal data** | Minimum data collection; zero running cost | Hardening sprint scaling needs |
| D7 | Job data | **Hand-made sample jobs as schema.org/JobPosting JSON-LD** | Real source unknown; JSON-LD earns Level 3 interoperability | Organizers provide a job source |

**Still open:** which cloud LLM to use as the demo default; which embedding model; SMS gateway; whether the embed host exposes course content by API.

## 3. Repository layout (monorepo)

```
assistant/
  widget/        Shadow DOM web component, built to assistant.js
  api/           FastAPI app, routes, OpenAPI spec
  core/          router, retrieval, providers (llm, speech), grounding rules
  adapters/      telegram/, sms/ (gateway + simulator)
  ingest/        course and job content to chunks
  data/          sample course content, sample jobs, offline FAQ (am + en)
  tests/         unit, API, accessibility (axe-core via Playwright)
  docs/          these documents, install guide, WCAG report, licence
```

## 4. Cross-cutting rules

- **Configuration by environment variables.** One setting picks the AI provider (for example `AI_PROVIDER=cloud|local|faq`). No keys in the repo.
- **No provider-specific code outside its adapter.** If swapping providers requires editing core logic, the design has failed.
- **Language handling:** every message carries a language tag (`am` or `en`); the widget sets `lang` and `dir` accordingly.
- **Graceful degradation order:** cloud AI, then local model, then offline FAQ, then "connect me to a human".
- **Honest status:** the system reports what it did (`answered`, `not_found`, `needs_human`) instead of guessing.

## 5. What changes at kick-off

The real Savanna starter project and documentation replace assumptions drawn from the static pages. Expect to adjust: the embed method, authentication, how course content is read, and whether LTI is practical. The core, providers and channel adapters should not need to change.
