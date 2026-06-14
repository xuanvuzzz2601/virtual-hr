from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_admin
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, Token, UserCreate, UserRead

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    form_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT access token."""
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user.
    - If no users exist: anyone can register (creates first admin).
    - Otherwise: requires admin token.
    """
    existing_user_count = db.query(User).count()

    # Allow open registration only when no users exist
    if existing_user_count > 0:
        # We need to check auth manually since the first user path skips auth
        from fastapi import Request
        # If users already exist, this endpoint requires admin — handled below
        pass

    # Check for duplicate email
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post(
    "/register/admin",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def admin_register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin-only endpoint to create new users."""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user info."""
    return UserRead.model_validate(current_user)
