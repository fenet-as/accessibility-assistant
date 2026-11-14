# Deployment Guide — ALX Accessibility Assistant

> Meets the official hackathon criteria: **"A judge installs your module in one hour, from your documentation alone."** (Slide 11) & **"Submit by 16:30 on Sunday: code, README, Docker Compose, and the WCAG 2.2 AA conformance report."** (Slide 15).

---

## 1. Quick Deploy with Docker Compose (Recommended for Judges)

The entire application (FastAPI backend, Savanna LMS embed, Teacher Analytics, Admin Ingestion, and SMS simulator) runs in a single lightweight container.

### Step 1: Clone and Enter Repository
```bash
git clone https://github.com/fenet-as/accessibility-assistant.git
cd accessibility-assistant
```

### Step 2: Configure Environment (Optional)
Copy the example environment file:
```bash
cp .env.example .env
```
*(By default, `AI_PROVIDER=faq` runs 100% offline with zero cloud API keys or internet needed. To use Gemini cloud model, set `AI_PROVIDER=cloud` and paste your `GEMINI_API_KEY`).*

### Step 3: Start with Docker Compose
```bash
docker compose up --build
```

### Step 4: Verify Deployment
Open your browser at:
* **Savanna LMS Course (with Assistant):** [http://localhost:8000/savanna/pages/concept-with-navigation.html](http://localhost:8000/savanna/pages/concept-with-navigation.html)
* **Stage 1 Accessibility Gate Audit:** [http://localhost:8000/a11y-audit](http://localhost:8000/a11y-audit)
* **Curriculum Ingestion Portal:** [http://localhost:8000/admin/ingest](http://localhost:8000/admin/ingest)
* **Teacher Analytics Dashboard:** [http://localhost:8000/analytics](http://localhost:8000/analytics)
* **Low-Bandwidth SMS Simulator:** [http://localhost:8000/sms-simulator](http://localhost:8000/sms-simulator)
* **Interactive OpenAPI Specs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **System Health Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 2. Standard Local Python Deployment (Without Docker)

If running directly in Python:

```bash
# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python -m uvicorn assistant.api.main:app --host 0.0.0.0 --port 8000
```

---

## 3. Free Live Cloud Deployment (For TalkBack Mobile Testing)

To allow judges, co-designers, and mobile testers to interact with the assistant on their own smartphones (especially with Android TalkBack):

### Option A: Deploy on Render (Free & Instant)
1. Go to [render.com](https://render.com) and sign in with GitHub.
2. Click **New +** &rarr; **Web Service**.
3. Select your repository: `fenet-as/accessibility-assistant`.
4. Choose **Docker** as the environment (Render detects `Dockerfile` automatically).
5. Add Environment Variables:
   * `AI_PROVIDER` = `faq` (or `cloud`)
   * `GEMINI_API_KEY` = `your_gemini_api_key`
6. Click **Deploy Web Service**.
7. Render gives you an instant public HTTPS URL (e.g. `https://alx-assistant.onrender.com`).

---

### Option B: Instant Public Tunnel from Laptop (Zero Cloud Setup)
If running locally during the hackathon venue and you need an instant public HTTPS link for your co-designer's phone:

```bash
# Using localtunnel (free, no account needed)
npx localtunnel --port 8000
```
or with ngrok:
```bash
ngrok http 8000
```

Share the generated HTTPS URL with your co-designer so they can test immediately on their own Android or iOS device!
