# 01 – Architecture & Decisions

*Status: implemented. Code layout and scaling notes are summarised in the README; this document records why.*

## 1. Shape of the system

One set of services, thin delivery adapters, and swappable infrastructure behind interfaces.

```
  Web widget (script tag, Shadow DOM) ─► api/ routers ─┐
  Telegram (webhook or long-poll) ─────► channels/telegram.py ─┼─► container ─► services ─► domain
  SMS gateway / simulator ─────────────► channels/sms.py ─┘                      │
                                                                       infrastructure (implements domain ports):
                                                                       BM25 index · chunk store · SQLite · AI providers
```

**Dependency rule:** `domain` imports nothing from the app. `services` import `domain` and infrastructure *types*. `api` and `channels` only call `services`. Only `container.py` constructs concrete classes.

**Channel rule:** every channel sends a `ChatRequest` to `TutorService` and gets back a `ChatResponse` (status, answer, citations, actions). The adapter only formats that response for its medium.

## 2. Decisions

| ID | Decision | Choice | Why | Revisit when |
| --- | --- | --- | --- | --- |
| D1 | Backend | FastAPI (Python) | Free OpenAPI docs; good fit for retrieval and local models | – |
| D2 | Widget | Vanilla JS web component, Shadow DOM | No build step, small for 3G, CSS isolated from Savanna's Bootstrap | Starter shows a conflicting embed model |
| D3 | Retrieval | BM25 with bilingual keyword tags, inverted index | Works offline; deterministic; fast enough for thousands of chunks | Amharic-question recall is too low → add multilingual embeddings behind the same `search()` |
| D4 | AI provider | `AIProvider` port; offline FAQ and Gemini implementations | No paid-API lock-in; Gemini degrades to offline on any failure | A local open model is available → add a third implementation |
| D5 | Human handoff | Logged ticket + unguessable Jitsi room; learner opens it | Cheap, learner-controlled, no custom signalling | Organizers name the support team → notify a staff Telegram group from `EscalationService` |
| D6 | Storage | SQLite in WAL mode, hashed session ids | Zero cost, multiple workers on one host, no plain-text identifiers | More than one host → Postgres with the same `Database` methods |
| D7 | Job data | `data/jobs.json` as schema.org/JobPosting | Level 3 interoperability; one source for web, SMS and Telegram | A job source or API is provided |
| D8 | Course corpus | `chunks.json`, atomic writes, version = file mtime | Every worker picks up ingests without a message bus | Large corpora → database or object storage |
| D9 | Scale | Multiple uvicorn workers, in-process LRU answer cache, GZip | Repeated cohort questions served without the AI call; small payloads | Per-host limits reached → horizontal scaling behind a load balancer |

## 3. Cross-cutting rules

- **Configuration only through environment variables** (`assistant/config.py`). No secrets in the repo.
- **Provider-specific code stays in its provider module.** Swapping providers changes `AI_PROVIDER`, not code.
- **Language:** every response carries `am` or `en`; the widget sets `lang` and `dir` on each message.
- **Degradation order:** cloud AI, then offline FAQ, then "connect me to a human".
- **Honest status:** `answered`, `not_found` or `needs_human`, never a guess.
- **Tests never touch real data:** `tests/conftest.py` points the database and corpus at temporary copies.

## 4. What changes when the real Savanna starter arrives

Expect to adjust the embed method, authentication, and how course content is read (a new parser in `ingest/`). Services, domain and channels should not need to change.
