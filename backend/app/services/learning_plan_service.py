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
