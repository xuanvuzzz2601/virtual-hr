import json
import logging
import random
import re
import string
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.security import get_password_hash
from app.database import get_db
from app.models.candidate import Candidate
from app.models.interview import InterviewEvaluation, InterviewSession, InterviewStatus
from app.models.job_description import JobDescription
from app.models.user import User, UserRole
from app.schemas.interview import (
    GeminiSessionConfig,
    InterviewCompleteRequest,
    InterviewCredentials,
    InterviewEvaluationRead,
    InterviewSessionCreate,
    InterviewSessionRead,
    InterviewSessionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_password(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", ""))
    return slug[:12] or "candidate"


def _serialize_session(s: InterviewSession) -> InterviewSessionRead:
    return InterviewSessionRead(
        id=s.id,
        candidate_id=s.candidate_id,
        jd_id=s.jd_id,
        status=s.status,
        transcript=json.loads(s.transcript) if s.transcript else None,
        started_at=s.started_at,
        completed_at=s.completed_at,
        created_at=s.created_at,
        candidate_user_id=s.candidate_user_id,
        candidate_plain_password=s.candidate_plain_password,
    )


def _serialize_evaluation(e: InterviewEvaluation) -> InterviewEvaluationRead:
    return InterviewEvaluationRead(
        id=e.id,
        session_id=e.session_id,
        technical_knowledge=e.technical_knowledge,
        communication_skills=e.communication_skills,
        problem_solving=e.problem_solving,
        confidence=e.confidence,
        role_fit=e.role_fit,
        overall_score=e.overall_score,
        strengths=json.loads(e.strengths) if e.strengths else [],
        weaknesses=json.loads(e.weaknesses) if e.weaknesses else [],
        summary=e.summary,
        recommendation=e.recommendation,
        created_at=e.created_at,
    )


@router.post(
    "/",
    response_model=InterviewSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interview_session(
    session_in: InterviewSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new interview session for a candidate."""
    # Validate candidate exists
    candidate = (
        db.query(Candidate).filter(Candidate.id == session_in.candidate_id).first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {session_in.candidate_id} not found",
        )

    # Validate JD exists
    jd = db.query(JobDescription).filter(JobDescription.id == session_in.jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {session_in.jd_id} not found",
        )

    # Candidate must belong to this JD
    if candidate.jd_id != session_in.jd_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate does not belong to the specified job description",
        )

    session = InterviewSession(
        candidate_id=session_in.candidate_id,
        jd_id=session_in.jd_id,
        status=InterviewStatus.pending,
    )
    db.add(session)
    db.flush()  # get session.id before commit

    # Auto-generate a candidate login account for this session
    plain_password = _generate_password()
    slug = _slug(candidate.name)
    email = f"{slug}_{session.id}@interview.virtualhr"

    # Ensure unique email (edge case)
    if db.query(User).filter(User.email == email).first():
        email = f"{slug}_{session.id}_{_generate_password(4)}@interview.virtualhr"

    candidate_user = User(
        email=email,
        name=candidate.name,
        role=UserRole.candidate,
        hashed_password=get_password_hash(plain_password),
        is_active=True,
    )
    db.add(candidate_user)
    db.flush()

    session.candidate_user_id = candidate_user.id
    session.candidate_plain_password = plain_password

    db.commit()
    db.refresh(session)
    return _serialize_session(session)


@router.get("/my-session", response_model=InterviewSessionRead)
def get_my_session_early(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the interview session assigned to the current candidate account."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No interview session found for this account",
        )
    return _serialize_session(session)


@router.get("/{session_id}", response_model=InterviewSessionRead)
def get_interview_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get interview session detail by ID."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found",
        )
    return _serialize_session(session)


@router.get("/candidate/{candidate_id}", response_model=List[InterviewSessionRead])
def get_candidate_sessions(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all interview sessions for a specific candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found",
        )

    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_id == candidate_id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return [_serialize_session(s) for s in sessions]


@router.post("/{session_id}/config", response_model=GeminiSessionConfig)
def get_session_config(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get Gemini Live session configuration.
    Returns the system prompt tailored to the JD and candidate profile.
    Also marks the session as in_progress.
    """
    from app.services.interview_service import generate_interview_system_prompt

    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found",
        )

    if session.status == InterviewStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a cancelled interview session",
        )

    candidate = (
        db.query(Candidate).filter(Candidate.id == session.candidate_id).first()
    )
    jd = db.query(JobDescription).filter(JobDescription.id == session.jd_id).first()

    if not candidate or not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate or job description not found",
        )

    # Parse candidate data
    candidate_data = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "skills": json.loads(candidate.skills) if candidate.skills else [],
        "education": json.loads(candidate.education) if candidate.education else [],
        "work_experience": (
            json.loads(candidate.work_experience)
            if candidate.work_experience
            else []
        ),
        "certifications": (
            json.loads(candidate.certifications) if candidate.certifications else []
        ),
    }

    # Parse JD data
    jd_data = {
        "title": jd.title,
        "department": jd.department,
        "seniority_level": jd.seniority_level,
        "responsibilities": jd.responsibilities,
        "required_skills": (
            json.loads(jd.required_skills) if jd.required_skills else []
        ),
        "preferred_skills": (
            json.loads(jd.preferred_skills) if jd.preferred_skills else []
        ),
        "experience_requirements": jd.experience_requirements,
    }

    system_prompt = generate_interview_system_prompt(jd_data, candidate_data)

    # Mark session as in_progress
    if session.status == InterviewStatus.pending:
        session.status = InterviewStatus.in_progress
        session.started_at = datetime.utcnow()
        db.commit()

    return GeminiSessionConfig(
        system_prompt=system_prompt,
        candidate_name=candidate.name,
        job_title=jd.title,
        session_id=session_id,
        gemini_api_key=settings.GEMINI_API_KEY if settings.GEMINI_API_KEY else None,
    )


