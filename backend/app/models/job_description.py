import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class JobStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    seniority_level = Column(String(100), nullable=False)
    responsibilities = Column(Text, nullable=False)
    required_skills = Column(Text, nullable=False)   # JSON string
    preferred_skills = Column(Text, nullable=True)   # JSON string
    experience_requirements = Column(String(255), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.draft, nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    creator = relationship("User", back_populates="job_descriptions")
    candidates = relationship("Candidate", back_populates="job_description")
    interview_sessions = relationship("InterviewSession", back_populates="job_description")
