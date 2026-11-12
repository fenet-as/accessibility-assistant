# 07 – Task Backlog & Implementation Tracker

*ALX Digital Bridge Accessibility Hackathon 2026 · Track 3: Multilingual Assistant and Live Help*

This backlog translates `docs/00` through `docs/06` into discrete, testable implementation tasks.
Each task includes clear **Acceptance Criteria (AC)**, **Owner Area**, and **Scoring Impact**.

Status tags:
- `[ ] Planned`
- `[-] In Progress`
- `[x] Done (Tested & Verified)`

---

## Task Overview & Dependency Graph

```
[TASK-00: Repo & CI Setup] 
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
[TASK-01: FastAPI Core & Ingestion]       [TASK-05: Accessible Widget Shell]
       │                                          │
       ▼                                          ▼
[TASK-02: Grounded RAG & Citations]       [TASK-06: Widget Chat Flow & Live ARIA]
       │                                          │
       ├───────────────────┬──────────────────────┤
       ▼                   ▼                      ▼
[TASK-03: Pluggable AI] [TASK-08: Telegram] [TASK-07: Savanna Static Embed Test]
       │                   ▼                      │
       ├───────────────►[TASK-09: SMS Sim]        ▼
       ▼                                    [TASK-11: Human Escalation & Consent Screen Share]
[TASK-04: Level 2 OpenAPI]                        │
       │                                          ▼
       ▼                                    [TASK-12: axe-core & WCAG 2.2 Audit]
[TASK-10: Career Gateway & JobPosting]            │
       │                                          ▼
       └────────────────────────────────────►[TASK-13: Submission & Hardening Packet]
```

---

## Phase 0: Foundation & Walking Skeleton (Pre-Event: Nov 12–13)

### TASK-00: Project Structure, Monorepo Scaffolding & Test Harness
- **Priority:** P0 (Must Have)
- **Target Module:** `root`, `assistant/`, `tests/`
- **Description:** Scaffold the monorepo structure outlined in `doc 01` with Python FastAPI backend, vanilla JS Web Component widget, sample data fixtures, and automated test runners.
- **Acceptance Criteria:**
  1. Directory layout matches `assistant/{widget, api, core, adapters, ingest, data, tests, docs}`.
  2. `requirements.txt` and `pyproject.toml` created with FastAPI, Uvicorn, Pydantic, Pytest, BeautifulSoup4, and python-dotenv.
  3. CI / local test script (`pytest`) runs and passes a basic health check.
  4. Environment configuration handled via `.env.example` (no secrets checked in).
- **Status:** `[x] Done (Tested & Verified)`

---

### TASK-01: Course Content Ingestion & Markdown Chunker
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/ingest/`
- **Description:** Ingest real course HTML from `savanna-static/pages/concept-with-navigation.html` ("The Future of the VA Industry") and chunk into structured semantic passages.
- **Acceptance Criteria:**
  1. Script extracts title, section headings, clean text, and anchor links.
  2. Strips layout/navigation/script boilerplate; keeps clean semantic paragraphs.
  3. Saves structured chunks to `assistant/data/chunks.json` with fields: `id`, `source_title`, `section`, `anchor_url`, `language`, `text`.
  4. Script can re-run via a single CLI command (`python -m assistant.ingest.run`).
- **Status:** `[x] Done (Tested & Verified)`

---

### TASK-02: Grounded RAG Pipeline with Strict Citations & Rejection Rule
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/core/retrieval.py`, `assistant/core/grounding.py`
- **Description:** Implement the core retrieval engine (BM25 keyword search baseline + multilingual scoring) with strict grounding rules. Answers must cite source sections and return `not_found` rather than hallucinating when confidence is low.
- **Acceptance Criteria:**
  1. BM25 search over `chunks.json` returns top-k matching passages with relevance scores.
  2. Grounding engine checks if score exceeds threshold; if below, returns status `not_found` with action `["get_human_help"]`.
  3. Test set of 10 in-scope questions (e.g., "What is shaping the future of VA work?") returns status `answered` with valid citations.
  4. Test set of 5 out-of-scope questions (e.g., "How do I bake a cake?") strictly returns `not_found` with 0 hallucinations.
- **Status:** `[ ] Planned`

---

