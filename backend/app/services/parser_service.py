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
  ],
  "skill_importance": {{
    "skill1": "critical",
    "skill2": "important",
    "skill3": "standard"
  }}
}}

Rules:
- Keep required_skills to 5-8 most important skills only, ordered from most to least important
- Only include skills truly required by the JD
- Extract evidence from the resume for each candidate skill
- For skill_importance, classify each required skill as:
    "critical": Core to the role — mentioned multiple times, listed first, described as must-have/expert-level, or central to day-to-day responsibilities
    "important": Clearly required but not the primary focus of the role
    "standard": Required but mentioned briefly or as a supporting/secondary skill
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
