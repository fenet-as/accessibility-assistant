# 06 – Build Plan, Testing & Submission

*Status: Planned. Dates are fixed by the organizers; the order of work is our proposal and can change when the team forms and the starter project arrives.*

## 1. Principle: walking skeleton first

Get one thin path working end to end and accessible, then widen it. The path: **learner asks in Amharic or English → grounded answer with citation → "Get human help" works.** Everything else plugs into that.

## 2. Phases

### Phase 0 – Before the event (Nov 11–13)

Subject to confirming that pre-event code is allowed; otherwise do research, design and tooling only.

- [ ] Confirm the pre-event code rule with organizers.
- [ ] Create the repo with the layout from doc 01 and CI that runs tests and axe-core.
- [ ] Ingest the sample concept page into chunks with citations.
- [ ] Keyword retrieval plus the `not_found` rule, with a first test question set.
- [ ] Widget shell: launcher, dialog, log with live announcements, input, `lang`/`dir`.
- [ ] Telegram bot created and answering through the same core.
- [ ] Draft bilingual FAQ and the 20–30 question test set.
- [ ] Attend the training sessions; note anything that changes the plan.

### Day 1 – Nov 14 (09:00–17:00)

- [ ] Kick-off: get the starter project, licence, submission rules; answer the open questions in doc 00.
- [ ] Form the team; assign owners to docs 02, 03, 04, 05.
- [ ] Meet the co-designer; test the widget shell on their real devices and screen reader.
- [ ] Load real course content; adapt the embed to the real Savanna environment.
- [ ] Try the Amharic retrieval options on the test set and decide.
- [ ] Provider interface with cloud, offline FAQ and (if feasible) local model.
- [ ] Escalation to the staff Telegram group working.

### Day 2 – Nov 15 (submission by 16:30)

- [ ] Morning: consent-gated screen share, job data and questions, alerts, accommodation form.
- [ ] SMS adapter and simulator (or real gateway if available).
- [ ] Fix every axe-core critical or serious issue; repeat the full manual gate run with the co-designer.
- [ ] Docs: install guide, OpenAPI, WCAG 2.2 AA report, privacy note.
- [ ] Demo script and rehearsal; honest implemented-vs-planned table.
- [ ] **Submit before 16:30**, leaving a buffer.

### After the event

Awards around Nov 22; winners do a two-week hardening sprint (security review, three testing rounds with 30+ testers with disabilities, Savanna integration).

## 3. Priority tiers (what to cut first)

| Tier | Items |
| --- | --- |
| **Must have** (gate and mandatory) | Accessible widget, Amharic and English text, grounded answers with citations, human help with consent-controlled sharing, Telegram, SMS route (at least simulated and clearly labelled), pluggable AI, job questions, alerts, accommodation requests |
| **Should have** | Voice, offline FAQ polish, local model, Simple Mode, OpenAPI polish, script-tag docs |
| **Nice to have** | Teacher dashboard, LTI 1.3, cross-channel linking, Ethiopian calendar display |

If time runs short, cut from the bottom. Never cut accessibility testing.

## 4. Test and evidence plan

| Check | How | Evidence |
| --- | --- | --- |
| axe-core clean | Playwright + axe on every widget state, in CI | Report showing 0 critical and 0 serious |
| Screen readers | NVDA and TalkBack, full task, co-designer | Session notes and fixes made |
| Keyboard only, 200% zoom, sound off | Manual runs, co-designer | Checklist with dates |
| Grounding | Fixed question set; out-of-scope questions must return `not_found` | Test output |
| Provider swap | Switch cloud to offline FAQ without code changes | Demo plus test |
| Consent | Screen share cannot start without learner action | Test and recording of behaviour |
| Low bandwidth | Throttled 3G run; widget size measured | Measurements |
| Privacy | Data inventory vs stored data | Short written note |

## 5. Submission checklist

- [ ] Working demo on Savanna (or the provided starter project).
- [ ] Script-tag install guide that a stranger can follow.
- [ ] REST API with OpenAPI spec.
- [ ] Level 3 item: schema.org/JobPosting output (and LTI 1.3 only if realistic).
- [ ] WCAG 2.2 AA conformance report; axe-core results.
- [ ] Co-designer evaluation summary and what changed because of it.
- [ ] Privacy and security notes; no secrets in the repo.
- [ ] Open-source licence as specified by ALX.
- [ ] Deployment and running-cost documentation (no paid API lock-in).
- [ ] Honest table of what is implemented, partial, simulated and planned.

## 6. Top risks

| Risk | Mitigation |
| --- | --- |
| Amharic quality in retrieval, models, or screen-reader voices | Measure early; keep offline bilingual FAQ and English path as safe fallbacks |
| Starter project differs from the static pages | Keep the core and adapters independent; adapt only the embed layer |
| SMS gateway unavailable | Adapter plus labelled simulator |
| Mobile screen sharing not supported | Text and photo fallback |
| Too much scope for two days | Walking skeleton, tiers above, daily cut review |
| Team not formed or skills uneven | Keep decisions simple; docs make work splittable by section |
