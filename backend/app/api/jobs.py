import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.job_description import JobDescription, JobStatus
from app.models.user import User
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionList,
    JobDescriptionRead,
    JobDescriptionUpdate,
)

router = APIRouter()


def _serialize_jd(jd: JobDescription, db: Session) -> JobDescriptionRead:
    """Convert ORM model to schema, deserializing JSON fields."""
    from app.models.candidate import Candidate

    candidate_count = db.query(Candidate).filter(Candidate.jd_id == jd.id).count()

    return JobDescriptionRead(
        id=jd.id,
        title=jd.title,
        department=jd.department,
        seniority_level=jd.seniority_level,
        responsibilities=jd.responsibilities,
        required_skills=json.loads(jd.required_skills) if jd.required_skills else [],
        preferred_skills=json.loads(jd.preferred_skills) if jd.preferred_skills else [],
        experience_requirements=jd.experience_requirements,
        status=jd.status,
        is_open=jd.is_open if jd.is_open is not None else True,
        created_by=jd.created_by,
        created_at=jd.created_at,
        updated_at=jd.updated_at,
        creator=jd.creator,
        candidate_count=candidate_count,
    )


@router.get("", response_model=List[JobDescriptionList])
def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all job descriptions with optional status filter."""
    from app.models.candidate import Candidate

    query = db.query(JobDescription)
    if status_filter:
        query = query.filter(JobDescription.status == status_filter)
    query = query.order_by(JobDescription.created_at.desc())
    jds = query.offset(skip).limit(limit).all()

    result = []
    for jd in jds:
        candidate_count = (
            db.query(Candidate).filter(Candidate.jd_id == jd.id).count()
        )
        result.append(
            JobDescriptionList(
                id=jd.id,
                title=jd.title,
                department=jd.department,
                seniority_level=jd.seniority_level,
                status=jd.status,
                is_open=jd.is_open if jd.is_open is not None else True,
                created_by=jd.created_by,
                created_at=jd.created_at,
                updated_at=jd.updated_at,
                candidate_count=candidate_count,
            )
        )
    return result


@router.post("", response_model=JobDescriptionRead, status_code=status.HTTP_201_CREATED)
def create_job(
    jd_in: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new job description."""
    jd = JobDescription(
        title=jd_in.title,
        department=jd_in.department,
        seniority_level=jd_in.seniority_level,
        responsibilities=jd_in.responsibilities,
        required_skills=json.dumps(jd_in.required_skills, ensure_ascii=False),
        preferred_skills=json.dumps(
            jd_in.preferred_skills or [], ensure_ascii=False
        ),
        experience_requirements=jd_in.experience_requirements,
        status=JobStatus.draft,
        created_by=current_user.id,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return _serialize_jd(jd, db)


@router.get("/{jd_id}", response_model=JobDescriptionRead)
def get_job(
    jd_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a job description by ID."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )
    return _serialize_jd(jd, db)


@router.put("/{jd_id}", response_model=JobDescriptionRead)
def update_job(
    jd_id: int,
    jd_in: JobDescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )

    update_data = jd_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "required_skills":
            setattr(jd, field, json.dumps(value, ensure_ascii=False))
        elif field == "preferred_skills":
            setattr(jd, field, json.dumps(value or [], ensure_ascii=False))
        else:
            setattr(jd, field, value)

    from datetime import datetime
    jd.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(jd)
    return _serialize_jd(jd, db)


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    jd_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )
    db.delete(jd)
    db.commit()


@router.post("/{jd_id}/publish", response_model=JobDescriptionRead)
def publish_job(
    jd_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Publish a job description (change status to published)."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )
    if jd.status == JobStatus.archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish an archived job",
        )
    jd.status = JobStatus.published
    from datetime import datetime
    jd.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jd)
    return _serialize_jd(jd, db)


@router.post("/{jd_id}/toggle-open", response_model=JobDescriptionRead)
def toggle_job_open(
    jd_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Toggle a job's open/close status for candidate applications."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )
    jd.is_open = not (jd.is_open if jd.is_open is not None else True)
    from datetime import datetime
    jd.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jd)
    return _serialize_jd(jd, db)


@router.post("/{jd_id}/archive", response_model=JobDescriptionRead)
def archive_job(
    jd_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Archive a job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )
    jd.status = JobStatus.archived
    from datetime import datetime
    jd.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jd)
    return _serialize_jd(jd, db)
