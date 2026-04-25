# Skill Assessment Agent

AI-powered skill assessment and personalized learning plan generator. Paste a Job Description + Resume, get assessed through a conversational AI interview, receive a gap analysis, and a curated free learning plan.

## Demo

[Deploy to get your link — see Deployment section below]

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                   │
│  [JD + Resume Input] → [Chat Interface] → [Report View] │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / SSE (streaming)
┌──────────────────────────▼──────────────────────────────┐
│                   Backend (FastAPI)                      │
│                                                          │
│  POST /api/analyze        → Parse JD + Resume            │
│  POST /api/assess/message → LangGraph agent (SSE)        │
│  GET  /api/report/{id}    → Gap analysis + plan          │
└──────────┬────────────────────────┬─────────────────────┘
           │                        │
    ┌──────▼──────┐        ┌────────▼────────┐
    │  Groq API   │        │  SQLite (file)  │
    │ llama-3.3   │        │  + LangGraph    │
    │  -70b-ver.  │        │  checkpointer   │
    └─────────────┘        └─────────────────┘
```

## Tech Stack

| Layer | Technology | Why Free |
|---|---|---|
| LLM | Groq API — `llama-3.3-70b-versatile` | Free tier, no credit card needed |
| Agent Framework | LangGraph (open source) | MIT license |
| Backend | FastAPI + Python 3.11 | Open source |
| PDF Parsing | pdfplumber | Open source |
| Database | SQLite (file-based) | Built-in, zero cost |
| ORM | SQLAlchemy | Open source |
| Frontend | Next.js + TailwindCSS | Open source |
| Charts | Recharts | Open source |
| Backend Deploy | Render.com free tier | Free (sleeps after 15min inactivity) |
| Frontend Deploy | Vercel free tier | Free forever for hobby |

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- pnpm (`npm install -g pnpm`)
- Poetry (`pip install poetry`)
- Free Groq API key from [console.groq.com](https://console.groq.com)

### Method 1: Docker Compose (recommended)

```bash
git clone <this-repo>
cd skill-assessment-agent
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
docker-compose up --build
```

Then open http://localhost:3000

### Method 2: Manual

**Backend:**
```bash
cd backend
cp .env.example .env
# Edit .env: set GROQ_API_KEY=your_key_here
poetry install
poetry run uvicorn main:app --reload --port 8000
```

**Frontend** (in a new terminal):
```bash
cd frontend
cp .env.local.example .env.local
# .env.local already points to http://localhost:8000
pnpm install
pnpm dev
```

Open http://localhost:3000

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Get free at console.groq.com |
| `DATABASE_URL` | No | `sqlite:///./skill_assessment.db` | SQLite path |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL |

## Deployment

### Backend → Render.com (free tier)

1. Push this repo to GitHub (make it public for Render free tier)
2. Go to [render.com](https://render.com) → New Web Service → connect your repo
3. Set **Root Directory**: `backend`
4. **Build Command**: `pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev`
5. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add **Environment Variables**:
   - `GROQ_API_KEY` → your key from console.groq.com
   - `DATABASE_URL` → `sqlite:///./skill_assessment.db`
   - `CORS_ORIGINS` → (fill in after Vercel deploy, e.g. `https://your-app.vercel.app`)
7. Deploy → copy the Render URL (e.g. `https://skill-assessment-api.onrender.com`)

### Frontend → Vercel (free tier)

1. Go to [vercel.com](https://vercel.com) → New Project → import your repo
2. Set **Root Directory**: `frontend`
3. Add **Environment Variable**:
   - `NEXT_PUBLIC_API_URL` → your Render backend URL
4. Deploy → copy the Vercel URL

### Update CORS After Both Deploys

Go to Render dashboard → your backend service → Environment → update `CORS_ORIGINS` to your Vercel URL → Manual Redeploy.

## How Scoring Works

Each skill is assessed through conversational questions and scored 0–10:

| Score | Label | Meaning |
|---|---|---|
| 8–10 | Strong | Deep understanding, edge cases, trade-offs, real-world experience |
| 6–7 | Adequate | Solid understanding, applies in standard scenarios |
| 3–5 | Gap | Partial understanding, missing key concepts |
| 0–2 | Critical Gap | No understanding / completely wrong / "I don't know" |

**Overall readiness** is the average score across all required skills:
- >= 7.0 average → **Ready**
- >= 5.0 average → **Partially Ready**
- < 5.0 average → **Not Ready**

The overall score displayed as a percentage = `average_score * 10`.

## Sample Input / Output

### Sample Job Description
```
Senior Python Backend Engineer
Requirements:
- 4+ years Python experience
- FastAPI or Django REST framework
- PostgreSQL and Redis
- Docker and Kubernetes
- Experience with async programming
```

### Sample Resume
```
Jane Doe — Backend Engineer (3 years)
- Built REST APIs with FastAPI serving 50k req/day
- PostgreSQL database design and query optimization
- Deployed services with Docker; limited Kubernetes experience
- Python asyncio for background tasks
```

### Expected Report Output
- **Python**: 8.5/10 — Strong (3 years hands-on FastAPI)
- **FastAPI**: 8.0/10 — Strong
- **PostgreSQL**: 7.5/10 — Adequate
- **Redis**: 2.0/10 — Critical Gap (not mentioned in resume)
- **Kubernetes**: 4.0/10 — Gap (limited experience)

**Overall**: 60% — Partially Ready — 6 weeks to job-ready

**Learning Plan** includes:
- Redis: Redis University (free), official docs, project idea to build a rate limiter
- Kubernetes: KodeKloud free tier, Kubernetes docs, project to deploy their FastAPI app

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze` | Parse JD + Resume, create session, return first question |
| POST | `/api/analyze/pdf` | Same but accepts a PDF file upload for the resume |
| POST | `/api/assess/message` | Send answer, get next question (SSE streaming) |
| GET | `/api/assess/state/{id}` | Get session state (for page refresh reconnection) |
| GET | `/api/report/{id}` | Get full report with gap analysis and learning plan |
| GET | `/health` | Health check |
