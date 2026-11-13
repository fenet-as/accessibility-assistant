# ALX Digital Bridge Accessibility Assistant — Installation & Adoption Guide

*Adopt this accessible multilingual assistant on any website, LMS, or application in under 60 seconds.*

---

## 1. Level 1: 60-Second Drop-In Web Embed (Recommended)

To add the accessible tutor widget to any website (Savanna LMS, WordPress, React, Django, or plain HTML), simply paste this single script tag right before your closing `</body>` tag:

```html
<!-- Drop-in ALX Accessibility Assistant -->
<script 
  src="https://your-domain.com/assistant/widget/assistant.js" 
  data-api="https://your-domain.com/api" 
  data-lang="auto" 
  data-source="course:va-1" 
  defer>
</script>
```

### Configuration Attributes

| Attribute | Default | Description |
|---|---|---|
| `data-api` | `http://localhost:8000/api` | Base URL of the assistant FastAPI backend. |
| `data-lang` | `auto` | Preferred language: `am` (Amharic), `en` (English), or `auto` (auto-detects). |
| `data-source` | `course:va-1` | Scope identifier for the active course or page. |

---

## 2. Level 2: REST API & Programmatic Integration

If you want to build a custom frontend or connect an external app, use our documented REST API.

* **Base URL:** `https://your-domain.com/api`
* **Interactive OpenAPI (Swagger) UI:** `https://your-domain.com/docs`

### Example: Asking a Course Question
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session": "learner-101",
    "message": "What is shaping the future of virtual assistant work?",
    "language": "en",
    "mode": "normal"
  }'
```

**JSON Response:**
```json
{
  "status": "answered",
  "language": "en",
  "answer": "More remote-first businesses...",
  "citations": [
    {
      "title": "The Future of the VA Industry",
      "section": "What is Shaping the Future of VA Work?",
      "url": "pages/concept-with-navigation.html#what-is-shaping-the-future-of-va-work"
    }
  ],
  "actions": ["get_human_help"]
}
```

---

## 3. Level 3: Standards-Based Interoperability

### Career Gateway (`schema.org/JobPosting`)
Fetch all accessible job vacancies formatted as standard JSON-LD:
```bash
curl -X GET "http://localhost:8000/api/jobs"
```

### Learning Tools Interoperability (LTI 1.3)
To register the tool in Canvas, Moodle, or Blackboard, use our LTI configuration manifest:
```
URL: https://your-domain.com/api/lti/config.json
```

---

## 4. Local Development Quickstart

1. **Clone & Install:**
   ```bash
   git clone https://github.com/fenet-as/accessibility-assistant.git
   cd accessibility-assistant
   pip install -r assistant/requirements.txt
   ```

2. **Start Backend Server:**
   ```bash
   python -m uvicorn assistant.api.main:app --host 127.0.0.1 --port 8000
   ```

3. **Open in Browser:**
   * **Host LMS with Widget:** `http://localhost:8000`
   * **SMS Simulator:** `http://localhost:8000/sms-simulator`
   * **Accessibility Audit:** `http://localhost:8000/a11y-audit`
   * **API Docs:** `http://localhost:8000/docs`

