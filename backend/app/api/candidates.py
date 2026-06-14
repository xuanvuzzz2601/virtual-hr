import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.database import get_db
from app.models.candidate import Candidate, RecommendationLevel
from app.models.job_description import JobDescription
from app.models.user import User
from app.schemas.candidate import CandidateList, CandidateRead, CandidateUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE_MB = 10


def _serialize_candidate(c: Candidate) -> CandidateRead:
    """Convert ORM Candidate to schema, deserializing JSON fields."""
    return CandidateRead(
        id=c.id,
        jd_id=c.jd_id,
        name=c.name,
        email=c.email,
        phone=c.phone,
        skills=json.loads(c.skills) if c.skills else [],
        education=json.loads(c.education) if c.education else [],
        work_experience=json.loads(c.work_experience) if c.work_experience else [],
        certifications=json.loads(c.certifications) if c.certifications else [],
        cv_filename=c.cv_filename,
        cv_file_path=c.cv_file_path,
        overall_score=c.overall_score,
        skills_match=c.skills_match,
        experience_match=c.experience_match,
        education_match=c.education_match,
        domain_knowledge=c.domain_knowledge,
        communication_indicators=c.communication_indicators,
        recommendation_level=c.recommendation_level,
        ranking_summary=c.ranking_summary,
        created_at=c.created_at,
    )


async def _parse_and_rank_candidate(candidate_id: int, jd_id: int, file_path: str):
    """
    Background task: parse CV with Gemini, then rank against JD.
    Updates the candidate record in DB when done.
    """
    from app.database import SessionLocal
    from app.models.job_description import JobDescription
    from app.services.candidate_ranker import rank_candidate
    from app.services.cv_parser import parse_cv

    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()

        if not candidate or not jd:
            logger.error(f"Candidate {candidate_id} or JD {jd_id} not found")
            return

        # Step 1: Parse CV
        logger.info(f"Parsing CV for candidate {candidate_id}: {file_path}")
        parsed = await parse_cv(file_path)

        # Update candidate with parsed data
        candidate.name = parsed.get("name") or candidate.name
        candidate.email = parsed.get("email") or candidate.email
        candidate.phone = parsed.get("phone") or candidate.phone
        candidate.skills = json.dumps(parsed.get("skills", []), ensure_ascii=False)
        candidate.education = json.dumps(
            parsed.get("education", []), ensure_ascii=False
        )
        candidate.work_experience = json.dumps(
            parsed.get("work_experience", []), ensure_ascii=False
        )
        candidate.certifications = json.dumps(
            parsed.get("certifications", []), ensure_ascii=False
        )
        candidate.parsed_data = json.dumps(parsed, ensure_ascii=False)
        db.commit()

        # Step 2: Rank candidate against JD
        logger.info(f"Ranking candidate {candidate_id} against JD {jd_id}")
        jd_data = {
            "title": jd.title,
            "department": jd.department,
            "seniority_level": jd.seniority_level,
            "responsibilities": jd.responsibilities,
            "required_skills": json.loads(jd.required_skills) if jd.required_skills else [],
            "preferred_skills": json.loads(jd.preferred_skills) if jd.preferred_skills else [],
            "experience_requirements": jd.experience_requirements,
        }
        ranking = await rank_candidate(jd_data, parsed)

        # Update scores
        candidate.overall_score = ranking.get("overall_score")
        candidate.skills_match = ranking.get("skills_match")
        candidate.experience_match = ranking.get("experience_match")
        candidate.education_match = ranking.get("education_match")
        candidate.domain_knowledge = ranking.get("domain_knowledge")
        candidate.communication_indicators = ranking.get("communication_indicators")
        candidate.recommendation_level = RecommendationLevel(
            ranking.get("recommendation_level", "moderate_match")
        )
        candidate.ranking_summary = ranking.get("summary", "")
        db.commit()

        logger.info(
            f"Candidate {candidate_id} processed. Score: {ranking.get('overall_score')}"
        )

    except Exception as e:
        logger.error(f"Background processing failed for candidate {candidate_id}: {e}")
        # Mark with default scores so the record is not "stuck"
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if candidate:
                candidate.ranking_summary = f"Processing error: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/jobs/{jd_id}/candidates", response_model=List[CandidateList])
def list_candidates(
    jd_id: int,
    sort_by: Optional[str] = Query("overall_score", enum=["overall_score", "created_at", "name"]),
    order: Optional[str] = Query("desc", enum=["asc", "desc"]),
    recommendation: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List candidates for a specific job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )

    query = db.query(Candidate).filter(Candidate.jd_id == jd_id)

    if recommendation:
        try:
            rec_level = RecommendationLevel(recommendation)
            query = query.filter(Candidate.recommendation_level == rec_level)
        except ValueError:
            pass

    # Sorting
    sort_col = getattr(Candidate, sort_by, Candidate.overall_score)
    if order == "desc":
        query = query.order_by(sort_col.desc().nullslast())
    else:
        query = query.order_by(sort_col.asc().nullslast())

    candidates = query.offset(skip).limit(limit).all()
    return [
        CandidateList(
            id=c.id,
            jd_id=c.jd_id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            cv_filename=c.cv_filename,
            overall_score=c.overall_score,
            skills_match=c.skills_match,
            experience_match=c.experience_match,
            education_match=c.education_match,
            domain_knowledge=c.domain_knowledge,
            communication_indicators=c.communication_indicators,
            recommendation_level=c.recommendation_level,
            ranking_summary=c.ranking_summary,
            created_at=c.created_at,
        )
        for c in candidates
    ]


@router.post(
    "/jobs/{jd_id}/upload",
    response_model=CandidateUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_cv(
    jd_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a CV file for a job description.
    Triggers background CV parsing and candidate ranking via Gemini.
    """
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {jd_id} not found",
        )

    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE_MB}MB",
        )

    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / str(jd_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file (handle duplicate names with counter)
    safe_filename = file.filename.replace(" ", "_")
    file_path = upload_dir / safe_filename
    counter = 1
    while file_path.exists():
        stem = Path(safe_filename).stem
        file_path = upload_dir / f"{stem}_{counter}{ext}"
        counter += 1

    with open(file_path, "wb") as f:
        f.write(content)

    # Create candidate record with placeholder name/email
    # (will be updated after CV parsing)
    candidate = Candidate(
        jd_id=jd_id,
        name=Path(file.filename).stem,  # Temporary name from filename
        email="pending@parsing.com",    # Temporary email
        cv_filename=file_path.name,
        cv_file_path=str(file_path),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    # Trigger async background task for parsing + ranking
    background_tasks.add_task(
        _parse_and_rank_candidate,
        candidate.id,
        jd_id,
        str(file_path),
    )

    return CandidateUploadResponse(
        message="CV uploaded successfully. Parsing and ranking in progress.",
        candidate_id=candidate.id,
        candidate=_serialize_candidate(candidate),
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get candidate detail by ID."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found",
        )
    return _serialize_candidate(candidate)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a candidate and their CV file."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found",
        )

    # Delete CV file from disk
    try:
        if candidate.cv_file_path and os.path.exists(candidate.cv_file_path):
            os.remove(candidate.cv_file_path)
    except OSError as e:
        logger.warning(f"Could not delete CV file: {e}")

    db.delete(candidate)
    db.commit()
