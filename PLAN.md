# Skill Assessment & Learning Plan Agent — Full Implementation + Deployment Plan

## Overview
Standalone AI agent for hackathon submission. Takes a Job Description + Resume, conversationally assesses real skill proficiency via multi-turn chat, identifies gaps, and generates a personalised learning plan with curated free resources and time estimates.

**All resources used are 100% free.**

---

## Tech Stack (Free Only)

| Layer | Technology | Why Free |
|---|---|---|
| LLM | Groq API — `llama-3.3-70b-versatile` | Free tier, no credit card needed |
| Agent Framework | LangGraph (open source) | MIT license |
| Backend | FastAPI + Python 3.11 | Open source |
| PDF Parsing | pdfplumber | Open source |
| Database | SQLite (file-based) | Built-in, zero cost |
| ORM | SQLAlchemy | Open source |
| Frontend | Next.js 15 + TailwindCSS | Open source |
| Charts | Recharts | Open source |
| Backend Deploy | Render.com free tier | Free (sleeps after 15min inactivity) |
| Frontend Deploy | Vercel free tier | Free forever for hobby |
| Repo | GitHub (public) | Free |

---

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
│  POST /api/analyze   → Parse JD + Resume                 │
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

---

## Project Structure

```
skill-assessment-agent/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── render.yaml
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py          # POST /api/analyze
│   │   │   ├── assess.py           # POST /api/assess/message (SSE stream)
│   │   │   └── report.py           # GET /api/report/{session_id}
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── parser_service.py   # Extract skills from JD + resume via Groq
│   │   │   ├── assessment_agent.py # LangGraph graph definition
│   │   │   ├── gap_service.py      # Gap analysis + score classification
│   │   │   └── learning_plan_service.py  # Learning plan generation via Groq
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── db_models.py        # SQLAlchemy models
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── entities.py         # Pydantic schemas
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_parser.py
│       └── test_report.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── .env.local.example
│   ├── Dockerfile
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Step 1: JD + Resume input
│   │   ├── assess/
│   │   │   └── [sessionId]/
│   │   │       └── page.tsx        # Step 2: Chat assessment
│   │   └── report/
│   │       └── [sessionId]/
│   │           └── page.tsx        # Step 3: Report + learning plan
│   └── lib/
│       ├── api.ts                  # API client functions
│       └── types.ts                # TypeScript types
├── docker-compose.yml
├── .env.example                    # root env example
├── README.md
└── PLAN.md                         # this file
```

---

## Backend Implementation Details

### `backend/pyproject.toml`
```toml
[tool.poetry]
name = "skill-assessment-agent"
version = "0.1.0"
description = "AI-powered skill assessment and learning plan agent"
authors = ["Your Name"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
langchain = "^0.3.0"
langchain-groq = "^0.2.0"
langgraph = "^0.2.0"
pdfplumber = "^0.11.0"
sqlalchemy = "^2.0.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
python-multipart = "^0.0.12"
sse-starlette = "^2.1.0"
python-dotenv = "^1.0.0"
aiofiles = "^24.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.24.0"
httpx = "^0.27.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### `backend/.env.example`
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///./skill_assessment.db
CORS_ORIGINS=http://localhost:3000
```

### `backend/config.py`
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    groq_api_key: str
    database_url: str = "sqlite:///./skill_assessment.db"
    cors_origins: List[str] = ["http://localhost:3000"]
    groq_model: str = "llama-3.3-70b-versatile"

    class Config:
        env_file = ".env"

settings = Settings()
```

### `backend/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `backend/app/models/db_models.py`
```python
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    jd_text: Mapped[str] = mapped_column(Text)
    resume_text: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[dict] = mapped_column(JSON)
    candidate_skills: Mapped[dict] = mapped_column(JSON)
    role_context: Mapped[str] = mapped_column(Text, default="")
    seniority: Mapped[str] = mapped_column(String(20), default="Mid")
    status: Mapped[str] = mapped_column(String(20), default="assessing")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="session")
    skill_scores: Mapped[list["SkillScore"]] = relationship("SkillScore", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    session: Mapped["Session"] = relationship("Session", back_populates="messages")

class SkillScore(Base):
    __tablename__ = "skill_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"))
    skill: Mapped[str] = mapped_column(String(100))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    session: Mapped["Session"] = relationship("Session", back_populates="skill_scores")
```

