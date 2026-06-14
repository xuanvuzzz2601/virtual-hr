import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.security import get_password_hash
from app.database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup / Shutdown lifecycle
# ---------------------------------------------------------------------------

def _migrate_existing_db():
    """Add new columns to existing tables without dropping data (SQLite safe)."""
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE job_descriptions ADD COLUMN is_open INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE interview_sessions ADD COLUMN candidate_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE interview_sessions ADD COLUMN candidate_plain_password VARCHAR(255)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Create all database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")
    # Add new columns to existing tables if missing
    _migrate_existing_db()

    # Ensure upload directory exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory ready: {upload_dir.resolve()}")

    # Seed default users
    _seed_users()

    yield

    logger.info("Application shutting down.")


def _seed_users():
    """Seed default admin and demo users if they don't exist."""
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        default_users = [
            {
                "email": "admin@virtualhr.com",
                "name": "Admin",
                "role": UserRole.admin,
                "password": "admin123",
            },
            {
                "email": "hr@virtualhr.com",
                "name": "HR Manager",
                "role": UserRole.hr,
                "password": "hr123",
            },
            {
                "email": "manager@virtualhr.com",
                "name": "Hiring Manager",
                "role": UserRole.hiring_manager,
                "password": "manager123",
            },
        ]

        for user_data in default_users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    email=user_data["email"],
                    name=user_data["name"],
                    role=user_data["role"],
                    hashed_password=get_password_hash(user_data["password"]),
                    is_active=True,
                )
                db.add(user)
                logger.info(f"Seeded user: {user_data['email']}")

        db.commit()
    except Exception as e:
        logger.error(f"Failed to seed users: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Virtual HR Platform API — AI-powered recruitment with "
            "CV parsing, candidate ranking, and automated interviewing."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "*",  # Allow all origins in development
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routers ----
    from app.api.auth import router as auth_router
    from app.api.candidates import router as candidates_router
    from app.api.interviews import router as interviews_router
    from app.api.jobs import router as jobs_router

    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(jobs_router, prefix="/api/jobs", tags=["Job Descriptions"])
    app.include_router(
        candidates_router, prefix="/api/candidates", tags=["Candidates"]
    )
    app.include_router(
        interviews_router, prefix="/api/interviews", tags=["Interviews"]
    )

    # ---- Health check ----
    @app.get("/health", tags=["Health"])
    def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/", tags=["Root"])
    def root():
        return {
            "message": f"Welcome to {settings.APP_NAME} API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()
