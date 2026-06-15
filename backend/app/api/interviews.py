import asyncio
import base64
import json
import logging
import random
import re
import string
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.security import get_password_hash, verify_token
from app.database import SessionLocal, get_db
from app.models.candidate import Candidate
from app.models.interview import InterviewEvaluation, InterviewSession, InterviewStatus
from app.models.job_description import JobDescription
from app.models.user import User, UserRole
from app.schemas.interview import (
    GeminiSessionConfig,
    InterviewCompleteRequest,
    InterviewEvaluationRead,
    InterviewSessionCreate,
    InterviewSessionRead,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_LIVE_MODEL = "gemini-3.1-flash-live-preview"


def _generate_password(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", ""))
    return slug[:12] or "candidate"


def _serialize_session(s: InterviewSession, db: Session = None) -> InterviewSessionRead:
    # Resolve candidate login email from the linked user account
    candidate_email: str | None = None
    if s.candidate_user_id:
        user = s.candidate_user  # lazy-loaded; DB session must be open
        if user:
            candidate_email = user.email

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
        candidate_email=candidate_email,
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


def _is_hr_or_above(user: User) -> bool:
    return user.role in (UserRole.admin, UserRole.hr, UserRole.hiring_manager)


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=InterviewSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interview_session(
    session_in: InterviewSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new interview session for a candidate."""
    candidate = (
        db.query(Candidate).filter(Candidate.id == session_in.candidate_id).first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {session_in.candidate_id} not found",
        )

    jd = db.query(JobDescription).filter(JobDescription.id == session_in.jd_id).first()
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description {session_in.jd_id} not found",
        )

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
    db.flush()

    plain_password = _generate_password()
    slug = _slug(candidate.name)
    email = f"{slug}_{session.id}@interview.virtualhr"

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

    # Candidates can only view their own session
    if current_user.role == UserRole.candidate and session.candidate_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return _serialize_session(session)


@router.get("/candidate/{candidate_id}", response_model=List[InterviewSessionRead])
def get_candidate_sessions(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all interview sessions for a specific candidate (HR/admin only)."""
    if not _is_hr_or_above(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    Get Gemini Live session configuration (system prompt).
    Also marks the session as in_progress.
    The Gemini API key is NOT returned — use the /live WebSocket endpoint instead.
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

    candidate_data = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "skills": json.loads(candidate.skills) if candidate.skills else [],
        "education": json.loads(candidate.education) if candidate.education else [],
        "work_experience": (
            json.loads(candidate.work_experience) if candidate.work_experience else []
        ),
        "certifications": (
            json.loads(candidate.certifications) if candidate.certifications else []
        ),
    }
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

    if session.status == InterviewStatus.pending:
        session.status = InterviewStatus.in_progress
        session.started_at = datetime.utcnow()
        db.commit()

    return GeminiSessionConfig(
        system_prompt=system_prompt,
        candidate_name=candidate.name,
        job_title=jd.title,
        session_id=session_id,
    )


@router.put("/{session_id}/complete", response_model=InterviewSessionRead)
def complete_interview(
    session_id: int,
    complete_data: InterviewCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark an interview session as completed and save the transcript."""
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

    # Candidates can only complete their own session
    if current_user.role == UserRole.candidate and session.candidate_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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


@router.post("/{session_id}/autosave", status_code=status.HTTP_204_NO_CONTENT)
def autosave_transcript(
    session_id: int,
    save_data: InterviewCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Periodically save transcript without completing the session (crash recovery)."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        return  # silent — autosave is best-effort

    if current_user.role == UserRole.candidate and session.candidate_user_id != current_user.id:
        return

    if session.status in (InterviewStatus.pending, InterviewStatus.in_progress):
        session.transcript = json.dumps(save_data.transcript, ensure_ascii=False)
        db.commit()


@router.post("/{session_id}/evaluate", response_model=InterviewEvaluationRead)
async def evaluate_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Trigger AI evaluation of a completed interview transcript."""
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

    existing = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.session_id == session_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

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
            json.loads(jd.required_skills) if jd and jd.required_skills else []
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


# ── WebSocket: Gemini Live proxy ───────────────────────────────────────────────

@router.websocket("/{session_id}/live")
async def interview_live_ws(
    session_id: int,
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket proxy for Gemini Live API.
    Keeps the Gemini API key server-side; client sends/receives raw audio + JSON events.

    Client → backend messages (JSON):
      {"type": "audio", "data": "<base64 PCM 16kHz>"}
      {"type": "text", "content": "..."}
      {"type": "end"}

    Backend → client messages (JSON):
      {"type": "ready"}
      {"type": "audio", "data": "<base64 PCM 24kHz>"}
      {"type": "transcript", "role": "interviewer"|"candidate", "text": "..."}
      {"type": "turn_complete"}
      {"type": "interrupted"}
      {"type": "error", "message": "..."}
    """
    # ── Auth (JWT via query param — browser WS doesn't support custom headers) ─
    user_id_str = verify_token(token)
    if not user_id_str:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    db = SessionLocal()
    system_prompt: str = ""
    try:
        user = db.query(User).filter(User.id == int(user_id_str)).first()
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        session = (
            db.query(InterviewSession)
            .filter(InterviewSession.id == session_id)
            .first()
        )
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return

        # Candidates can only connect to their own session
        if user.role == UserRole.candidate and session.candidate_user_id != user.id:
            await websocket.close(code=1008, reason="Forbidden")
            return

        if session.status == InterviewStatus.cancelled:
            await websocket.close(code=1003, reason="Session cancelled")
            return

        candidate = db.query(Candidate).filter(Candidate.id == session.candidate_id).first()
        jd = db.query(JobDescription).filter(JobDescription.id == session.jd_id).first()

        from app.services.interview_service import generate_interview_system_prompt

        candidate_data = {
            "name": candidate.name if candidate else "ứng viên",
            "email": candidate.email if candidate else "",
            "phone": candidate.phone if candidate else "",
            "skills": json.loads(candidate.skills) if candidate and candidate.skills else [],
            "education": json.loads(candidate.education) if candidate and candidate.education else [],
            "work_experience": (
                json.loads(candidate.work_experience) if candidate and candidate.work_experience else []
            ),
            "certifications": (
                json.loads(candidate.certifications) if candidate and candidate.certifications else []
            ),
        }
        jd_data = {
            "title": jd.title if jd else "N/A",
            "department": jd.department if jd else "N/A",
            "seniority_level": jd.seniority_level if jd else "N/A",
            "responsibilities": jd.responsibilities if jd else "",
            "required_skills": json.loads(jd.required_skills) if jd and jd.required_skills else [],
            "preferred_skills": json.loads(jd.preferred_skills) if jd and jd.preferred_skills else [],
            "experience_requirements": jd.experience_requirements if jd else "",
        }

        system_prompt = generate_interview_system_prompt(jd_data, candidate_data)

        # Mark in_progress
        if session.status == InterviewStatus.pending:
            session.status = InterviewStatus.in_progress
            session.started_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()

    # ── Accept WS ────────────────────────────────────────────────────────────
    await websocket.accept()

    if not settings.GEMINI_API_KEY:
        await websocket.send_json({"type": "error", "message": "GEMINI_API_KEY not configured on server"})
        await websocket.close()
        return

    # ── Gemini Live proxy ─────────────────────────────────────────────────────
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Use typed config — required for gemini-3.1-flash-live-preview
    live_config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=system_prompt)]
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    async def _forward_one_response(sc, session_id_log: str) -> None:
        """Send a single server_content object to the client WebSocket."""
        if sc.model_turn and sc.model_turn.parts:
            for part in sc.model_turn.parts:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    audio_b64 = base64.b64encode(inline.data).decode()
                    await websocket.send_json({"type": "audio", "data": audio_b64})

        out_tx = getattr(sc, "output_transcription", None)
        if out_tx and getattr(out_tx, "text", None):
            await websocket.send_json({"type": "transcript", "role": "interviewer", "text": out_tx.text})

        in_tx = getattr(sc, "input_transcription", None)
        if in_tx and getattr(in_tx, "text", None):
            await websocket.send_json({"type": "transcript", "role": "candidate", "text": in_tx.text})

        if getattr(sc, "turn_complete", False):
            logger.info("[%s] turn_complete received from Gemini", session_id_log)
            await websocket.send_json({"type": "turn_complete"})

        if getattr(sc, "interrupted", False):
            await websocket.send_json({"type": "interrupted"})

    sid_log = f"session:{session_id}"

    async def relay_gemini_to_ws(gemini_session) -> None:
        """
        Forward Gemini events to the client WebSocket.
        Wraps receive() in a while-True loop because some SDK versions
        only iterate over one model turn per receive() call.
        """
        turn = 0
        try:
            while True:
                got_any = False
                logger.info("[%s] relay_gemini_to_ws: calling receive() (turn=%d)", sid_log, turn)
                async for response in gemini_session.receive():
                    got_any = True
                    sc = response.server_content
                    if sc is None:
                        continue
                    await _forward_one_response(sc, sid_log)

                if not got_any:
                    logger.info("[%s] relay_gemini_to_ws: receive() empty → Gemini session ended", sid_log)
                    break
                turn += 1
                logger.info("[%s] relay_gemini_to_ws: receive() exhausted, looping for turn=%d", sid_log, turn)

        except asyncio.CancelledError:
            logger.info("[%s] relay_gemini_to_ws cancelled", sid_log)
        except Exception as exc:
            logger.warning("[%s] relay_gemini_to_ws error: %s", sid_log, exc, exc_info=True)

    audio_chunks_received = 0

    async def relay_ws_to_gemini(gemini_session) -> None:
        """Forward client messages to Gemini with full logging."""
        nonlocal audio_chunks_received
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "audio":
                    pcm = base64.b64decode(msg["data"])
                    audio_chunks_received += 1
                    if audio_chunks_received == 1 or audio_chunks_received % 50 == 0:
                        logger.info("[%s] relay_ws_to_gemini: audio chunk #%d (%d bytes PCM)",
                                    sid_log, audio_chunks_received, len(pcm))
                    try:
                        await gemini_session.send_realtime_input(
                            audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
                        )
                    except Exception as send_exc:
                        logger.error("[%s] send_realtime_input(audio) failed: %s", sid_log, send_exc)
                        break

                elif msg_type == "text":
                    text_content = msg.get("content", "")
                    logger.info("[%s] relay_ws_to_gemini: text → Gemini: %r", sid_log, text_content[:80])
                    try:
                        await gemini_session.send_realtime_input(text=text_content)
                        logger.info("[%s] relay_ws_to_gemini: text sent OK", sid_log)
                    except Exception as send_exc:
                        logger.error("[%s] send_realtime_input(text) failed: %s", sid_log, send_exc)
                        break

                elif msg_type == "end":
                    logger.info("[%s] relay_ws_to_gemini: received 'end' from client", sid_log)
                    try:
                        await gemini_session.send_realtime_input(audio_stream_end=True)
                    except Exception:
                        pass
                    break

        except WebSocketDisconnect:
            logger.info("[%s] relay_ws_to_gemini: client disconnected", sid_log)
        except asyncio.CancelledError:
            logger.info("[%s] relay_ws_to_gemini cancelled", sid_log)
        except Exception as exc:
            logger.warning("[%s] relay_ws_to_gemini error: %s", sid_log, exc, exc_info=True)

    try:
        async with client.aio.live.connect(model=_LIVE_MODEL, config=live_config) as gemini_session:
            logger.info("[%s] Gemini Live session connected, sending kick-off", sid_log)
            await websocket.send_json({"type": "ready"})
            await gemini_session.send_realtime_input(
                text="Bắt đầu buổi phỏng vấn. Hãy giới thiệu bản thân và bắt đầu."
            )

            task_recv = asyncio.create_task(relay_gemini_to_ws(gemini_session))
            task_send = asyncio.create_task(relay_ws_to_gemini(gemini_session))

            _done, pending = await asyncio.wait(
                [task_recv, task_send],
                return_when=asyncio.FIRST_COMPLETED,
            )
            logger.info("[%s] asyncio.wait returned, done=%d, pending=%d",
                        sid_log, len(_done), len(pending))
            for t in pending:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass

    except WebSocketDisconnect:
        logger.info("[%s] client WS disconnected during Gemini connect", sid_log)
    except Exception as exc:
        logger.error("[%s] interview_live_ws error: %s", sid_log, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
