from typing import Generator
from sqlite3 import SQLITE_CONSTRAINT_UNIQUE

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session, Session
from sqlalchemy.exc import IntegrityError

from src.dependencies.config import Config

config = Config()

url = URL.create(
    drivername="postgresql",
    username=config["DB_USERNAME"],
    database=config["DB_DATABASE"],
    host=config["DB_HOST"],
    port=int(str(config["DB_PORT"])),
    password=config["DB_PASSWORD"],
)

engine = create_engine(url)

# Session factory for creating new sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DEPRECATED: Legacy scoped session - use get_db() dependency instead
# Kept for backwards compatibility during migration
db_session = scoped_session(SessionLocal)

Base = declarative_base()
Base.query = db_session.query_property()


def is_unique_conflict(error: IntegrityError, constraints: tuple[str, ...]) -> bool:
    """Recognize the expected uniqueness conflicts on PostgreSQL and test SQLite."""
    original = error.orig
    if getattr(original, "pgcode", None) == "23505":
        diagnostic = getattr(original, "diag", None)
        return getattr(diagnostic, "constraint_name", None) in constraints
    return getattr(original, "sqlite_errorcode", None) == SQLITE_CONSTRAINT_UNIQUE


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Session is automatically closed after request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import src.models

    Base.metadata.create_all(bind=engine)
