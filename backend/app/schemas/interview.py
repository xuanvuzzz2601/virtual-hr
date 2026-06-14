from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.interview import InterviewStatus


class TranscriptMessage(BaseModel):
    role: str           # "interviewer" | "candidate"
    content: str
    timestamp: Optional[str] = None


class InterviewSessionCreate(BaseModel):
    candidate_id: int
    jd_id: int


class InterviewSessionUpdate(BaseModel):
    status: Optional[InterviewStatus] = None
    transcript: Optional[List[Dict[str, Any]]] = None


class InterviewCredentials(BaseModel):
    candidate_email: str
    candidate_password: str
    session_id: int


class InterviewSessionRead(BaseModel):
    id: int
    candidate_id: int
    jd_id: int
    status: InterviewStatus
    transcript: Optional[List[Dict[str, Any]]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    candidate_user_id: Optional[int] = None
    candidate_plain_password: Optional[str] = None

    model_config = {"from_attributes": True}


class InterviewCompleteRequest(BaseModel):
    transcript: List[Dict[str, Any]]


class InterviewEvaluationRead(BaseModel):
    id: int
    session_id: int
    technical_knowledge: float
    communication_skills: float
    problem_solving: float
    confidence: float
    role_fit: float
    overall_score: float
    strengths: Optional[List[str]] = []
    weaknesses: Optional[List[str]] = []
    summary: str
    recommendation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GeminiSessionConfig(BaseModel):
    system_prompt: str
    candidate_name: str
    job_title: str
    session_id: int
    gemini_api_key: Optional[str] = None
