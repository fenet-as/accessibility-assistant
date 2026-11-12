# 00 – Project Overview & Requirements

*ALX Digital Bridge Accessibility Hackathon 2026 · Track 3: Multilingual Assistant and Live Help*

This is the master reference. Docs 01–06 cover each part of the build. Status labels used everywhere: **Planned** (not built), **In progress**, **Done (tested)**. Nothing is marked Done without evidence.

## 1. Event facts

- **Organizer:** ALX Ethiopia (Digital Bridge), with AAAPD and Tomorrow is Better. Partners: SNV and Mercy Corps under LIWAY.
- **Venue:** ALX Tech Hub, Lideta, Addis Ababa.
- **Day 1:** Nov 14, 09:00–17:00. **Day 2:** Nov 15, submission by **16:30**.
- **Awards:** around Nov 22. Winner per track gets 100,000 ETB and a paid two-week hardening sprint with ALX engineers (security review, three testing rounds with 30+ testers with disabilities, Savanna integration).
- **Participation:** confirmed. Team of four engineers plus a co-designer; team not formed yet.
- **Deployment path:** Savanna (about 3,000 learners), then eight job-matching platforms and two regional training institutions, planned for December.

## 2. What we are building (one paragraph)

A reusable, accessible, multilingual assistant module (not a standalone chatbot) that drops into Savanna with one script tag. Learners ask course questions in Amharic or English by text or voice and get answers grounded only in course content, with citations. If the assistant cannot answer, it says so and offers a human. The same assistant is reachable through Telegram and a low-bandwidth SMS route, and also answers job questions, sends job alerts, and takes interview accommodation requests.

## 3. Judging

**Stage 1 – Accessibility gate (pass/fail).** A co-designer must complete the main task unaided using: NVDA, TalkBack, keyboard only, 200% zoom, and sound off. axe-core must report **zero critical or serious** issues. We must submit a **WCAG 2.2 AA conformance report**.

**Stage 2 – 100 points.**

| Category | Points | What it rewards |
| --- | --: | --- |
| Works for the people it is for | 30 | Co-designer evaluation, independent task completion, use of feedback |
| Can be adopted | 25 | Easy install, documentation, three integration levels |
| Built for Ethiopia | 15 | Amharic/Ethiopic script, Ethiopian calendar, cheap Android, 3G, offline |
| Quality, security, privacy | 15 | Tests, minimum data, consent, security |
| Can be kept running | 15 | Low running cost, no paid-API lock-in, clear docs |

## 4. Mandatory requirements checklist

| # | Requirement | Covered in | Status |
| --- | --- | --- | --- |
| R1 | Tutor in Amharic and English, text and voice | 02, 03 | Planned |
| R2 | Answers only from course content, with citations; admits when it cannot answer | 03 | Planned |
| R3 | Web embed reusable on other sites | 02 | Planned |
| R4 | Telegram bot with core tutoring and route to a human | 04 | Planned |
| R5 | Low-bandwidth SMS or lightweight text route | 04 | Planned |
| R6 | Chat announces new messages to assistive tech, handles RTL, keyboard, screen readers | 02 | Planned |
| R7 | One-click human help with learner-controlled screen sharing | 05 | Planned |
| R8 | Pluggable AI: cloud, local open model, offline FAQ | 03 | Planned |
| R9 | Career Gateway: job alerts via Telegram and SMS | 04 | Planned |
| R10 | Interview accommodation requests | 04 | Planned |
| R11 | Answer job-related questions | 03, 04 | Planned |
| R12 | Integration: script tag (L1), REST + OpenAPI (L2), standard such as LTI 1.3 / JobPosting (L3) | 02, 03, 04 | Planned |

**Extra credit:** plain-language Simple Mode; teacher dashboard with no learner identities.

## 5. Non-negotiable principles

1. Accessibility from the first commit, not at the end. The co-designer is a team member.
2. Never invent course facts; always cite; say "not in the course material" when true.
3. Never start screen sharing without the learner’s explicit action.
4. Minimise data collection. No personal data stored by default.
5. Keep the AI layer replaceable; avoid paid-API lock-in.
6. Design for 3G, cheap Android phones, and offline fallback.
7. Do not overengineer. Distinguish implemented from planned, and never claim a requirement is met without testing.

## 6. Known unknowns (ask at kick-off)

- Savanna starter project: stack, auth, how widgets are embedded, how course content is accessed.
- Format of real course materials and expected citation format.
- Who receives escalated help requests; any existing support or tutor system.
- SMS gateway and any hackathon credits; expected SMS limits.
- Job data source or existing job-matching API; how accommodation requests reach employers.
- Open-source licence ALX will specify; exact submission requirements.
- Whether code written before the event is allowed.

## 7. Document map

- **00** Overview & Requirements (this doc)
- **01** Architecture & Decisions
- **02** Embed Widget & Accessibility Spec
- **03** Backend API, RAG & AI Providers
- **04** Channels (Telegram, SMS) & Career Gateway
- **05** Human Escalation, Privacy & Security
- **06** Build Plan, Testing & Submission
