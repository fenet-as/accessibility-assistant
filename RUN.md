# Run — Docker first, then common commands

## Docker (recommended)

```bash
cd accessibility-assistant

# Optional config (Gemini, Telegram, etc.)
cp .env.example .env   # Windows: Copy-Item .env.example .env

# Build and start API + widget
docker compose up --build
```

Open:

| URL | What |
|-----|------|
| http://localhost:8000/ | Savanna + assistant widget |
| http://localhost:8000/docs | API docs |
| http://localhost:8000/a11y-audit | Accessibility audit |
| http://localhost:8000/sms-simulator | SMS simulator |

```bash
# Also start Telegram bot (needs TELEGRAM_BOT_TOKEN in .env)
docker compose --profile telegram up --build

# Stop
docker compose down

# Rebuild after code changes
docker compose up --build --force-recreate
```

Data (`assistant.db`, `chunks.json`) lives in the `assistant-data` volume and survives restarts.

---

## Without Docker (local)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn assistant.api.main:app --reload --port 8000
```

macOS/Linux: `source venv/bin/activate` and `cp .env.example .env`.

---

## Useful commands

```bash
# Tests
python -m pytest

# Rebuild course index from Savanna page
python -m assistant.ingest

# Telegram long-polling (local, not Docker)
python -m assistant.channels.telegram

# Quick chat smoke test
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session":"demo","message":"What is shaping the future of virtual assistant work?","language":"en"}'

# Offline course pack
curl "http://localhost:8000/api/offline/packs"
curl "http://localhost:8000/api/offline/pack?scope=course:va-1" -o pack.json
```

Inside a running Docker container:

```bash
docker compose exec api python -m pytest
docker compose exec api python -m assistant.ingest
```

Default `AI_PROVIDER=faq` works fully offline. Set `AI_PROVIDER=cloud` and `GEMINI_API_KEY` in `.env` for Gemini (falls back to FAQ on failure).