### `backend/app/schemas/entities.py`
```python
from pydantic import BaseModel
from typing import Optional, List

class AnalyzeRequest(BaseModel):
    jd_text: str
    resume_text: str

class CandidateSkill(BaseModel):
    skill: str
    years_experience: Optional[float] = None
    evidence: Optional[str] = None

class AnalyzeResponse(BaseModel):
    session_id: str
    required_skills: List[str]
    candidate_skills: List[CandidateSkill]
    first_message: str

class AssessMessageRequest(BaseModel):
    session_id: str
    message: str

class SkillScoreOut(BaseModel):
    skill: str
    score: float
    status_label: str  # Strong | Adequate | Gap | Critical Gap
    notes: str

class LearningResource(BaseModel):
    title: str
    url: str
    type: str          # course | video | docs | book
    is_free: bool = True

class LearningItem(BaseModel):
    skill: str
    priority: int
    gap_size: str
    estimated_hours: int
    resources: List[LearningResource]
    project_idea: str
    weekly_plan: str

class ReportResponse(BaseModel):
    session_id: str
    overall_score: float
    readiness_label: str  # Not Ready | Partially Ready | Ready
    weeks_to_ready: int
    skill_scores: List[SkillScoreOut]
    learning_plan: List[LearningItem]
```

### `backend/app/services/parser_service.py`
```python
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings

llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)

PARSER_SYSTEM_PROMPT = """You are a technical recruiter and skills analyst.
Extract skills from job descriptions and resumes accurately.
Always respond with valid JSON only, no extra text, no markdown code fences."""

async def parse_jd_and_resume(jd_text: str, resume_text: str) -> dict:
    prompt = f"""
Analyze this Job Description and Resume. Extract skills data as JSON.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Return JSON with this exact structure (no markdown, no code fences, pure JSON only):
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have": ["skill1"],
  "seniority": "Junior|Mid|Senior|Lead",
  "role_context": "brief description of the role",
  "candidate_skills": [
    {{"skill": "name", "years_experience": 2.5, "evidence": "used at X for Y"}}
  ]
}}

Rules:
- Keep required_skills to 5-8 most important skills only
- Only include skills truly required by the JD
- Extract evidence from the resume for each candidate skill
"""
    messages = [SystemMessage(content=PARSER_SYSTEM_PROMPT), HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    content = response.content.strip()
    # Strip markdown fences if model adds them despite instructions
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())
```

