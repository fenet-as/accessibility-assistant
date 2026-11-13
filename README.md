# ALX Accessibility Assistant & Live Help

> **Track 3: Multilingual Assistant and Live Help**  
> **ALX Digital Bridge Accessibility Hackathon 2026**  
> *A drop-in, zero-dependency, WCAG 2.2 AA compliant AI tutor and career gateway built for Ethiopian learners.*

[![WCAG 2.2 AA Gate](https://img.shields.io/badge/WCAG%202.2%20AA%20Gate-PASSED%20(0%20Violations)-22c55e?style=for-the-badge&logo=w3c)](http://localhost:8000/a11y-audit)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688?style=for-the-badge&logo=fastapi)](http://localhost:8000/docs)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Pluggable AI](https://img.shields.io/badge/AI%20Engine-Gemini%202.5%20%7C%20Offline%20FAQ-orange?style=for-the-badge)](http://localhost:8000/api/health)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Stage 1 Accessibility Gate Status](#stage-1-accessibility-gate-status)
3. [Quick Start & Local Running Instructions](#quick-start--local-running-instructions)
4. [Environment Configuration (.env)](#environment-configuration-env)
5. [Live Application URLs & Endpoints](#live-application-urls--endpoints)
6. [Key Architectural Highlights](#key-architectural-highlights)
7. [Running the Automated Test Suite](#running-the-automated-test-suite)
8. [Omnichannel Channels (SMS & Telegram)](#omnichannel-channels-sms--telegram)
9. [Project Directory Structure](#project-directory-structure)
10. [Submission Packet & Adoption Reference](#submission-packet--adoption-reference)

---

## Project Overview

The **ALX Accessibility Assistant** is an accessible, multilingual support system embedded into ALX's Savanna LMS. It addresses the high barrier to entry faced by Ethiopian learners with disabilities and low-bandwidth connectivity (2G/3G feature phones) by providing:

* **Level 1 Drop-in Web Component (`<alx-assistant>`):** Encapsulated in the Shadow DOM to guarantee style isolation, responsive from 320px screens up to 200% browser zoom.
* **Strictly Grounded RAG with Zero Hallucination:** Answers are strictly grounded in course materials with verifiable section citations. Out-of-scope queries are rejected with 0 citations and an offer of human escalation.
* **In-Page Smooth Deep-Linking:** Clicking a citation in the assistant scrolls smoothly to the exact cited paragraph in the lesson, highlights it with a soft yellow focus ring, and focuses the heading for screen readers.
* **Pluggable AI Engine:** Runs 100% offline out-of-the-box (zero paid API lock-in, zero cost), or connects seamlessly to Google Gemini 2.5 Flash when configured.
* **Bilingual English & Amharic (አማርኛ):** Native support for Ethiopic script (`\u1200-\u137F`), stop-word removal, and Plain Language Simple Mode.
* **Learner-Controlled Live Escalation:** Anonymous help ticketing with explicit consent gates before launching Jitsi Meet video and screen-sharing sessions.
* **Inclusive Career Gateway:** Aggregates jobs using `schema.org/JobPosting` structured JSON-LD with SMS alerts and interview accommodation requests.

---

## Stage 1 Accessibility Gate Status

The assistant has been evaluated against **WCAG 2.2 Level AA** criteria using automated in-browser **axe-core 4.10+** scanning directly across the component and its Shadow DOM:

```
========================================================================
Stage 1 Accessibility Gate Automated Audit
========================================================================
Severity     Violations Found    Requirement for Gate    Status
------------------------------------------------------------------------
Critical     0                   0 Allowed               PASS (0)
Serious      0                   0 Allowed               PASS (0)
Moderate     0                   Advisory                0
Minor        0                   Advisory                0
------------------------------------------------------------------------
WCAG 2.2 AA Gate Status: PASS — Eligible for Stage 2 Scoring
✓ Zero axe-core violations found!
========================================================================
```

* **Live Verification Page:** Run live in your browser at [http://localhost:8000/a11y-audit](http://localhost:8000/a11y-audit).
* **Screen Reader Certified:** Tested with **NVDA** (Windows) and **TalkBack** (Android). Incoming messages are placed in an ARIA live region (`role="log"`, `aria-live="polite"`).
* **Keyboard-Only Accessible:** Complete keyboard navigation with visible focus rings. Pressing `Escape` closes the chat dialog and immediately restores focus to the launcher button.
* **WCAG 2.5.3 (Label in Name):** All interactive buttons (`#alx-launcher`, `#alx-lang-btn`, `#alx-escalate-btn`) contain their visible labels in their programmatic accessible names.

---

## Quick Start & Local Running Instructions

Follow these step-by-step instructions to run the entire stack locally on Windows, macOS, or Linux.

### Prerequisites

* **Python 3.10, 3.11, 3.12, or 3.13** installed.
* **pip** (Python package manager).
* Modern web browser (Chrome, Edge, Firefox, or Safari).

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/fenet-as/accessibility-assistant.git
cd accessibility-assistant
```

---

### Step 2: (Recommended) Create and Activate a Virtual Environment

* **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

### Step 3: Install Required Dependencies

```bash
pip install -r requirements.txt
```

*(Key libraries: `fastapi`, `uvicorn`, `beautifulsoup4`, `python-dotenv`, `google-genai`, `pytest`, `httpx`)*

---

### Step 4: Configure Environment Variables

The project includes an example template. Copy `.env.example` to `.env`:

* **On Windows (PowerShell):**
  ```powershell
  Copy-Item assistant\.env.example .env
  ```
* **On macOS / Linux:**
  ```bash
  cp assistant/.env.example .env
  ```

The system automatically runs **100% offline** with zero configuration required. If you want to connect live **Google Gemini 2.5 Flash**, open `.env` and set:

```env
AI_PROVIDER=cloud
GEMINI_API_KEY=your_gemini_api_key_here
```

*(See [Environment Configuration](#environment-configuration-env) below for all available options).*

---

### Step 5: Start the Local Server

Run the backend server using Uvicorn:

```bash
python -m uvicorn assistant.api.main:app --host 127.0.0.1 --port 8000 --reload
```

When successfully started, your terminal will display:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

---

### Step 6: Open the Application in Your Browser

| What You Want to Test | Browser URL | Description |
| :--- | :--- | :--- |
| **Savanna LMS Course Lesson** | **[http://localhost:8000/pages/concept-with-navigation.html](http://localhost:8000/pages/concept-with-navigation.html)** | Interactive course lesson with embedded `<alx-assistant>` widget. |
| **Stage 1 Accessibility Audit** | **[http://localhost:8000/a11y-audit](http://localhost:8000/a11y-audit)** | Real-time axe-core WCAG 2.2 AA automated verification page. |
| **Interactive API Docs (Swagger)**| **[http://localhost:8000/docs](http://localhost:8000/docs)** | OpenAPI 3.0 interactive documentation for all endpoints. |
| **Teacher Analytics Dashboard** | **[http://localhost:8000/analytics](http://localhost:8000/analytics)** | Topic confusion breakdown, language stats, and escalation rates. |
| **SMS Feature Phone Simulator** | **[http://localhost:8000/sms-simulator](http://localhost:8000/sms-simulator)** | Interactive 2G/3G mobile phone simulator with Amharic SMS. |

---

## Environment Configuration (.env)

The application supports both a root `.env` and `assistant/.env` (both are ignored by git to protect credentials):

| Environment Variable | Allowed Values | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `AI_PROVIDER` | `faq` or `cloud` | `faq` | `faq`: 100% offline rule engine (zero API cost).<br>`cloud`: Google Gemini 2.5 Flash. |
| `GEMINI_API_KEY` | String | *Empty* | Your Google Gemini API Key (required when `AI_PROVIDER=cloud`). |
| `HOST` | String | `127.0.0.1` | Local host IP to bind the server to. |
| `PORT` | Integer | `8000` | Port number for the FastAPI server. |
| `JITSI_BASE_URL` | URL | `https://meet.jit.si` | Jitsi instance for privacy-safe video & screen sharing. |
| `TELEGRAM_BOT_TOKEN` | String | *Empty* | Optional token for live Telegram bot polling. |
| `DATABASE_PATH` | Path | `assistant/data/assistant.db` | Path to SQLite database. |

### How Pluggable Fallback Works
If `AI_PROVIDER=cloud` is selected but no API key is provided, or if Gemini encounters rate limits or network outages, the app **automatically degrades to the Offline FAQ engine**. It will never crash or disrupt a learner.

---

## Live Application URLs & Endpoints

### Core Endpoints

* `GET /api/health`: System health status, active AI provider, and indexed chunks count.
* `POST /api/chat`: Submit questions in English or Amharic; returns grounded answer with section citations.
* `POST /api/escalate`: Generates an anonymous escalation ticket and secure Jitsi screen-share room.
* `GET /api/jobs`: Returns accessible job listings in `schema.org/JobPosting` JSON-LD format.
* `POST /api/subscriptions`: Subscribes a phone number to SMS job alerts.
* `POST /api/accommodations`: Submits an interview accommodation request for learners with disabilities.
* `GET /api/analytics/summary`: Aggregate analytics on learner queries, language distributions, and escalation trends.
* `GET /api/lti/config.json`: LTI 1.3 tool configuration manifest for Canvas / Moodle.

---

## Key Architectural Highlights

### 1. In-Page Smooth Deep-Linking
When a learner asks a question, the assistant provides citations with section titles. Clicking any citation:
1. Detects the section anchor (e.g. `#what-is-shaping-the-future-of-va-work`) on the current page.
2. Smoothly scrolls the page directly to the cited text.
3. Gently highlights the section with a soft yellow focus ring for 2.5 seconds.
4. Moves keyboard and screen-reader focus to the heading.

### 2. Simple Mode (Cognitive Accessibility)
Learners can toggle **Simple Mode** in the assistant toolbar. When active:
* Answers are simplified into short, elementary bullet points.
* Sentences avoid dense academic jargon.

### 3. Screen Sharing with Explicit Learner Consent
Screen sharing is never initiated automatically. When a learner requests human assistance:
1. An explicit modal displays what will be shared (screen content, microphone).
2. The learner must actively confirm consent.
3. The learner is redirected to an end-to-end encrypted Jitsi Meet room where they control their own browser media permissions.

---

## Running the Automated Test Suite

The repository includes a comprehensive 29-test test suite covering grounding, API contracts, accessibility, omnichannel routes, and database persistence.

To execute all tests:

```bash
python -m pytest assistant/tests/ -v
```

### Running Specific Test Modules

* **Accessibility & WCAG Compliance:**
  ```bash
  python -m pytest assistant/tests/test_accessibility.py -v
  ```
* **Strict Anti-Hallucination Grounding:**
  ```bash
  python -m pytest assistant/tests/test_grounding.py -v
  ```
* **REST API Endpoints:**
  ```bash
  python -m pytest assistant/tests/test_api.py -v
  ```
* **Omnichannel (SMS & Telegram):**
  ```bash
  python -m pytest assistant/tests/test_channels.py -v
  ```
* **SQLite Persistence & Analytics:**
  ```bash
  python -m pytest assistant/tests/test_database.py -v
  ```

---

## Omnichannel Channels (SMS & Telegram)

### 1. SMS Simulator (2G/3G Low-Bandwidth)
Visit **[http://localhost:8000/sms-simulator](http://localhost:8000/sms-simulator)** to simulate a basic feature phone:
* Send `HELP` or `እገዛ` to see available SMS commands.
* Send `JOBS` or `ሥራ` to receive active job openings.
* Send any course question in Amharic or English to receive a 160-character split SMS response.

### 2. Telegram Bot
* **File:** `assistant/adapters/telegram/bot.py`
* Supports `/start`, `/help`, `/human`, and course query messages.
* To run the live polling bot, set `TELEGRAM_BOT_TOKEN` in `.env` and execute:
  ```bash
  python -m assistant.adapters.telegram.bot
  ```

---

## Project Directory Structure

```
accessibility-assistant/
├── .env.example                       # Environment configuration template
├── README.md                          # Main project guide (this document)
├── INSTALL.md                         # 60-Second adoption guide
├── requirements.txt                   # Production Python dependencies
├── assistant/
│   ├── api/
│   │   ├── main.py                    # FastAPI application & REST API routes
│   │   └── analytics.html             # Teacher Analytics dashboard
│   ├── core/
│   │   ├── database.py                # SQLite query & escalation persistence
│   │   ├── grounding.py               # Anti-hallucination coordinator
│   │   ├── models.py                  # Pydantic data schemas
│   │   ├── retrieval.py               # BM25 bilingual search engine
│   │   └── providers/
│   │       ├── factory.py             # Pluggable AI provider factory
│   │       ├── faq_provider.py        # 100% offline rule-based FAQ engine
│   │       └── cloud_provider.py      # Google Gemini 2.5 Flash provider
│   ├── data/
│   │   ├── chunks.json                # Ingested course curriculum chunks
│   │   └── assistant.db               # SQLite database (auto-generated)
│   ├── ingest/
│   │   └── chunker.py                 # HTML parser & curriculum segmenter
│   ├── widget/
│   │   ├── assistant.js               # <alx-assistant> Shadow DOM web widget
│   │   ├── audit.html                 # axe-core automated audit runner
│   │   └── axe.min.js                 # Self-hosted axe-core 4.10+ engine
│   ├── adapters/
│   │   ├── sms/                       # SMS service & simulator
│   │   └── telegram/                  # Telegram bot adapter
│   └── tests/                         # Pytest test suite (29 tests)
├── savanna-static/                    # Cloned Savanna LMS test pages
└── .github/workflows/ci.yml           # GitHub Actions automated CI workflow
```

---

## Submission Packet & Adoption Reference

* **Adoption in Under 60 Seconds:** See [INSTALL.md](INSTALL.md) for embed snippets for LMS platforms, React apps, and CMS engines.
* **Stage 1 Verification:** Open [http://localhost:8000/a11y-audit](http://localhost:8000/a11y-audit) to inspect live axe-core results.
* **Live Demo Script:** See `done_so_far/06 – Phase 5 – Submission Packet & Adoption Guide.md` for the exact 3-minute hackathon presentation outline.

---

## License

This project is submitted to the **ALX Digital Bridge Accessibility Hackathon 2026** under the MIT License.
