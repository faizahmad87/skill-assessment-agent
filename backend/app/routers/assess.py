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
    MAX_QUESTIONS_MAP,
)

router = APIRouter()

MIN_QUESTIONS = 3  # always ask at least this many questions per skill


@router.post("/api/assess/message")
async def send_message(request: AssessMessageRequest, db: DBSessionType = Depends(get_db)):
    db_session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status == "complete":
        raise HTTPException(status_code=400, detail="Assessment already complete")

    # Eagerly copy everything we need into plain Python values BEFORE the generator runs.
    session_id = request.session_id
    seniority = db_session.seniority
    role_context = db_session.role_context
    candidate_skills = list(db_session.candidate_skills or [])

    state = dict(db_session.assessment_state or {})
    current_skill: str = state.get("current_skill", "")
    skills_queue: list = list(state.get("skills_queue", []))
    questions_asked: int = int(state.get("questions_asked", 1))
    conversation_history: list = list(state.get("conversation_history", []))
    skill_scores: dict = dict(state.get("skill_scores", {}))
    skill_importance: dict = dict(state.get("skill_importance", {}))
    skill_conversation_start: int = int(state.get("skill_conversation_start", 0))

    # Append user message to history and persist it immediately
    conversation_history.append({"role": "user", "content": request.message})
    db.add(Message(session_id=session_id, role="user", content=request.message))
    db.commit()

    async def generate():
        nonlocal current_skill, skills_queue, questions_asked, conversation_history, skill_scores, skill_conversation_start

        # Open a fresh DB session for all writes inside the generator
        gen_db = SessionLocal()
        try:
            # Determine importance and max questions for current skill
            importance = skill_importance.get(current_skill, "standard")
            max_q = MAX_QUESTIONS_MAP.get(importance, MIN_QUESTIONS)

            # 1. Evaluate the answer
            evaluation = await evaluate_answer(
                skill=current_skill,
                conversation_history=conversation_history,
                seniority=seniority,
                skill_importance=importance,
                questions_asked=questions_asked,
                max_questions=max_q,
            )
            score = float(evaluation.get("score", 5.0))
            notes = evaluation.get("notes", "")
            need_followup = evaluation.get("need_followup", False)

            skill_scores[current_skill] = {"score": score, "notes": notes}

            # 2. Decide next action
            # Force follow-up if below minimum; allow extra if evaluator says so and below max
            if questions_asked < MIN_QUESTIONS or (questions_asked < max_q and need_followup):
                # Ask a follow-up question
                skill_history = conversation_history[skill_conversation_start:]
                response_text = await generate_followup_question(
                    skill=current_skill,
                    question_number=questions_asked + 1,
                    max_questions=max_q,
                    skill_conversation_history=skill_history,
                    role_context=role_context,
                    seniority=seniority,
                    skill_importance=importance,
                    current_score=score,
                )
                questions_asked += 1
                is_complete = False

            elif skills_queue:
                # Move to the next skill
                next_skill = skills_queue[0]
                skills_queue = skills_queue[1:]
                next_importance = skill_importance.get(next_skill, "standard")
                next_max_q = MAX_QUESTIONS_MAP.get(next_importance, MIN_QUESTIONS)

                transition = await generate_transition(next_skill)
                first_q = await generate_first_question(
                    skill=next_skill,
                    candidate_skills=candidate_skills,
                    role_context=role_context,
                    seniority=seniority,
                    recent_history=conversation_history[-4:],
                    max_questions=next_max_q,
                    skill_importance=next_importance,
                )
                response_text = f"{transition} {first_q}"
                current_skill = next_skill
                questions_asked = 1  # first question of new skill
                skill_conversation_start = len(conversation_history) + 1  # +1 for assistant message about to be added
                is_complete = False

            else:
                # All skills done
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
                    "skill_importance": skill_importance,
                    "skill_conversation_start": skill_conversation_start,
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