### `backend/app/services/assessment_agent.py`
```python
import json
from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from config import settings

llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.3)

class AssessmentState(TypedDict):
    session_id: str
    required_skills: list
    candidate_skills: list
    role_context: str
    seniority: str
    skills_queue: list
    current_skill: str
    questions_asked: int
    conversation_history: list   # [{role, content}]
    skill_scores: dict           # {skill: {score, notes}}
    is_complete: bool

ASSESSMENT_SYSTEM_PROMPT = """You are a senior technical interviewer conducting a skill assessment.
Your goal is to assess a candidate's ACTUAL proficiency, not just what they claim.

Rules:
- Ask practical, scenario-based questions ONLY (never trivia)
- Reference their resume evidence naturally
- Be conversational and encouraging
- Keep questions concise (2-3 sentences max)
- Ask ONE question at a time
- Do NOT reveal the score you are assigning
"""

def build_assessment_graph(db_path: str = "./langgraph_checkpoints.db"):
    def select_next_skill(state: AssessmentState) -> dict:
        if not state["skills_queue"]:
            return {"is_complete": True}
        next_skill = state["skills_queue"][0]
        remaining = state["skills_queue"][1:]
        return {"current_skill": next_skill, "skills_queue": remaining, "questions_asked": 0}

    def ask_question(state: AssessmentState) -> dict:
        skill = state["current_skill"]
        candidate_evidence = next(
            (s.get("evidence", "") for s in state["candidate_skills"]
             if s.get("skill", "").lower() == skill.lower()), ""
        )
        candidate_exp = next(
            (s.get("years_experience", 0) for s in state["candidate_skills"]
             if s.get("skill", "").lower() == skill.lower()), 0
        )
        is_first = state["questions_asked"] == 0
        recent_conv = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in state["conversation_history"][-6:]]
        )

        if is_first:
            prompt = f"""Role context: {state['role_context']} ({state['seniority']} level)
Skill to assess: {skill}
Candidate claimed experience: {candidate_exp} years
Resume evidence: {candidate_evidence or 'None'}
Recent conversation:
{recent_conv}

Generate ONE practical, scenario-based question to assess {skill} proficiency.
Reference resume evidence if available. Make it conversational.
Respond with the question text only."""
        else:
            last_answer = state["conversation_history"][-1]["content"] if state["conversation_history"] else ""
            prompt = f"""Role: {state['role_context']} ({state['seniority']} level)
Current skill: {skill}
Their last answer: {last_answer}

Generate ONE follow-up question that digs deeper into a gap or interesting point.
Keep it brief and conversational. Question text only."""

        messages = [SystemMessage(content=ASSESSMENT_SYSTEM_PROMPT), HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        question = response.content.strip()
        new_history = state["conversation_history"] + [{"role": "assistant", "content": question}]
        return {"conversation_history": new_history}

    def evaluate_answer(state: AssessmentState) -> dict:
        skill = state["current_skill"]
        conversation_context = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in state["conversation_history"][-8:]]
        )
        score_prompt = f"""Evaluate candidate proficiency in: {skill}
Role level: {state['seniority']}

Conversation:
{conversation_context}

Score their DEMONSTRATED proficiency based on all answers.

Rubric:
0-2: No understanding / completely wrong / "I don't know"
3-5: Partial understanding, missing key concepts
6-7: Solid understanding, applies in standard scenarios
8-10: Deep understanding, edge cases, trade-offs, real-world experience

Respond with JSON only (no markdown):
{{"score": 7.5, "notes": "Shows solid understanding of X but gaps in Y", "need_followup": false}}

need_followup = true only if one more question would meaningfully change the score."""

        messages = [HumanMessage(content=score_prompt)]
        response = llm.invoke(messages)
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            evaluation = json.loads(content.strip())
        except Exception:
            evaluation = {"score": 5.0, "notes": "Evaluation parsing error", "need_followup": False}

        updated_scores = {**state["skill_scores"], skill: {
            "score": evaluation.get("score", 5.0),
            "notes": evaluation.get("notes", "")
        }}
        need_followup = evaluation.get("need_followup", False) and state["questions_asked"] < 2
        return {
            "skill_scores": updated_scores,
            "questions_asked": state["questions_asked"] + 1,
            "_need_followup": need_followup
        }

    def route_after_evaluation(state: AssessmentState) -> str:
        if state.get("_need_followup", False):
            return "ask_question"
        if state["skills_queue"]:
            return "select_next_skill"
        return "finalize"

    def finalize(state: AssessmentState) -> dict:
        n = len(state["skill_scores"])
        closing = (
            f"That wraps up our assessment! I've evaluated your proficiency across {n} skill{'s' if n != 1 else ''}. "
            "Your detailed report with skill scores and a personalized learning plan is now ready."
        )
        new_history = state["conversation_history"] + [{"role": "assistant", "content": closing}]
        return {"conversation_history": new_history, "is_complete": True}

    builder = StateGraph(AssessmentState)
    builder.add_node("select_next_skill", select_next_skill)
    builder.add_node("ask_question", ask_question)
    builder.add_node("evaluate_answer", evaluate_answer)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("select_next_skill")
    builder.add_edge("select_next_skill", "ask_question")
    builder.add_edge("ask_question", END)  # Pause here — wait for user response

    builder.add_conditional_edges("evaluate_answer", route_after_evaluation, {
        "ask_question": "ask_question",
        "select_next_skill": "select_next_skill",
        "finalize": "finalize",
    })
    builder.add_edge("finalize", END)

    memory = SqliteSaver.from_conn_string(db_path)
    return builder.compile(checkpointer=memory)


# Singleton graph instance
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_assessment_graph()
    return _graph_instance
```

**Key design**: After `ask_question` the graph hits END and returns to the API with the question. Next time the user replies, the router manually appends their message to `conversation_history` and resumes from `evaluate_answer`.

### `backend/app/services/gap_service.py`
```python
def classify_score(score: float) -> str:
    if score >= 8:
        return "Strong"
    elif score >= 6:
        return "Adequate"
    elif score >= 3:
        return "Gap"
    else:
        return "Critical Gap"

def analyze_gaps(required_skills: list, skill_scores: dict, candidate_skills: list) -> dict:
    results = []
    for skill in required_skills:
        score_data = skill_scores.get(skill, {"score": 0.0, "notes": "Not assessed"})
        score = float(score_data.get("score", 0.0))
        label = classify_score(score)
        results.append({
            "skill": skill,
            "score": score,
            "status_label": label,
            "notes": score_data.get("notes", ""),
            "is_gap": score < 6,
        })

    total = sum(r["score"] for r in results)
    overall = (total / len(results)) if results else 0
    readiness = "Ready" if overall >= 7 else "Partially Ready" if overall >= 5 else "Not Ready"
    return {
        "skill_results": results,
        "overall_score": round(overall * 10),  # 0–100
        "readiness_label": readiness
    }
```

