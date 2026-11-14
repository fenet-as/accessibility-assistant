# 02 – Embed Widget & Accessibility Spec

*Status: Planned. This is the part the accessibility gate tests first, so it is built and tested before anything else.*

## 1. Integration (Level 1)

One script tag adds the assistant to any page:

```html
<script src="https://HOST/assistant.js"
        data-api="https://HOST/api"
        data-lang="auto"
        data-source="course:va-1"
        defer></script>
```

- Renders inside a **Shadow DOM** so host CSS (Bootstrap on Savanna) cannot break it and it cannot break the host.
- No external requests except to our own API. Fonts and icons are self-hosted so it works offline-first and on 3G.
- Configuration through `data-*` attributes; a small JavaScript API (`Assistant.open()`, `Assistant.setLanguage()`) for hosts that want it.
- Host page can pass the current course or page as context so answers can cite it.

## 2. Interface structure

| Element | Behaviour |
| --- | --- |
| **Launcher button** | Real `<button>` with a text label (not icon-only), 44 px minimum target, visible focus ring |
| **Chat panel** | Non-modal dialog (`role="dialog"`, labelled). **Not a focus trap**: Escape closes it, focus returns to the launcher, Tab can leave it |
| **Message log** | `role="log"` with polite live announcements; each new assistant message is announced once |
| **Message bubbles** | Each has `lang` and `dir="auto"` so Amharic, English and Arabic render and read correctly |
| **Citations** | Visible list under each answer; each is a real link to the source section |
| **Input area** | Labelled text field, Send button, Enter to send; visible instructions, no placeholder-only labels |
| **Language control** | Amharic / English switch, announced when changed |
| **Simple Mode** | Toggle for shorter sentences and step-by-step answers (extra credit) |
| **Voice** | Optional microphone and read-aloud buttons; never the only way to do anything |
| **Get human help** | Always visible, one activation; see doc 05 |
| **Status messages** | "Thinking…", "Not found in course material", errors – all announced, none colour-only |

## 3. Accessibility requirements (the gate)

**Must pass with a co-designer working unaided:** NVDA, TalkBack, keyboard only, 200% zoom, sound off. **axe-core:** zero critical or serious issues.

Implementation checklist (WCAG 2.2 AA):

- Semantic HTML first; ARIA only where HTML cannot express the role.
- Every control reachable and operable by keyboard; logical tab order; visible focus that is not hidden by sticky host headers (WCAG 2.2 Focus Not Obscured).
- Colour contrast at least 4.5:1 for text, 3:1 for controls and focus indicators; information never conveyed by colour alone.
- Layout reflows at 200% zoom and at 320 px width without horizontal scrolling or clipped content.
- Target size at least 24 px (we aim for 44 px).
- New messages announced without stealing focus; no double announcements.
- Sound off must be fine: any audio output has a text equivalent.
- Respect `prefers-reduced-motion`; no auto-playing anything.
- Language of each message set with `lang`; text direction set per message for RTL.
- Errors identified in text with a suggested fix; no time limits.
- Works on a low-end Android phone and with TalkBack gestures.

## 4. Language and script

- Ethiopic script rendered with a self-hosted font (for example a Noto Sans Ethiopic subset); fallback stack defined.
- Screen readers need an Amharic voice installed to read Amharic aloud. This must be **tested on the co-designer’s real setup** early; if NVDA or TalkBack reads Amharic poorly, we document it and make sure English and visual text always work.
- RTL: layout uses logical CSS properties (`margin-inline-start`, not left/right), so Arabic and similar scripts work without special cases.
- Ethiopian calendar: show Ethiopian dates alongside Gregorian where dates appear (deadlines, job closing dates). Planned.

## 5. Coexisting with Savanna (assumptions to verify at kick-off)

- The static pages use Bootstrap, including modals that trap focus. Test the widget while a Bootstrap modal is open.
- Avoid global styles and global ids; use a unique custom element name.
- Do not rely on host JavaScript. Keep `localStorage` use to non-personal preferences (language, Simple Mode).

## 6. Performance targets (proposed, to be measured)

- Widget under about 50 KB gzipped, excluding fonts.
- Loads lazily after the host page; usable on 3G.
- Chat works with the cloud AI unreachable (falls back to offline FAQ).

## 7. Test plan for this part

1. **Automated:** axe-core through Playwright on a page with the widget in every state (closed, open, error, human-help dialog) on every build.
2. **Manual:** NVDA + browser, TalkBack on Android, keyboard-only, 200% zoom, sound off, one full task each.
3. **Co-designer sessions:** early prototype review, then repeat. Record findings and what we changed.
4. **Output:** WCAG 2.2 AA conformance report for submission.