@router.put("/{session_id}/complete", response_model=InterviewSessionRead)
def complete_interview(
    session_id: int,
    complete_data: InterviewCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark an interview session as completed and save the transcript.
    """
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found",
        )

    if session.status == InterviewStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled interview session",
        )

    if session.status == InterviewStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview session is already completed",
        )

    session.status = InterviewStatus.completed
    session.transcript = json.dumps(complete_data.transcript, ensure_ascii=False)
    session.completed_at = datetime.utcnow()

    if not session.started_at:
        session.started_at = datetime.utcnow()

    db.commit()
    db.refresh(session)
    return _serialize_session(session)


@router.post("/{session_id}/evaluate", response_model=InterviewEvaluationRead)
async def evaluate_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Trigger AI evaluation of a completed interview transcript.
    Uses Gemini Pro to analyze the transcript and generate scores.
    """
    from app.services.interview_service import evaluate_interview_transcript

    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found",
        )

    if session.status != InterviewStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be completed before evaluation",
        )

    if not session.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview transcript is empty",
        )

    # Check for existing evaluation
    existing = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.session_id == session_id)
        .first()
    )
    if existing:
        # Delete old evaluation and re-evaluate
        db.delete(existing)
        db.commit()

    # Fetch related data
    candidate = (
        db.query(Candidate).filter(Candidate.id == session.candidate_id).first()
    )
    jd = db.query(JobDescription).filter(JobDescription.id == session.jd_id).first()

    candidate_data = {
        "name": candidate.name if candidate else "Unknown",
        "skills": json.loads(candidate.skills) if candidate and candidate.skills else [],
    }
    jd_data = {
        "title": jd.title if jd else "Unknown",
        "seniority_level": jd.seniority_level if jd else "",
        "required_skills": (
            json.loads(jd.required_skills)
            if jd and jd.required_skills
            else []
        ),
        "experience_requirements": jd.experience_requirements if jd else "",
    }

    transcript = json.loads(session.transcript)

    try:
        result = await evaluate_interview_transcript(transcript, jd_data, candidate_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI evaluation service error: {str(e)}",
        )

    evaluation = InterviewEvaluation(
        session_id=session_id,
        technical_knowledge=result["technical_knowledge"],
        communication_skills=result["communication_skills"],
        problem_solving=result["problem_solving"],
        confidence=result["confidence"],
        role_fit=result["role_fit"],
        overall_score=result["overall_score"],
        strengths=json.dumps(result.get("strengths", []), ensure_ascii=False),
        weaknesses=json.dumps(result.get("weaknesses", []), ensure_ascii=False),
        summary=result.get("summary", ""),
        recommendation=result.get("recommendation", ""),
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _serialize_evaluation(evaluation)


@router.get("/{session_id}/evaluation", response_model=InterviewEvaluationRead)
def get_evaluation(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get evaluation result for a completed interview session."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found",
        )

    evaluation = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.session_id == session_id)
        .first()
    )
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation found for this session. Run POST /{id}/evaluate first.",
        )
    return _serialize_evaluation(evaluation)