### `backend/app/services/learning_plan_service.py`
```python
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from config import settings

llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.4)

async def generate_learning_plan(gaps: list, candidate_skills: list, role_context: str) -> dict:
    gap_skills = [g for g in gaps if g["is_gap"]]
    gap_skills.sort(key=lambda x: x["score"])  # Critical gaps first

    candidate_skill_names = [s.get("skill", "") for s in candidate_skills]
    plan_items = []
    total_hours = 0

    for i, gap in enumerate(gap_skills):
        prompt = f"""Generate a learning plan for a developer who needs to learn: {gap['skill']}
Current score: {gap['score']}/10 ({gap['status_label']})
Skills they already know (can leverage): {', '.join(candidate_skill_names)}
Target role: {role_context}

Respond with JSON only (no markdown, no code fences):
{{
  "estimated_hours": 40,
  "resources": [
    {{"title": "Resource Name", "url": "https://example.com", "type": "course", "is_free": true}},
    {{"title": "Resource Name", "url": "https://example.com", "type": "video", "is_free": true}},
    {{"title": "Resource Name", "url": "https://example.com", "type": "docs", "is_free": true}}
  ],
  "project_idea": "Build X to practice Y",
  "weekly_plan": "Week 1: Cover fundamentals. Week 2: Build project."
}}

IMPORTANT:
- Only FREE resources: official docs, YouTube, freeCodeCamp, The Odin Project, MDN, etc.
- Use real, accurate URLs
- Reduce estimated_hours if candidate has adjacent skills"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            item = json.loads(content.strip())
            item["skill"] = gap["skill"]
            item["priority"] = i + 1
            item["gap_size"] = gap["status_label"]
            plan_items.append(item)
            total_hours += item.get("estimated_hours", 40)
        except Exception:
            continue

    weeks_to_ready = max(1, round(total_hours / 10))
    return {"learning_plan": plan_items, "weeks_to_ready": weeks_to_ready, "total_hours": total_hours}
```

### `backend/app/routers/analyze.py`
```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DBSessionType
import pdfplumber
import io
from database import get_db
from app.models.db_models import Session as DBSession, SkillScore
from app.schemas.entities import AnalyzeRequest, AnalyzeResponse
from app.services.parser_service import parse_jd_and_resume
from app.services.assessment_agent import get_graph

router = APIRouter()

@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, db: DBSessionType = Depends(get_db)):
    try:
        parsed = await parse_jd_and_resume(request.jd_text, request.resume_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse JD/Resume: {str(e)}")

    session_id = str(uuid.uuid4())
    required_skills = parsed.get("required_skills", [])
    candidate_skills = parsed.get("candidate_skills", [])

    db_session = DBSession(
        id=session_id,
        jd_text=request.jd_text,
        resume_text=request.resume_text,
        required_skills=required_skills,
        candidate_skills=candidate_skills,
        role_context=parsed.get("role_context", ""),
        seniority=parsed.get("seniority", "Mid"),
        status="assessing"
    )
    db.add(db_session)
    for skill in required_skills:
        db.add(SkillScore(session_id=session_id, skill=skill))
    db.commit()

    # Initialize LangGraph and get first question
    initial_state = {
        "session_id": session_id,
        "required_skills": required_skills,
        "candidate_skills": candidate_skills,
        "role_context": parsed.get("role_context", ""),
        "seniority": parsed.get("seniority", "Mid"),
        "skills_queue": required_skills[1:] if len(required_skills) > 1 else [],
        "current_skill": required_skills[0] if required_skills else "",
        "questions_asked": 0,
        "conversation_history": [],
        "skill_scores": {},
        "is_complete": False,
        "_need_followup": False,
    }

    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()
    result = await graph.ainvoke(initial_state, config=config)
    first_message = result["conversation_history"][-1]["content"] if result["conversation_history"] else "Let's begin your assessment!"

    return AnalyzeResponse(
        session_id=session_id,
        required_skills=required_skills,
        candidate_skills=[{"skill": s.get("skill", ""), "years_experience": s.get("years_experience"), "evidence": s.get("evidence")} for s in candidate_skills],
        first_message=first_message,
    )

@router.post("/api/analyze/pdf")
async def analyze_pdf(
    jd_text: str = Form(...),
    resume_file: UploadFile = File(...),
    db: DBSessionType = Depends(get_db)
):
    content = await resume_file.read()
    resume_text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            resume_text += page.extract_text() or ""
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")
    return await analyze(AnalyzeRequest(jd_text=jd_text, resume_text=resume_text), db)
```

### `backend/app/routers/assess.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSessionType
import json
from database import get_db
from app.models.db_models import Session as DBSession, Message, SkillScore
from app.schemas.entities import AssessMessageRequest
from app.services.assessment_agent import get_graph

router = APIRouter()

