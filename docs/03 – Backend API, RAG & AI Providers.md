# 03 – Backend API, RAG & AI Providers

*Status: Planned. Stack: FastAPI (Python), SQLite. The API contract is the stable part; everything behind it is swappable.*

## 1. REST API (Level 2)

FastAPI generates the OpenAPI spec automatically; we keep it accurate and documented.

| Method & path | Purpose |
| --- | --- |
| `POST /api/chat` | Ask a question; returns answer, citations, status |
| `GET /api/health` | Health check and which AI provider is active |
| `GET /api/jobs` | List or search sample job postings (JobPosting JSON-LD) |
| `POST /api/subscriptions` | Subscribe or unsubscribe a channel to job alerts |
| `POST /api/accommodations` | Submit an interview accommodation request |
| `POST /api/escalate` | Request a human; returns a help request id and next steps |
| `POST /api/telegram/webhook` | Telegram adapter entry point |
| `POST /api/sms/inbound` | SMS adapter entry point (gateway or simulator) |
| `GET /api/analytics/summary` | Aggregated, anonymous topics and unanswered questions (extra credit) |

### Chat request and response

```json
// POST /api/chat
{ "session": "anon-8f3a", "message": "የንግድ አስተካካይ ማን ነው?",
  "language": "am", "mode": "simple", "scope": "course:va-1" }

// response
{ "status": "answered",            // answered | not_found | needs_human
  "language": "am",
  "answer": "...",
  "citations": [ { "title": "The Future of the VA Industry",
                   "section": "Key trends", "url": "...#key-trends" } ],
  "actions": [ "get_human_help" ] }
```

## 2. Content ingestion

1. **Source:** start with the Savanna concept page "The Future of the VA Industry" from the static repo; the real format is confirmed at kick-off.
2. **Parse** HTML into sections by heading; strip navigation, scripts, and layout.
3. **Chunk** each section into short passages, each keeping: source title, section heading, URL with anchor, language, and original text.
4. **Store** chunks and the search index locally. Re-running ingestion must be one command.
5. **Jobs** use a second collection with the same structure, so job questions go through the same pipeline.

## 3. Retrieval

- **Phase A – keyword search (BM25):** works offline, no model download, good for English questions on English content.
- **Phase B – multilingual embeddings:** needed when the learner asks in Amharic and the course is English. We will compare a small open multilingual embedding model against keyword-only on a **test set of 20–30 real questions in both languages** before committing.
- **Fallback for Amharic:** a curated bilingual FAQ (Amharic and English) that always works with no model.
- Risk to track: Amharic tokenisation and quality of small models; do not assume it works until measured.

## 4. Grounding rules (the critical requirement)

1. Answer **only** from retrieved passages. The model receives the passages and a strict instruction to use nothing else.
2. Every answer carries citations pointing at the passages used.
3. If best retrieval score is below a threshold, return `not_found` with a plain message and the option to get a human. **No generated guess.**
4. Treat retrieved text as data, not instructions (guards against prompt injection from content).
5. Log unanswered questions (anonymously) so teachers can see gaps.

## 5. Provider interface (pluggable AI)

Core code depends only on small interfaces:

```python
class AIProvider(Protocol):
    name: str
    def generate(self, question: str, passages: list[Passage],
                 language: str, simple: bool) -> Answer: ...

class Retriever(Protocol):
    def search(self, query: str, language: str, k: int) -> list[Passage]: ...
```

| Provider | Use | Notes |
| --- | --- | --- |
| **Cloud** | Demo default | One vendor behind an adapter; check free-tier limits and data terms |
| **Local open model** | Self-hosted, no per-call cost | Needs hardware; weaker Amharic on small models, to be tested |
| **Offline FAQ** | No network, no model | Matches against curated bilingual Q\&A; always available |

Selection by configuration. A **live switch to the offline FAQ** is part of the demo, to prove no lock-in.

## 6. Simple Mode (extra credit)

A flag on each request that changes the generation instruction: short sentences, plain words, explain unfamiliar terms, break instructions into steps. Same grounding rules apply.

## 7. Voice

- First attempt: browser speech recognition and speech synthesis in the widget (no server cost).
- Amharic support varies by browser and device; **test before promising it**. If unreliable, document the limit and keep text as the full path.
- Server-side speech is a later option and must also sit behind a provider interface.

## 8. Data stored (SQLite)

- Anonymous session id, channel, language, timestamps.
- Chat turns only as needed for the conversation; short retention (to be set).
- Anonymous question topics and `not_found` counts for analytics.
- No names, phone numbers, or emails unless a learner explicitly subscribes to alerts (see doc 04).

## 9. Tests for this part

- Unit tests for chunking, retrieval, grounding threshold, provider switching.
- API tests for every endpoint and status.
- A fixed question set with expected citations, run in CI.
