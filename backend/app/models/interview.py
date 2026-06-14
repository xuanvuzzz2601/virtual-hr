import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class InterviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.pending, nullable=False)
    transcript = Column(Text, nullable=True)           # JSON array of messages
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Auto-generated candidate login account
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    candidate_plain_password = Column(String(255), nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="interview_sessions")
    job_description = relationship("JobDescription", back_populates="interview_sessions")
    candidate_user = relationship("User", foreign_keys=[candidate_user_id])
    evaluation = relationship(
        "InterviewEvaluation",
        back_populates="session",
        uselist=False,
    )


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("interview_sessions.id"), unique=True, nullable=False
    )

    # Scores (0-100)
    technical_knowledge = Column(Float, nullable=False)
    communication_skills = Column(Float, nullable=False)
    problem_solving = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    role_fit = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)

    # Qualitative
    strengths = Column(Text, nullable=True)    # JSON array
    weaknesses = Column(Text, nullable=True)   # JSON array
    summary = Column(Text, nullable=False)
    recommendation = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("InterviewSession", back_populates="evaluation")
