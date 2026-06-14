from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.job_description import JobStatus
from app.schemas.user import UserRead


class JobDescriptionBase(BaseModel):
    title: str
    department: str
    seniority_level: str
    responsibilities: str
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    experience_requirements: str
    is_open: bool = True


class JobDescriptionCreate(JobDescriptionBase):
    pass


class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    seniority_level: Optional[str] = None
    responsibilities: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_requirements: Optional[str] = None
    status: Optional[JobStatus] = None


class JobDescriptionRead(JobDescriptionBase):
    id: int
    status: JobStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator: Optional[UserRead] = None
    candidate_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class JobDescriptionList(BaseModel):
    id: int
    title: str
    department: str
    seniority_level: str
    status: JobStatus
    is_open: bool = True
    created_by: int
    created_at: datetime
    updated_at: datetime
    candidate_count: int = 0

    model_config = {"from_attributes": True}
