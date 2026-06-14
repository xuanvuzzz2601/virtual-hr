from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.candidate import RecommendationLevel


class CandidateRead(BaseModel):
    id: int
    jd_id: int
    name: str
    email: str
    phone: Optional[str] = None
    skills: Optional[List[str]] = []
    education: Optional[List[Dict[str, Any]]] = []
    work_experience: Optional[List[Dict[str, Any]]] = []
    certifications: Optional[List[str]] = []
    cv_filename: str
    cv_file_path: str
    overall_score: Optional[float] = None
    skills_match: Optional[float] = None
    experience_match: Optional[float] = None
    education_match: Optional[float] = None
    domain_knowledge: Optional[float] = None
    communication_indicators: Optional[float] = None
    recommendation_level: Optional[RecommendationLevel] = None
    ranking_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateList(BaseModel):
    id: int
    jd_id: int
    name: str
    email: str
    phone: Optional[str] = None
    cv_filename: str
    overall_score: Optional[float] = None
    skills_match: Optional[float] = None
    experience_match: Optional[float] = None
    education_match: Optional[float] = None
    domain_knowledge: Optional[float] = None
    communication_indicators: Optional[float] = None
    recommendation_level: Optional[RecommendationLevel] = None
    ranking_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateUploadResponse(BaseModel):
    message: str
    candidate_id: int
    candidate: CandidateRead
