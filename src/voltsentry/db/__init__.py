"""
FILE: src/voltsentry/db/__init__.py
PATH: voltsentry/src/voltsentry/db/__init__.py
DESCRIPTION: Database module initialization
"""
from .session import engine, get_session, ensure_db_directory, get_db_path, SessionLocal
from .models import Base, BatteryReading, ChargeCycleEvent, AlarmEvent, CalibrationRecord, AutomationHookLog
from .repositories import (
    BaseRepository,
    BatteryReadingRepository,
    ChargeCycleRepository,
    AlarmEventRepository,
    CalibrationRepository,
    AutomationHookRepository,
    get_repository,
    flush_all_pending,
)
from .migrations import run_migrations, create_migration, get_current_revision

__all__ = [
    "engine",
    "get_session",
    "ensure_db_directory",
    "get_db_path",
    "SessionLocal",
    "Base",
    "BatteryReading",
    "ChargeCycleEvent",
    "AlarmEvent",
    "CalibrationRecord",
    "AutomationHookLog",
    "BaseRepository",
    "BatteryReadingRepository",
    "ChargeCycleRepository",
    "AlarmEventRepository",
    "CalibrationRepository",
    "AutomationHookRepository",
    "get_repository",
    "flush_all_pending",
    "run_migrations",
    "create_migration",
    "get_current_revision",
]