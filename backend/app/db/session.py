"""Database engine and session factory.

Routers get a session via the `get_db` FastAPI dependency, which guarantees
the session is closed after each request.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base  # noqa: F401  (re-exported for convenience)


settings = get_settings()

# check_same_thread is a SQLite-only requirement; harmless to omit for Postgres.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
