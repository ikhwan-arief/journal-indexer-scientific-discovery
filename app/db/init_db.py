from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_password_hash
from app.db.base import Base
from app.db.session import engine
from app.models.user import User


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        existing = db.scalar(select(User).where(User.username == settings.default_admin_username))
        if existing:
            return

        admin = User(
            username=settings.default_admin_username,
            full_name="System Administrator",
            role="administrator",
            password_hash=create_password_hash(settings.default_admin_password),
            is_active=True,
        )
        db.add(admin)
        db.commit()