@router.post("/api/assess/message")
async def send_message(request: AssessMessageRequest, db: DBSessionType = Depends(get_db)):
    db_session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status == "complete":
        raise HTTPException(status_code=400, detail="Assessment already complete")

    # Persist user message
    db.add(Message(session_id=request.session_id, role="user", content=request.message))
    db.commit()

    graph = get_graph()
    config = {"configurable": {"thread_id": request.session_id}}

    async def generate():
        # Get current graph state
        current_state = await graph.aget_state(config)
        state_values = dict(current_state.values)

        # Append user message to history
        updated_history = state_values.get("conversation_history", []) + [
            {"role": "user", "content": request.message}
        ]

        # Update state to include user message, then resume at evaluate_answer
        await graph.aupdate_state(config, {"conversation_history": updated_history})

        # Re-invoke from evaluate_answer node
        result = await graph.ainvoke(None, config=config)

        is_complete = result.get("is_complete", False)

        # Get the last assistant message (new question or closing)
        history = result.get("conversation_history", [])
        last_assistant = next(
            (m["content"] for m in reversed(history) if m["role"] == "assistant"),
            ""
        )

        # Persist agent message
        if last_assistant:
            db.add(Message(session_id=request.session_id, role="assistant", content=last_assistant))

        # Update skill scores in DB
        for skill, score_data in result.get("skill_scores", {}).items():
            db_score = db.query(SkillScore).filter(
                SkillScore.session_id == request.session_id,
                SkillScore.skill == skill
            ).first()
            if db_score:
                db_score.score = float(score_data.get("score", 0.0))
                db_score.notes = score_data.get("notes", "")
                db_score.status = "assessed"

        if is_complete:
            db_session.status = "complete"

        db.commit()

        # Stream the response token by token (simulate streaming for smooth UX)
        words = last_assistant.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'token': chunk, 'is_complete': False})}\n\n"

        yield f"data: {json.dumps({'token': '', 'is_complete': is_complete})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/api/assess/state/{session_id}")
async def get_state(session_id: str, db: DBSessionType = Depends(get_db)):
    """Get current session state — useful for reconnecting after page refresh."""
    db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id).all()
    return {
        "session_id": session_id,
        "status": db_session.status,
        "required_skills": db_session.required_skills,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }
```

### `backend/app/routers/report.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSessionType
from database import get_db
from app.models.db_models import Session as DBSession, SkillScore
from app.schemas.entities import ReportResponse
from app.services.gap_service import analyze_gaps
from app.services.learning_plan_service import generate_learning_plan

router = APIRouter()

@router.get("/api/report/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str, db: DBSessionType = Depends(get_db)):
    db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    scores = db.query(SkillScore).filter(SkillScore.session_id == session_id).all()
    skill_scores_dict = {s.skill: {"score": s.score, "notes": s.notes} for s in scores}

    gap_analysis = analyze_gaps(db_session.required_skills, skill_scores_dict, db_session.candidate_skills)
    learning_data = await generate_learning_plan(
        gap_analysis["skill_results"],
        db_session.candidate_skills,
        db_session.role_context or "",
    )

    return ReportResponse(
        session_id=session_id,
        overall_score=gap_analysis["overall_score"],
        readiness_label=gap_analysis["readiness_label"],
        weeks_to_ready=learning_data["weeks_to_ready"],
        skill_scores=gap_analysis["skill_results"],
        learning_plan=learning_data["learning_plan"],
    )
```

### `backend/app/routers/__init__.py`
```python
# empty
```

### `backend/app/services/__init__.py`
```python
# empty
```

### `backend/app/models/__init__.py`
```python
# empty
```

### `backend/app/schemas/__init__.py`
```python
# empty
```

### `backend/app/__init__.py`
```python
# empty
```

### `backend/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from app.models.db_models import Base
from app.routers import analyze, assess, report
from config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Skill Assessment Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(assess.router)
app.include_router(report.router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/render.yaml`
```yaml
services:
  - type: web
    name: skill-assessment-api
    runtime: python
    buildCommand: pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: CORS_ORIGINS
        value: https://your-vercel-app.vercel.app
      - key: DATABASE_URL
        value: sqlite:///./skill_assessment.db
```

### `backend/tests/conftest.py`
```python
import pytest
from fastapi.testclient import TestClient
import os
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from main import app

@pytest.fixture
def client():
    return TestClient(app)
```

### `backend/tests/test_report.py`
```python
def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_report_not_found(client):
    res = client.get("/api/report/nonexistent-session-id")
    assert res.status_code == 404

def test_analyze_missing_body(client):
    res = client.post("/api/analyze", json={})
    assert res.status_code == 422
```

### `backend/tests/__init__.py`
```python
# empty
```

---

## Frontend Implementation Details

### `frontend/package.json`
```json
{
  "name": "skill-assessment-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "recharts": "^2.13.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "typescript": "^5",
    "tailwindcss": "^3.4.0",
    "postcss": "^8",
    "autoprefixer": "^10"
  }
}
```

### `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### `frontend/next.config.ts`
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {};

export default nextConfig;
```

### `frontend/tailwind.config.ts`
```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: { extend: {} },
  plugins: [],
};

