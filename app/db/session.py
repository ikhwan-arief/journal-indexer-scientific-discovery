from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


sqlite_file = Path(settings.sqlite_path)
sqlite_file.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{sqlite_file}",
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
