from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(db_session)) -> User:
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return user


def require_curator_or_admin(user: User = Depends(current_user)) -> User:
    if user.role not in {"administrator", "curator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Curator or administrator role required")
    return user
