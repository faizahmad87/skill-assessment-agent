from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSessionType
import json
from database import get_db, SessionLocal
from app.models.db_models import Session as DBSession, Message, SkillScore
from app.schemas.entities import AssessMessageRequest
from app.services.assessment_agent import (
    evaluate_answer,
    generate_first_question,
    generate_followup_question,
    generate_transition,
)

router = APIRouter()


@router.post("/api/assess/message")
async def send_message(request: AssessMessageRequest, db: DBSessionType = Depends(get_db)):
    db_session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status == "complete":
        raise HTTPException(status_code=400, detail="Assessment already complete")

    # Eagerly copy everything we need into plain Python values BEFORE the generator runs.
    # The SQLAlchemy session closes after the HTTP response begins, so we must not access
    # ORM attributes lazily inside the async generator.
    session_id = request.session_id
    seniority = db_session.seniority
    role_context = db_session.role_context
    candidate_skills = list(db_session.candidate_skills or [])

    state = dict(db_session.assessment_state or {})
    current_skill: str = state.get("current_skill", "")
    skills_queue: list = list(state.get("skills_queue", []))
    questions_asked: int = int(state.get("questions_asked", 0))
    conversation_history: list = list(state.get("conversation_history", []))
    skill_scores: dict = dict(state.get("skill_scores", {}))

    # Append user message to history and persist it immediately
    conversation_history.append({"role": "user", "content": request.message})
    db.add(Message(session_id=session_id, role="user", content=request.message))
    db.commit()

    async def generate():
        nonlocal current_skill, skills_queue, questions_asked, conversation_history, skill_scores

        # Open a fresh DB session for all writes inside the generator
        gen_db = SessionLocal()
        try:
            # 1. Evaluate the answer for the current skill
            evaluation = await evaluate_answer(
                skill=current_skill,
                conversation_history=conversation_history,
                seniority=seniority,
            )
            score = float(evaluation.get("score", 5.0))
            notes = evaluation.get("notes", "")
            need_followup = evaluation.get("need_followup", False) and questions_asked < 2

            skill_scores[current_skill] = {"score": score, "notes": notes}

            # 2. Decide next action and generate response text
            if need_followup:
                response_text = await generate_followup_question(
                    skill=current_skill,
                    last_answer=request.message,
                    role_context=role_context,
                    seniority=seniority,
                )
                questions_asked += 1
                is_complete = False

            elif skills_queue:
                next_skill = skills_queue[0]
                skills_queue = skills_queue[1:]
                transition = await generate_transition(next_skill)
                first_q = await generate_first_question(
                    skill=next_skill,
                    candidate_skills=candidate_skills,
                    role_context=role_context,
                    seniority=seniority,
                    recent_history=conversation_history[-4:],
                )
                response_text = f"{transition} {first_q}"
                current_skill = next_skill
                questions_asked = 0
                is_complete = False

            else:
                n = len(skill_scores)
                response_text = (
                    f"That wraps up our assessment! I've evaluated your proficiency across "
                    f"{n} skill{'s' if n != 1 else ''}. "
                    "Your detailed report with skill scores and a personalized learning plan is now ready."
                )
                is_complete = True

            conversation_history.append({"role": "assistant", "content": response_text})

            # 3. Persist everything via the fresh DB session
            gen_db.add(Message(session_id=session_id, role="assistant", content=response_text))

            for skill, score_data in skill_scores.items():
                db_score = gen_db.query(SkillScore).filter(
                    SkillScore.session_id == session_id,
                    SkillScore.skill == skill,
                ).first()
                if db_score:
                    db_score.score = float(score_data["score"])
                    db_score.notes = score_data["notes"]
                    db_score.status = "assessed"

            sess = gen_db.query(DBSession).filter(DBSession.id == session_id).first()
            if sess:
                sess.assessment_state = {
                    "current_skill": current_skill,
                    "skills_queue": skills_queue,
                    "questions_asked": questions_asked,
                    "conversation_history": conversation_history,
                    "skill_scores": skill_scores,
                }
                if is_complete:
                    sess.status = "complete"

            gen_db.commit()

        finally:
            gen_db.close()

        # 4. Stream the response word by word
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'token': chunk, 'is_complete': False})}\n\n"

        yield f"data: {json.dumps({'token': '', 'is_complete': is_complete})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/assess/state/{session_id}")
async def get_state(session_id: str, db: DBSessionType = Depends(get_db)):
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
