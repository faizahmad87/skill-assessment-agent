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
) -> str:
    """Generate the opening question for a skill."""
    evidence = next(
        (s.get("evidence", "") for s in candidate_skills if s.get("skill", "").lower() == skill.lower()), ""
    )
    exp = next(
        (s.get("years_experience", 0) for s in candidate_skills if s.get("skill", "").lower() == skill.lower()), 0
    )
    recent = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_history[-4:]])

    prompt = f"""Role: {role_context} ({seniority} level)
Skill to assess now: {skill}
Candidate's claimed experience: {exp} years
Resume evidence: {evidence or 'Not mentioned'}
Recent conversation context:
{recent or '(start of assessment)'}

Generate ONE practical scenario-based question to assess their {skill} proficiency.
If they mentioned evidence, reference it naturally.
Return the question text only."""

    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()


async def generate_followup_question(
    skill: str,
    last_answer: str,
    role_context: str,
    seniority: str,
) -> str:
    """Generate a follow-up question to probe deeper on the current skill."""
    prompt = f"""Role: {role_context} ({seniority} level)
Current skill being assessed: {skill}
Candidate's last answer: {last_answer}

Generate ONE brief follow-up question that probes a gap or interesting point in their answer.
Keep it conversational. Return the question text only."""

    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()


async def evaluate_answer(
    skill: str,
    conversation_history: list,
    seniority: str,
) -> dict:
    """
    Score the candidate's demonstrated proficiency for the current skill.
    Returns: {score: float, notes: str, need_followup: bool}
    """
    conv = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in conversation_history[-10:]])

    prompt = f"""Evaluate candidate proficiency in: {skill}
Expected level: {seniority}

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

Set need_followup=true ONLY if one more question would meaningfully change the score."""

    response = await llm_eval.ainvoke([HumanMessage(content=prompt)])
    try:
        return json.loads(_strip_fences(response.content))
    except Exception:
        return {"score": 5.0, "notes": "Could not evaluate response", "need_followup": False}


async def generate_transition(next_skill: str) -> str:
    """Brief acknowledgement before moving to the next skill."""
    prompt = f"""You just finished assessing one skill in a technical interview. Now moving to: {next_skill}.
Write one brief, natural sentence to transition — acknowledge the previous answer and introduce the next topic.
Under 20 words. Return only the sentence."""
    response = await llm.ainvoke([SystemMessage(content=INTERVIEWER_PROMPT), HumanMessage(content=prompt)])
    return response.content.strip()
