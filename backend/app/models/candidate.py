import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class RecommendationLevel(str, enum.Enum):
    strong_match = "strong_match"
    moderate_match = "moderate_match"
    weak_match = "weak_match"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)

    # Parsed CV data stored as JSON strings
    skills = Column(Text, nullable=True)               # JSON array
    education = Column(Text, nullable=True)            # JSON array
    work_experience = Column(Text, nullable=True)      # JSON array
    certifications = Column(Text, nullable=True)       # JSON array

    # File info
    cv_filename = Column(String(255), nullable=False)
    cv_file_path = Column(String(500), nullable=False)

    # AI scoring
    overall_score = Column(Float, nullable=True)
    skills_match = Column(Float, nullable=True)
    experience_match = Column(Float, nullable=True)
    education_match = Column(Float, nullable=True)
    domain_knowledge = Column(Float, nullable=True)
    communication_indicators = Column(Float, nullable=True)
    recommendation_level = Column(Enum(RecommendationLevel), nullable=True)
    parsed_data = Column(Text, nullable=True)          # Full JSON from Gemini parse
    ranking_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job_description = relationship("JobDescription", back_populates="candidates")
    interview_sessions = relationship("InterviewSession", back_populates="candidate")