export default config;
```

### `frontend/postcss.config.mjs`
```javascript
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
```

### `frontend/.env.local.example`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### `frontend/app/globals.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### `frontend/lib/types.ts`
```typescript
export interface CandidateSkill {
  skill: string;
  years_experience?: number;
  evidence?: string;
}

export interface AnalyzeResponse {
  session_id: string;
  required_skills: string[];
  candidate_skills: CandidateSkill[];
  first_message: string;
}

export interface SkillScore {
  skill: string;
  score: number;
  status_label: 'Strong' | 'Adequate' | 'Gap' | 'Critical Gap';
  notes: string;
}

export interface LearningResource {
  title: string;
  url: string;
  type: 'course' | 'video' | 'docs' | 'book';
  is_free: boolean;
}

export interface LearningItem {
  skill: string;
  priority: number;
  gap_size: string;
  estimated_hours: number;
  resources: LearningResource[];
  project_idea: string;
  weekly_plan: string;
}

export interface ReportResponse {
  session_id: string;
  overall_score: number;
  readiness_label: string;
  weeks_to_ready: number;
  skill_scores: SkillScore[];
  learning_plan: LearningItem[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}
```

### `frontend/lib/api.ts`
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function analyzeInput(jdText: string, resumeText: string) {
  const res = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_text: jdText, resume_text: resumeText }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Analysis failed');
  }
  return res.json();
}

