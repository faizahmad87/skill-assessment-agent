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