### TASK-03: Pluggable AI Provider Architecture (Cloud + Offline FAQ Fallback)
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/core/providers/`
- **Description:** Implement `AIProvider` protocol with two swappable drivers:
  1. `CloudProvider` (Gemini API with strict system prompt and temperature 0.0)
  2. `OfflineFAQProvider` (zero-model, instant offline fuzzy match against Amharic & English Q&A)
- **Acceptance Criteria:**
  1. Switching between providers is controlled solely by `AI_PROVIDER=cloud|faq` in `.env`.
  2. System works 100% offline when `AI_PROVIDER=faq` is active (no internet connection required).
  3. Both providers return identical schema: `{status, language, answer, citations, actions}`.
  4. Simple Mode instruction toggle supported (shorter sentences, plain language).
- **Status:** `[ ] Planned`

---

### TASK-04: Level 2 REST API & OpenAPI 3.0 Documentation
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/api/`
- **Description:** Expose FastAPI routes for chat, health, jobs, accommodations, and escalation, generating interactive OpenAPI (Swagger) documentation.
- **Acceptance Criteria:**
  1. `POST /api/chat` validates session, message, language (`am`|`en`), and mode (`normal`|`simple`).
  2. `GET /api/health` returns status and active AI provider.
  3. Interactive Swagger UI accessible at `/docs` with detailed schemas and sample payloads.
  4. CORS configured to allow requests from Savanna static pages.
- **Status:** `[ ] Planned`

---

## Phase 1: Level 1 Web Component & Accessibility Gate (Nov 13–14)

### TASK-05: Shadow DOM Web Component Shell (`assistant.js`)
- **Priority:** P0 (Must Have - Accessibility Gate)
- **Target Module:** `assistant/widget/`
- **Description:** Build the standalone `<alx-assistant>` Web Component using Shadow DOM so it drops into any host page without CSS bleeding.
- **Acceptance Criteria:**
  1. Bundle built as single vanilla JS file (`assistant.js`) with zero runtime dependencies.
  2. Injected via `<script src="assistant.js" data-api="http://localhost:8000/api" defer></script>`.
  3. Floating launcher button: 48x48px target (exceeds 44px WCAG target size), visible focus ring, clear accessible label.
  4. Dialog opens and closes via keyboard (`Escape` closes and restores focus to launcher).
  5. Reflows cleanly at 200% zoom and 320px viewport without clipping or horizontal scroll.
- **Status:** `[ ] Planned`

---

### TASK-06: Accessible Chat Log, ARIA Live Announcements & RTL/Amharic Support
- **Priority:** P0 (Must Have - Accessibility Gate)
- **Target Module:** `assistant/widget/`
- **Description:** Implement message rendering with screen-reader friendly live updates, language switching (Amharic/English), and bidirectional text support.
- **Acceptance Criteria:**
  1. Message log container uses `role="log"` and `aria-live="polite"` with `aria-atomic="false"`.
  2. Incoming assistant message text is announced by screen readers (NVDA/TalkBack) without stealing keyboard focus from input.
  3. Message bubbles dynamically set `lang="am"` or `lang="en"` and `dir="auto"` (supporting RTL for Arabic and Ethiopic script).
  4. Visible citations list rendered under answers as accessible keyboard-focusable anchor links.
  5. Status states ("Thinking...", "Not found in course", Error) announced via text.
- **Status:** `[ ] Planned`

---

### TASK-07: Savanna Static Pages Embed Integration Test
- **Priority:** P0 (Must Have)
- **Target Module:** `savanna-static/pages/concept-with-navigation.html`
- **Description:** Embed `assistant.js` into Savanna's `concept-with-navigation.html` and verify seamless visual and functional coexistence.
- **Acceptance Criteria:**
  1. Single `<script>` tag in `pages/concept-with-navigation.html` mounts the widget cleanly.
  2. Host navigation, hamburger menu, and Bootstrap modals continue functioning with zero console errors.
  3. Widget reads host context (e.g. `data-source="course:va-1"`) and passes it to `/api/chat`.
- **Status:** `[ ] Planned`

---

## Phase 2: Omnichannel Channels & Career Gateway (Nov 14–15)

### TASK-08: Telegram Bot Channel Adapter
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/adapters/telegram/`
- **Description:** Implement Telegram bot adapter routing commands and messages to the shared core service.
- **Acceptance Criteria:**
  1. Supports commands: `/start`, `/lang`, `/help`, `/jobs`, `/human`.
  2. Natural language questions return the same grounded answers and citations as the web widget.
  3. Inline keyboard buttons for quick language switch and "Get Human Help".
  4. Works via local polling during development and webhook in deployment.
- **Status:** `[ ] Planned`

---

### TASK-09: Low-Bandwidth SMS Adapter & Interactive Simulator
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/adapters/sms/`
- **Description:** Build lightweight text adapter for SMS constraints (160 ASCII / 70 Unicode Amharic characters) plus a browser-based SMS simulator.
- **Acceptance Criteria:**
  1. Concise message formatting with numbered menu navigation ("Reply 1 for more, 2 for tutor").
  2. Message chunker that safely splits long replies without cutting Amharic Unicode characters mid-word.
  3. Web-based SMS Simulator page (`/sms-simulator`) showing simulated mobile screen for judge demo.
