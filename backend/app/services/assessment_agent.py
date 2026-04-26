"""
Assessment agent — pure async LLM functions, no LangGraph.
State is stored in SQLite (session.assessment_state) and managed by the router.
"""
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings

llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.3)
llm_eval = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)

INTERVIEWER_PROMPT = """You are a senior technical interviewer conducting a conversational skill assessment.
Rules:
- Ask practical, scenario-based questions ONLY (no trivia, no "what does X stand for?")
- Reference the candidate's resume evidence naturally when relevant
- Be encouraging and conversational, not robotic
- Keep questions concise (2-3 sentences max)
- ONE question at a time
- Do NOT reveal any score or grading"""

_SENIORITY_DIFFICULTY = {
    "Junior": "Foundational — test if they understand the concept and can apply it in a basic scenario",
    "Mid": "Practical — test how they use it day-to-day; expect working knowledge with common patterns",
    "Senior": "Complex — immediately test real-world scenarios, trade-offs, and edge cases",
    "Lead": "Strategic — test architectural decisions, team impact, and systemic thinking",
}

_DIFFICULTY_LEVELS = {
    2: "Intermediate — test practical application or a common edge case they may have glossed over",
    3: "Advanced — test a harder scenario, trade-offs, or failure modes",
    4: "Expert — test architectural decisions, performance implications, or real-world complexity",
    5: "Deep expert — test nuanced understanding: 'what would you do if X breaks / scales / changes'",
}

_ADAPTIVE_INSTRUCTION = {
    "struggling": "Candidate is struggling (score < 4) — keep difficulty similar, try approaching the concept from a different angle",
    "partial": "Candidate shows partial understanding (score 4–6) — probe the specific gaps you observed in their answers",
    "strong": "Candidate is performing well (score ≥ 7) — push harder, test edge cases and failure scenarios they haven't addressed",
}

MAX_QUESTIONS_MAP = {"critical": 5, "important": 4, "standard": 3}


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def generate_first_question(
    skill: str,
    candidate_skills: list,
    role_context: str,
    seniority: str,
    recent_history: list,
    max_questions: int = 3,
    skill_importance: str = "standard",
) -> str:
    """Generate the opening question for a skill, calibrated to seniority and importance."""
    evidence = next(
        (s.get("evidence", "") for s in candidate_skills if s.get("skill", "").lower() == skill.lower()), ""
    )
    exp = next(
        (s.get("years_experience", 0) for s in candidate_skills if s.get("skill", "").lower() == skill.lower()), 0
    )
    recent = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_history[-4:]])
    difficulty = _SENIORITY_DIFFICULTY.get(seniority, _SENIORITY_DIFFICULTY["Mid"])

    prompt = f"""Role: {role_context} ({seniority} level)
Skill to assess: {skill} (Importance in this role: {skill_importance})
Candidate's claimed experience: {exp} years
Resume evidence: {evidence or 'Not mentioned'}
Recent conversation context:
{recent or '(start of assessment)'}

This is question 1 of {max_questions} for {skill}.
Difficulty for this question: {difficulty}

Generate ONE practical scenario-based question to assess their {skill} proficiency.
If they mentioned resume evidence, reference it naturally.
Return the question text only — no preamble, no explanation."""

    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()


async def generate_followup_question(
    skill: str,
    question_number: int,
    max_questions: int,
    skill_conversation_history: list,
    role_context: str,
    seniority: str,
    skill_importance: str,
    current_score: float,
) -> str:
    """Generate a follow-up question with progressive difficulty and full skill context."""
    conv = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in skill_conversation_history])

    difficulty = _DIFFICULTY_LEVELS.get(question_number, _DIFFICULTY_LEVELS[3])

    if current_score < 4:
        adaptive = _ADAPTIVE_INSTRUCTION["struggling"]
    elif current_score < 7:
        adaptive = _ADAPTIVE_INSTRUCTION["partial"]
    else:
        adaptive = _ADAPTIVE_INSTRUCTION["strong"]

    prompt = f"""Role: {role_context} ({seniority} level)
Skill being assessed: {skill} (Importance: {skill_importance})
This is question {question_number} of {max_questions} for this skill.

Conversation so far on {skill}:
{conv}

Candidate's current estimated score: {current_score}/10
Difficulty for this question: {difficulty}
Adaptive guidance: {adaptive}

Rules:
- Test a DIFFERENT aspect of {skill} than what has already been covered above
- Start with ONE brief natural acknowledgment of their previous answer (max 1 sentence), then ask the question
- Keep it conversational and specific to the role context
- Do NOT repeat or rephrase a question already asked

Return only the acknowledgment sentence + question text."""

    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()


async def evaluate_answer(
    skill: str,
    conversation_history: list,
    seniority: str,
    skill_importance: str = "standard",
    questions_asked: int = 1,
    max_questions: int = 3,
) -> dict:
    """
    Score the candidate's demonstrated proficiency for the current skill.
    Returns: {score: float, notes: str, need_followup: bool}
    """
    conv = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in conversation_history[-10:]])
    max_q = MAX_QUESTIONS_MAP.get(skill_importance, 3)

    prompt = f"""Evaluate candidate proficiency in: {skill}
Expected level: {seniority}
Skill importance in this role: {skill_importance}
Questions asked so far: {questions_asked} of {max_q}

Conversation:
{conv}

Score their DEMONSTRATED proficiency based on all answers so far.

Rubric:
0-2: No understanding / wrong / "I don't know"
3-5: Partial — knows basics but missing key concepts
6-7: Solid — applies correctly in standard scenarios
8-10: Deep — handles edge cases, explains trade-offs, real experience

Respond with JSON only (no markdown, no fences):
{{"score": 7.0, "notes": "Solid understanding of X, gap in Y", "need_followup": false}}

Set need_followup=true ONLY if:
- There are meaningful gaps still worth exploring, AND
- questions_asked < {max_q} (there are remaining question slots)
For critical skills, be more likely to recommend follow-up to probe depth."""

    response = await llm_eval.ainvoke([HumanMessage(content=prompt)])
    try:
        return json.loads(_strip_fences(response.content))
    except Exception:
        return {"score": 5.0, "notes": "Could not evaluate response", "need_followup": False}


async def generate_transition(next_skill: str) -> str:
    """Brief acknowledgement before moving to the next skill."""
    prompt = f"""You just finished assessing one skill in a technical interview. Now moving to: {next_skill}.
Write one brief, natural sentence to transition — acknowledge the previous topic positively and introduce the next one.
Under 20 words. Return only the sentence."""
    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()
