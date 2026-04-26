import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DBSessionType
import pdfplumber
import io
from database import get_db
from app.models.db_models import Session as DBSession, SkillScore
from app.schemas.entities import AnalyzeRequest, AnalyzeResponse
from app.services.parser_service import parse_jd_and_resume
from app.services.assessment_agent import generate_first_question

router = APIRouter()


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from PDF or DOCX file bytes."""
    fname = filename.lower()
    if fname.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text.strip()
    elif fname.endswith(".docx") or fname.endswith(".doc"):
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use PDF or DOCX.")


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, db: DBSessionType = Depends(get_db)):
    try:
        parsed = await parse_jd_and_resume(request.jd_text, request.resume_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse JD/Resume: {str(e)}")

    session_id = str(uuid.uuid4())
    required_skills = parsed.get("required_skills", [])
    candidate_skills = parsed.get("candidate_skills", [])
    role_context = parsed.get("role_context", "")
    seniority = parsed.get("seniority", "Mid")

    if not required_skills:
        raise HTTPException(status_code=422, detail="Could not extract required skills from job description")

    # Initial assessment state stored in DB
    assessment_state = {
        "current_skill": required_skills[0],
        "skills_queue": required_skills[1:],
        "questions_asked": 0,
        "conversation_history": [],
        "skill_scores": {},
    }

    db_session = DBSession(
        id=session_id,
        jd_text=request.jd_text,
        resume_text=request.resume_text,
        required_skills=required_skills,
        candidate_skills=candidate_skills,
        role_context=role_context,
        seniority=seniority,
        status="assessing",
        assessment_state=assessment_state,
    )
    db.add(db_session)
    for skill in required_skills:
        db.add(SkillScore(session_id=session_id, skill=skill))
    db.commit()

    # Generate opening question for the first skill
    first_question = await generate_first_question(
        skill=required_skills[0],
        candidate_skills=candidate_skills,
        role_context=role_context,
        seniority=seniority,
        recent_history=[],
    )

    # Save first question to conversation history and messages table
    assessment_state["conversation_history"] = [{"role": "assistant", "content": first_question}]
    db_session.assessment_state = assessment_state
    from app.models.db_models import Message
    db.add(Message(session_id=session_id, role="assistant", content=first_question))
    db.commit()

    return AnalyzeResponse(
        session_id=session_id,
        required_skills=required_skills,
        candidate_skills=[
            {"skill": s.get("skill", ""), "years_experience": s.get("years_experience"), "evidence": s.get("evidence")}
            for s in candidate_skills
        ],
        first_message=first_question,
    )


@router.post("/api/analyze/pdf")
async def analyze_pdf(
    jd_text: str = Form(...),
    resume_file: UploadFile = File(...),
    db: DBSessionType = Depends(get_db),
):
    content = await resume_file.read()
    resume_text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            resume_text += page.extract_text() or ""
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")
    return await analyze(AnalyzeRequest(jd_text=jd_text, resume_text=resume_text), db)


@router.post("/api/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    db: DBSessionType = Depends(get_db),
):
    """Accept JD and/or Resume as text or file (PDF/DOCX), then run analysis."""
    # Resolve JD
    if jd_file and jd_file.filename:
        content = await jd_file.read()
        try:
            final_jd = extract_text_from_file(content, jd_file.filename)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        if not final_jd:
            raise HTTPException(status_code=422, detail="Could not extract text from JD file")
    elif jd_text and jd_text.strip():
        final_jd = jd_text.strip()
    else:
        raise HTTPException(status_code=422, detail="Provide jd_text or jd_file")

    # Resolve Resume
    if resume_file and resume_file.filename:
        content = await resume_file.read()
        try:
            final_resume = extract_text_from_file(content, resume_file.filename)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        if not final_resume:
            raise HTTPException(status_code=422, detail="Could not extract text from resume file")
    elif resume_text and resume_text.strip():
        final_resume = resume_text.strip()
    else:
        raise HTTPException(status_code=422, detail="Provide resume_text or resume_file")

    return await analyze(AnalyzeRequest(jd_text=final_jd, resume_text=final_resume), db)
