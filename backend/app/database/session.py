from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def get_database_engine() -> Engine:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return get_engine(database_url)


def get_db() -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=get_database_engine(), autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()