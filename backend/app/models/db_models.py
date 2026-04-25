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
    # Mutable assessment state: {current_skill, skills_queue, questions_asked, conversation_history, skill_scores}
    assessment_state: Mapped[dict] = mapped_column(JSON, default=dict)
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
