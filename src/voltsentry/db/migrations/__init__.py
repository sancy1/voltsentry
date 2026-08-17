"""
FILE: src/voltsentry/db/migrations/__init__.py
PATH: voltsentry/src/voltsentry/db/migrations/__init__.py
DESCRIPTION: Database migrations package initialization and runner exports.
"""

import sys
from pathlib import Path
from subprocess import run, CalledProcessError
from typing import List

from ..models import Base
from ..session import engine
from ...core.constants import DATA_DIR
from ...core.exceptions import MigrationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


def get_alembic_cfg_path() -> Path:
    """Get the path to alembic.ini by searching upward from the file path."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        ini_path = parent / "alembic.ini"
        if ini_path.exists():
            return ini_path
    return Path(__file__).parent.parent.parent.parent / "alembic.ini"


def run_migrations() -> None:
    """
    Run Alembic migrations to upgrade to the latest version.
    
    If alembic.ini is absent, falls back to direct table creation via Base.metadata.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    alembic_ini = get_alembic_cfg_path()

    if not alembic_ini.exists():
        logger.warning(
            "alembic.ini not found at %s. Falling back to direct table creation.", 
            alembic_ini
        )
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created directly via SQLAlchemy Base metadata.")
        return

    try:
        logger.info("Running Alembic migrations...")
        result = run(
            [
                sys.executable,
                "-m", "alembic",
                "-c", str(alembic_ini),
                "upgrade", "head"
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Migrations applied successfully:\n%s", result.stdout)
    except CalledProcessError as e:
        error_msg = f"Migration failed: {e.stderr}\n{e.stdout}"
        logger.critical(error_msg)
        raise MigrationError(error_msg) from e


def create_migration(message: str) -> None:
    """
    Create a new Alembic migration.

    Args:
        message: Migration description message
    """
    alembic_ini = get_alembic_cfg_path()

    if not alembic_ini.exists():
        raise MigrationError(f"Alembic config not found: {alembic_ini}")

    try:
        logger.info("Creating migration: %s", message)
        result = run(
            [
                sys.executable,
                "-m", "alembic",
                "-c", str(alembic_ini),
                "revision",
                "--autogenerate",
                "-m", message,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Migration created:\n%s", result.stdout)
    except CalledProcessError as e:
        error_msg = f"Migration creation failed: {e.stderr}\n{e.stdout}"
        logger.error(error_msg)
        raise MigrationError(error_msg) from e


def get_current_revision() -> str:
    """Get the current migration revision."""
    alembic_ini = get_alembic_cfg_path()

    if not alembic_ini.exists():
        return "no_migrations"

    try:
        result = run(
            [
                sys.executable,
                "-m", "alembic",
                "-c", str(alembic_ini),
                "current",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except CalledProcessError:
        return "unknown"


def get_migration_history() -> List[str]:
    """Get the migration history."""
    alembic_ini = get_alembic_cfg_path()

    if not alembic_ini.exists():
        return []

    try:
        result = run(
            [
                sys.executable,
                "-m", "alembic",
                "-c", str(alembic_ini),
                "history",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n")
    except CalledProcessError:
        return []


__all__ = [
    "run_migrations",
    "create_migration",
    "get_current_revision",
    "get_migration_history",
]