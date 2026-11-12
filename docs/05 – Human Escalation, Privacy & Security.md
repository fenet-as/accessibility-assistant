# 05 – Human Escalation, Privacy & Security

*Status: Planned. Screen sharing is the most privacy-sensitive feature in the project: it must never start without the learner’s own action.*

## 1. Escalation flow

1. **Trigger:** the learner presses "Get human help" (always visible), or the assistant returns `needs_human` or `not_found` and offers it. One activation starts the request.
2. **Request:** the system creates an anonymous help request with the language, channel, and a short note the learner may add. No screen content is sent.
3. **Routing:** the request is posted to a **staff Telegram group**. A human replies there; the reply is relayed back into the learner’s chat (web, Telegram or SMS).
4. **Optional screen sharing:** if the helper needs to see the screen, they ask in the chat. The learner is shown a clear dialog and chooses to start. See section 2.
5. **Close:** either side ends the session; the learner can say whether the problem was solved. Unresolved questions feed the anonymous analytics.

**Open questions for organizers:** who staffs the help desk, in what hours, and whether an existing support tool must be used instead of a Telegram group.

## 2. Learner-controlled screen sharing

**Design:** the helper sends a Jitsi room link. The learner joins and **starts sharing themselves**; the browser’s own picker lets them choose a window, tab or whole screen, and they can stop at any time.

Rules:

- Never auto-start. No share request is ever accepted on the learner’s behalf.
- A plain-language consent dialog before the learner opens the link: what will be visible, that they choose what to share, and how to stop.
- The dialog and the stop control are keyboard and screen-reader accessible.
- No recording by us. Say so in the dialog.
- The learner can say no and keep chatting with the helper by text.

**Known limitations to handle**

- Mobile Android browsers do not support the browser screen-share API in the usual way, so a TalkBack user on a phone may not be able to share. Provide a **fallback**: describe the problem in text, or send a photo/screenshot through the chat.
- Whether public Jitsi allows embedding or requires login can change; verify before relying on it. A self-hosted Jitsi or a plain WebRTC link are alternatives if needed.
- Document the data path: media goes between the learner and helper, not through our database.

## 3. Privacy by design

| Area | Rule |
| --- | --- |
| Collection | No accounts, no names, no phone numbers by default |
| Identifiers | Random anonymous session id; not linked across channels unless the learner opts in |
| Alerts | Store only the channel address and preferences, with explicit consent and a one-step unsubscribe |
| Accommodation requests | Collect only what is needed to arrange it; no medical details |
| Retention | Short, stated retention period for chat turns (value to be decided and documented) |
| Analytics | Aggregate topics and counts only; hide any group smaller than a minimum size so no individual can be inferred |
| Transparency | A plain-language privacy notice in the widget, in Amharic and English |
| Third parties | If a cloud AI is used, say which data leaves the system and avoid sending anything personal |

## 4. Security checklist

- Secrets in environment variables; none in the repository.
- CORS allow-list for embedding sites; rate limiting on public endpoints.
- Input validation and size limits; output escaped in the widget to prevent injection.
- Webhook verification for Telegram and the SMS gateway.
- Course and job text is treated as data, never as instructions to the model.
- Dependency scanning; minimal dependencies in the widget.
- HTTPS only; no sensitive data in URLs or logs.
- Basic security review notes ready for the hardening sprint.

## 5. Evidence we will keep

Test results for consent behaviour (screen share never starts without learner action), a data inventory, and a short privacy and security note in the submission. No claim is made in the submission for anything not tested.
