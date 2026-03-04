from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_admin
from app.core.security import create_access_token, create_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username, User.is_active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)


@router.post("/users", response_model=MessageResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> MessageResponse:
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    if payload.role not in {"administrator", "curator"}:
        raise HTTPException(status_code=400, detail="Role must be administrator or curator")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=create_password_hash(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    return MessageResponse(message="User created")