export async function* sendMessage(sessionId: string, message: string): AsyncGenerator<{ token: string; is_complete: boolean }> {
  const res = await fetch(`${API_URL}/api/assess/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error('Message failed');

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const parsed = JSON.parse(line.slice(6));
          yield parsed;
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function getReport(sessionId: string) {
  const res = await fetch(`${API_URL}/api/report/${sessionId}`);
  if (!res.ok) throw new Error('Report not found');
  return res.json();
}

export async function getSessionState(sessionId: string) {
  const res = await fetch(`${API_URL}/api/assess/state/${sessionId}`);
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}
```

### `frontend/app/layout.tsx`
```tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Skill Assessment Agent',
  description: 'AI-powered skill assessment and personalized learning plans — free for everyone',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
```

### `frontend/app/page.tsx`
```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeInput } from '@/lib/api';

export default function HomePage() {
  const router = useRouter();
  const [jdText, setJdText] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!jdText.trim() || !resumeText.trim()) {
      setError('Please fill in both fields.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await analyzeInput(jdText, resumeText);
      const params = new URLSearchParams({
        first: data.first_message,
        skills: JSON.stringify(data.required_skills),
      });
      router.push(`/assess/${data.session_id}?${params.toString()}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to analyze. Please try again.');
      setLoading(false);
    }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Skill Assessment Agent</h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Paste a job description and your resume. Our AI interviewer will assess your real proficiency
          through conversation and generate a personalized learning plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 rounded-2xl border border-gray-200 shadow-sm">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Job Description <span className="text-red-500">*</span>
          </label>
          <textarea
            value={jdText}
            onChange={e => setJdText(e.target.value)}
            placeholder="Paste the full job description here..."
            rows={8}
            className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm text-gray-800"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Your Resume <span className="text-red-500">*</span>
          </label>
          <textarea
            value={resumeText}
            onChange={e => setResumeText(e.target.value)}
            placeholder="Paste your resume text here (copy-paste from PDF or Word)..."
            rows={8}
            className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm text-gray-800"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl transition-colors text-base"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Analyzing your profile...
            </span>
          ) : 'Start Skill Assessment'}
        </button>
      </form>

      <div className="mt-10 grid grid-cols-3 gap-4 text-center">
        {[
          { step: '1', title: 'Input', desc: 'Paste JD + Resume' },
          { step: '2', title: 'Assess', desc: 'Chat with AI interviewer' },
          { step: '3', title: 'Report', desc: 'Get your learning plan' },
        ].map(item => (
          <div key={item.step} className="p-5 bg-white rounded-xl border border-gray-200">
            <div className="w-9 h-9 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold mx-auto mb-3 text-sm">
              {item.step}
            </div>
            <h3 className="font-semibold text-gray-900 text-sm">{item.title}</h3>
            <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
```

### `frontend/app/assess/[sessionId]/page.tsx`
```tsx
'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { sendMessage } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';

export default function AssessPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId as string;

  const firstMessage = searchParams.get('first') || '';
  const skillsParam = searchParams.get('skills') || '[]';
  const skills: string[] = JSON.parse(decodeURIComponent(skillsParam));

  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: firstMessage }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [assessedCount, setAssessedCount] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  async function handleSend() {
    if (!input.trim() || loading || isComplete) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    // Add placeholder for streaming response
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    let assistantContent = '';
    let done = false;

    try {
      for await (const chunk of sendMessage(sessionId, userMessage)) {
        if (chunk.token) {
          assistantContent += chunk.token;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: 'assistant', content: assistantContent, streaming: true };
            return updated;
          });
        }
        if (chunk.is_complete) {
          done = true;
        }
      }
    } catch (err) {
      console.error('Assessment error:', err);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' };
        return updated;
      });
    }

    // Mark streaming done
    setMessages(prev => {
      const updated = [...prev];
      if (updated[updated.length - 1].role === 'assistant') {
        updated[updated.length - 1] = { role: 'assistant', content: assistantContent };
      }
      return updated;
    });

    if (done) {
      setIsComplete(true);
      setAssessedCount(skills.length);
    } else {
      // Rough tracking: count agent turns as skill transitions
      setAssessedCount(prev => Math.min(prev + 0.5, skills.length - 1));
    }

    setLoading(false);
  }

  const progress = skills.length > 0 ? Math.round((assessedCount / skills.length) * 100) : 0;

  return (
    <main className="max-w-3xl mx-auto px-4 py-6 flex flex-col" style={{ height: '100dvh' }}>
      {/* Header */}
      <div className="mb-4 flex-shrink-0">
        <div className="flex justify-between items-center mb-2">
          <h1 className="text-sm font-semibold text-gray-700">Skill Assessment</h1>
          <span className="text-xs text-gray-400">{Math.round(assessedCount)}/{skills.length} skills</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${Math.max(5, progress)}%` }}
          />
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          {skills.map(s => (
            <span key={s} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">{s}</span>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
            }`}>
              {msg.content ? msg.content : (
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}/>
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}/>
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}/>
                </span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 pt-4 border-t border-gray-200">
        {isComplete ? (
          <div className="text-center space-y-2">
            <p className="text-sm text-gray-500">Assessment complete!</p>
            <button
              onClick={() => router.push(`/report/${sessionId}`)}
              className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-colors"
            >
              View My Report & Learning Plan
            </button>
          </div>
        ) : (
          <div className="flex gap-3">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={loading ? 'Waiting for response...' : 'Type your answer...'}
              disabled={loading}
              className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:bg-gray-50 disabled:text-gray-400"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-200 text-white font-semibold rounded-xl transition-colors text-sm"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
```

### `frontend/app/report/[sessionId]/page.tsx`
```tsx
'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { ReportResponse } from '@/lib/types';

const STATUS_COLORS: Record<string, string> = {
  'Strong': '#16a34a',
  'Adequate': '#2563eb',
  'Gap': '#d97706',
  'Critical Gap': '#dc2626',
};

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getReport(sessionId)
      .then(setReport)
      .catch(() => setError('Failed to load report. Please try again.'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-screen gap-3">
      <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <p className="text-gray-500 text-sm">Generating your personalized report...</p>
    </div>
  );

  if (error || !report) return (
    <div className="flex flex-col items-center justify-center h-screen gap-3">
      <p className="text-red-500">{error || 'Report not found.'}</p>
      <button onClick={() => router.push('/')} className="text-blue-600 hover:underline text-sm">Start new assessment</button>
    </div>
  );

  const readinessColor = report.readiness_label === 'Ready' ? 'text-green-600'
    : report.readiness_label === 'Partially Ready' ? 'text-yellow-600'
    : 'text-red-600';

  return (
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Your Skill Assessment Report</h1>
        <p className="text-gray-500">Here is your personalized skill analysis and learning plan.</p>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className="text-4xl font-bold text-blue-600">{report.overall_score}%</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Overall Readiness</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className={`text-2xl font-bold ${readinessColor}`}>{report.readiness_label}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Status</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className="text-4xl font-bold text-orange-500">{report.weeks_to_ready}w</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Weeks to Job-Ready</div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-5">Skill Scores</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={report.skill_scores} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="skill" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(val: number) => [`${val.toFixed(1)}/10`, 'Score']} />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {report.skill_scores.map((entry, i) => (
                <Cell key={i} fill={STATUS_COLORS[entry.status_label] || '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-3 justify-center flex-wrap">
          {Object.entries(STATUS_COLORS).map(([label, color]) => (
            <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* Skill Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 px-6 pt-6 pb-3">Skill Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Skill</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Score</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {report.skill_scores.map(skill => (
                <tr key={skill.skill} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-medium text-gray-900">{skill.skill}</td>
                  <td className="px-6 py-4 text-gray-700">{skill.score.toFixed(1)}/10</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold" style={{
                      backgroundColor: (STATUS_COLORS[skill.status_label] || '#6b7280') + '18',
                      color: STATUS_COLORS[skill.status_label] || '#6b7280'
                    }}>
                      {skill.status_label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs max-w-xs">{skill.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Learning Plan */}
      {report.learning_plan.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Personalized Learning Plan</h2>
          <div className="space-y-3">
            {report.learning_plan.map(item => (
              <details key={item.skill} className="bg-white rounded-2xl border border-gray-200 shadow-sm group">
                <summary className="p-5 cursor-pointer list-none flex justify-between items-center hover:bg-gray-50 rounded-2xl">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                      {item.priority}
                    </span>
                    <span className="font-semibold text-gray-900">{item.skill}</span>
                    <span className="px-2 py-0.5 rounded text-xs font-medium" style={{
                      backgroundColor: (STATUS_COLORS[item.gap_size] || '#6b7280') + '18',
                      color: STATUS_COLORS[item.gap_size] || '#6b7280'
                    }}>
                      {item.gap_size}
                    </span>
                  </div>
                  <span className="text-sm text-gray-400 flex-shrink-0">{item.estimated_hours}h</span>
                </summary>
                <div className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-4">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Free Resources</h4>
                    <ul className="space-y-1.5">
                      {item.resources?.map((r, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-medium flex-shrink-0">{r.type}</span>
                          <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate">
                            {r.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Project Idea</h4>
                    <p className="text-sm text-gray-600">{item.project_idea}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Study Plan</h4>
                    <p className="text-sm text-gray-600">{item.weekly_plan}</p>
                  </div>
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      <div className="text-center pb-8">
        <button onClick={() => router.push('/')} className="text-sm text-gray-400 hover:text-gray-600 hover:underline">
          Start a new assessment
        </button>
      </div>
    </main>
  );
}
```

### `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /app
COPY package.json ./
RUN pnpm install
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]
```

---

## Docker Compose

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - CORS_ORIGINS=http://localhost:3000
      - DATABASE_URL=sqlite:///./skill_assessment.db
    volumes:
      - ./backend:/app
      - backend_data:/app/data

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  backend_data:
```

### `.env.example` (root)
```
GROQ_API_KEY=your_groq_api_key_here
```

---

## README.md Content

### Structure:
```markdown
# Skill Assessment Agent

AI-powered skill assessment and personalized learning plan generator.
Paste a Job Description + Resume → conversational AI interview → gap analysis → free learning resources.

## Demo
[Link to deployed app]

## Architecture
[ASCII diagram]

## Tech Stack
[Table]

## Local Setup
1. Get free Groq API key at https://console.groq.com
2. Clone repo
3. cp .env.example .env && edit GROQ_API_KEY
4. docker-compose up --build
   OR:
   cd backend && poetry install && poetry run uvicorn main:app --reload --port 8000
   cd frontend && pnpm install && pnpm dev

## Deployment
Backend → Render.com (free tier)
Frontend → Vercel (free tier)
[Step-by-step instructions]

## How Scoring Works
[Rubric table]

## Sample Input/Output
[JD + Resume examples and expected report]
```

---

## Deployment Steps

### Backend → Render.com
1. Push repo to GitHub (public)
2. render.com → New Web Service → connect repo → Root dir: `backend`
3. Build: `pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Env vars: `GROQ_API_KEY` (from console.groq.com), `CORS_ORIGINS` (fill in after Vercel deploy)
6. Note backend URL

### Frontend → Vercel
1. vercel.com → New Project → import repo → Root dir: `frontend`
2. Env var: `NEXT_PUBLIC_API_URL=<render-backend-url>`
3. Deploy → note Vercel URL

### Update CORS
- Render dashboard → backend service → env vars → set `CORS_ORIGINS=<vercel-url>`
- Manual redeploy

---

## Build Order for Implementation

Execute strictly in this order:

1. `git init` in `/Users/faizahmad/github/skill-assessment-agent`
2. Create `backend/` directory with all files
3. Create `frontend/` directory — use `pnpm create next-app@latest . --typescript --tailwind --app --no-src-dir` inside `frontend/`
4. Overwrite generated Next.js files with the implementations above
5. Add `recharts` and `lucide-react` to frontend dependencies
6. Create `docker-compose.yml`, `README.md`, `.env.example` at root
7. Run `cd backend && poetry install` to verify backend deps resolve
8. Run `cd frontend && pnpm install` to verify frontend deps resolve
9. Verify `cd backend && poetry run uvicorn main:app --reload` starts without import errors (will fail if no .env — that's ok)
