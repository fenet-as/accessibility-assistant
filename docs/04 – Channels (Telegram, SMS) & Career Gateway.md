# 04 – Channels (Telegram, SMS) & Career Gateway

*Status: Planned. Telegram can be built now (a bot token is free). SMS depends on a gateway the organizers must name; until then we build the adapter and a clearly labelled simulator.*

## 1. Channel adapter pattern

Each channel does only three things: **receive** a message, **normalise** it into the core format, and **format** the core reply for that channel. All tutoring, grounding, and job logic stays in the core, so channels behave the same.

| Channel | Reply formatting |
| --- | --- |
| Web widget | Full answer, citation links, action buttons |
| Telegram | Short message, citations as links, inline buttons for "Get human help" and language |
| SMS | Very short, plain text, numbered options, citation as a short reference |

## 2. Telegram bot

**Core features**

- `/start` (language choice), `/lang`, `/help`, `/human`, `/jobs`, `/subscribe`, `/stop`.
- Free-text questions answered through the same core, with citations.
- "Get human help" button that starts escalation (doc 05).
- Development uses long polling; deployment uses a webhook.

**Open items:** voice messages (planned later, depends on speech provider); how conversations are linked across channels (see section 4).

## 3. SMS or low-bandwidth text route

**Constraints we must design for**

- A standard SMS holds about 160 characters; Amharic (Unicode) messages hold about 70 per segment, so replies must be short and may be split. Keep answers to one or two segments where possible.
- No rich formatting, no links that need a smartphone.

**Interaction design**

- Keyword commands: `HELP`, `JOBS`, `SUBSCRIBE`, `STOP`, `HUMAN`, plus free-text questions.
- Numbered replies ("Reply 1 for more, 2 for a person") so no typing is needed.
- Offline FAQ is the natural default here because it is cheap and needs no model.

**Gateway**

- Which provider, credits and Ethiopian network support are **unknown**; ask the organizers.
- Until confirmed: build the adapter behind a provider interface plus a simulator page. Anything shown with the simulator is described honestly as simulated.

## 4. Conversation identity (decision needed)

- Default: each channel has its own anonymous session; nothing is linked, which minimises data.
- Option: learner can link channels with a one-time code they choose to enter. Only build this if time allows and it can be done without storing personal data.

## 5. Career Gateway (required for every track)

### 5.1 Job data

- Source unknown. We create a small set of realistic sample jobs, stored as **schema.org/JobPosting** JSON-LD (title, description, hiring organization, location, employment type, qualifications, skills, application instructions, valid-through date).
- Exposed through `GET /api/jobs`; can be swapped for a real source later.

### 5.2 Job questions

The assistant answers "What jobs are available?", "What qualifications are needed?", "What skills?", "How do I apply?", "What does this mean?" using the **same grounded pipeline**, with the job postings as the source and cited the same way.

### 5.3 Job alerts (Telegram and SMS)

- Learner subscribes with simple choices (job type, location).
- A scheduled job matches new postings to subscriptions and sends a short alert on the chosen channel.
- Data kept: the channel address and preferences only, with explicit consent and an easy `STOP`.
- Real SMS delivery depends on the gateway; Telegram delivery can be real.

### 5.4 Interview accommodation requests

A short, accessible form (web) and a guided flow (Telegram and SMS):

| Field | Notes |
| --- | --- |
| Which job or interview | Chosen from the list or entered |
| Type of accommodation | Options such as accessible location, extra time, sign-language interpreter, screen-reader-friendly materials, alternative communication method, other (free text) |
| Preferred contact method | Channel the learner already uses |

- Keep it minimal: no disability diagnosis or medical details required. Say plainly what is stored and who sees it.
- **Open question:** how requests reach employers (organizers to confirm). Until then, requests are stored and shown in a simple staff view.

## 6. Tests for this part

- Adapter tests with recorded Telegram updates; SMS length and splitting tests including Amharic text.
- Alert matching tests; unsubscribe always works.
- Accessibility check of the accommodation form (same axe-core and manual process as the widget).
