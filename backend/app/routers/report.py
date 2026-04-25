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