- **Status:** `[ ] Planned`

---

### TASK-10: Career Gateway & schema.org/JobPosting Integration
- **Priority:** P0 (Must Have - Level 3 Interoperability)
- **Target Module:** `assistant/core/jobs.py`, `assistant/data/jobs.json`
- **Description:** Implement job queries, job alerts, interview accommodation requests, and Level 3 `schema.org/JobPosting` JSON-LD output.
- **Acceptance Criteria:**
  1. `GET /api/jobs` returns jobs compliant with schema.org/JobPosting JSON-LD.
  2. Grounded assistant answers job questions ("What qualifications are needed for Junior VA?").
  3. Job alerts subscription endpoint (`POST /api/subscriptions`) for Telegram & SMS.
  4. Accessible interview accommodation request form (`POST /api/accommodations`) with privacy-first options (extra time, sign language, accessible venue - NO medical disclosures).
- **Status:** `[ ] Planned`

---

## Phase 3: Human Escalation & Privacy-Safe Screen Sharing (Nov 15)

### TASK-11: One-Click Escalation & Learner-Controlled Jitsi Screen Share
- **Priority:** P0 (Must Have)
- **Target Module:** `assistant/core/escalation.py`, `assistant/widget/`
- **Description:** Implement one-click human help escalation that notifies tutors and provides a learner-consented screen sharing session.
- **Acceptance Criteria:**
  1. Clicking "Get Human Help" issues `POST /api/escalate` and returns an anonymous ticket.
  2. Notification dispatched to designated staff Telegram channel or tutor dashboard.
  3. Screen-share consent dialog: explicitly informs learner what is shared, emphasizes learner initiation, and requires explicit click to open Jitsi meeting.
  4. Under no circumstance does screen sharing auto-start without user action.
  5. Fallback path for mobile/TalkBack users who cannot share screen (text describe / photo upload).
- **Status:** `[ ] Planned`

---

## Phase 4: Verification, Accessibility Audit & Submission (Nov 15)

### TASK-12: Automated axe-core Testing & WCAG 2.2 AA Audit Report
- **Priority:** P0 (Mandatory Gate)
- **Target Module:** `tests/test_accessibility.py`, `docs/WCAG_2.2_AA_Report.md`
- **Description:** Run Playwright + axe-core automated audit on the host page with widget in all states (closed, open, chatting, escalation dialog) and draft the formal conformance report.
- **Acceptance Criteria:**
  1. Automated test reports **0 critical and 0 serious** axe-core violations.
  2. Full manual test protocol verified: keyboard-only navigation, 200% zoom, sound off, high contrast.
  3. Formal WCAG 2.2 AA conformance document drafted and ready for submission packet.
- **Status:** `[ ] Planned`

---

### TASK-13: Submission Packet, Live Demo Script & Adoption Guide
- **Priority:** P0 (Must Have - 25 Points Adoption)
- **Target Module:** `docs/`
- **Description:** Prepare the final submission deliverables: 60-second install guide, OpenAPI export, architecture diagram, co-designer test summary, and pitch script.
- **Acceptance Criteria:**
  1. `INSTALL.md`: step-by-step instructions to embed `assistant.js` on any site in under 60 seconds.
  2. Swagger JSON / OpenAPI 3.0 export verified.
  3. Live demonstration script covering: Amharic voice/text query, grounded citation click, provider swap to offline FAQ, Telegram bot query, and consent screen share.
  4. Honest "Implemented vs Planned" verification matrix.
- **Status:** `[ ] Planned`

---

## Phase 5: Extra Credit Enhancements (Time Permitting)

### TASK-14: Plain-Language "Simple Mode" Toggle
- **Priority:** P1 (Extra Credit)
- **Target Module:** `assistant/core/`, `assistant/widget/`
- **Description:** Add user-toggleable Simple Mode simplifying explanations into short sentences and step-by-step points.
- **Status:** `[ ] Planned`

### TASK-15: Privacy-Preserving Teacher Analytics Dashboard
- **Priority:** P1 (Extra Credit)
- **Target Module:** `assistant/api/`, `assistant/data/`
- **Description:** Aggregated read-only dashboard showing top asked topics and unanswered questions with strict anonymity (k-anonymity threshold to protect learner identities).
- **Status:** `[ ] Planned`

### TASK-16: LTI 1.3 Launch & Configuration Endpoint
- **Priority:** P2 (Nice to Have)
- **Target Module:** `assistant/api/lti.py`
- **Description:** Standard LTI 1.3 config endpoint (`/api/lti/config.json`) and basic OIDC launch handler for LMS platforms.
- **Status:** `[ ] Planned`

