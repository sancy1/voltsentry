"""
FILE: src/voltsentry/db/session.py
PATH: voltsentry/src/voltsentry/db/session.py
DESCRIPTION: Database session management with WAL mode and connection pooling
"""
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from voltsentry.core.constants import DB_PATH
from voltsentry.core.exceptions import DatabaseError
from voltsentry.core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# Engine Configuration
# ============================================================================
# Ensure database directory exists prior to creating engine
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={
        "timeout": 30,
        "check_same_thread": False,
    },
    echo=False,  # Set to True for SQL debugging
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """
    Configure SQLite for concurrent access and performance.
    
    WAL mode enables concurrent reads during writes.
    busy_timeout prevents "database locked" errors.
    """
    cursor = dbapi_conn.cursor()

    # WAL mode enables concurrent reads during writes
    cursor.execute("PRAGMA journal_mode=WAL")

    # Busy timeout for locked DB (5 seconds)
    cursor.execute("PRAGMA busy_timeout=5000")

    # Foreign keys enforcement
    cursor.execute("PRAGMA foreign_keys=ON")

    # Optimize for reading (20MB cache)
    cursor.execute("PRAGMA cache_size=-20000")

    # Synchronous = NORMAL (good balance of safety and performance)
    cursor.execute("PRAGMA synchronous=NORMAL")

    cursor.close()
    logger.debug("SQLite pragmas configured: WAL mode, busy_timeout=5000ms")


# ============================================================================
# Session Factory
# ============================================================================
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.

    Usage:
        with get_session() as session:
            reading = BatteryReading(percent=85)
            session.add(reading)

    Yields:
        SQLAlchemy Session object
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("Session committed successfully")
    except Exception as e:
        session.rollback()
        logger.error("Session rolled back due to: %s", e)
        raise DatabaseError(f"Database operation failed: {e}") from e
    finally:
        session.close()
        logger.debug("Session closed")


# ============================================================================
# Helper Functions
# ============================================================================
def ensure_db_directory() -> None:
    """Ensure the database directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Database directory ensured: %s", DB_PATH.parent)


def get_db_path() -> Path:
    """Get the database file path."""
    return DB_PATH


def get_engine_status() -> dict:
    """Get engine status for health checks."""
    return {
        "url": str(engine.url),
        "dialect": engine.dialect.name,
    }