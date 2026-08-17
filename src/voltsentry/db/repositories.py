"""
FILE: src/voltsentry/db/repositories.py
PATH: voltsentry/src/voltsentry/db/repositories.py
DESCRIPTION: Repository pattern for database operations - DRY data access
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import desc, and_, func
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session

from .models import (
    BatteryReading,
    ChargeCycleEvent,
    AlarmEvent,
    CalibrationRecord,
    AutomationHookLog,
)
from .session import get_session
from ..core.constants import DB_PENDING_QUEUE
from ..core.exceptions import DatabaseError, EntityNotFoundError
from ..core.logging_config import get_logger
from ..core.resilience import resilient
from ..core.decorators import timed, log_entry_exit

logger = get_logger(__name__)


# ============================================================================
# Base Repository - DRY Foundation
# ============================================================================
class BaseRepository:
    """
    Base repository with common CRUD operations.
    
    All repositories inherit from this class to avoid code duplication.
    Handles:
    - Save with retry and fallback
    - Pending write queuing
    - Flush pending writes
    """

    model = None  # Override in subclasses

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._pending_queue = DB_PENDING_QUEUE

    @property
    def session(self) -> Session:
        """Get session or raise if uninitialized."""
        if self._session is None:
            raise DatabaseError("No session available, use context manager")
        return self._session

    @timed()
    @resilient(exceptions=(OperationalError,), attempts=3)
    def save(self, entity) -> None:
        """
        Save an entity to database with automatic retry.
        
        If all retries fail, the entity is queued to disk.
        """
        try:
            self.session.add(entity)
            self.session.flush()
            logger.debug("Saved %s (id=%s)", type(entity).__name__, getattr(entity, 'id', None))
        except (OperationalError, IntegrityError) as e:
            logger.error("Failed to save %s: %s", type(entity).__name__, e)
            self._queue_to_disk(entity)
            raise DatabaseError(f"Save failed, queued: {e}") from e

    def _queue_to_disk(self, entity) -> None:
        """Queue entity to disk when DB is unavailable."""
        try:
            self._pending_queue.parent.mkdir(parents=True, exist_ok=True)
            data = self._entity_to_dict(entity)
            with open(self._pending_queue, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
            logger.warning("Entity queued to %s", self._pending_queue)
        except Exception as e:
            logger.critical("Failed to queue entity: %s", e)

    def _entity_to_dict(self, entity) -> Dict[str, Any]:
        """Convert entity to dict for queuing."""
        data = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
        data["_model"] = entity.__class__.__name__
        return data

    def flush_pending(self) -> int:
        """
        Flush pending writes from disk queue to database.
        
        Called on application startup to replay queued writes.
        """
        if not self._pending_queue.exists():
            return 0

        count = 0
        with self.session.begin():
            try:
                with open(self._pending_queue, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    try:
                        data = json.loads(line.strip())
                        entity = self._dict_to_entity(data)
                        self.session.add(entity)
                        count += 1
                    except Exception as e:
                        logger.error("Failed to replay queued write: %s", e)

                # Clear file on success
                self._pending_queue.unlink(missing_ok=True)
                logger.info("Flushed %d pending writes", count)
                return count
            except Exception as e:
                logger.error("Failed to flush pending writes: %s", e)
                raise

    def _dict_to_entity(self, data: Dict[str, Any]):
        """Convert dict back to entity."""
        model_name = data.pop("_model", None)
        if model_name is None:
            raise ValueError("Missing _model in queued data")

        # Map model name to class
        model_map = {
            "BatteryReading": BatteryReading,
            "ChargeCycleEvent": ChargeCycleEvent,
            "AlarmEvent": AlarmEvent,
            "CalibrationRecord": CalibrationRecord,
            "AutomationHookLog": AutomationHookLog,
        }

        model_class = model_map.get(model_name)
        if model_class is None:
            raise ValueError(f"Unknown model: {model_name}")

        # Parse datetime strings back to datetime objects
        for key, value in list(data.items()):
            if isinstance(value, str) and "T" in value:
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass

        return model_class(**data)


# ============================================================================
# Repository Implementations
# ============================================================================
class BatteryReadingRepository(BaseRepository):
    """Repository for BatteryReading entities."""

    model = BatteryReading

    def get_latest(self) -> Optional[BatteryReading]:
        """Get the most recent battery reading."""
        return self.session.query(BatteryReading).order_by(
            desc(BatteryReading.timestamp)
        ).first()

    def get_history(
        self,
        limit: int = 1000,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[BatteryReading]:
        """
        Get battery reading history with optional date range.

        Args:
            limit: Maximum number of records to return
            from_date: Start date (optional)
            to_date: End date (optional)

        Returns:
            List of BatteryReading objects, newest first
        """
        query = self.session.query(BatteryReading)

        if from_date:
            query = query.filter(BatteryReading.timestamp >= from_date)
        if to_date:
            query = query.filter(BatteryReading.timestamp <= to_date)

        return query.order_by(desc(BatteryReading.timestamp)).limit(limit).all()

    def get_average_percent(self, days: int = 7) -> Optional[float]:
        """Get average battery percentage over the last N days."""
        from_date = datetime.now() - timedelta(days=days)

        result = self.session.query(
            func.avg(BatteryReading.percent)
        ).filter(
            BatteryReading.timestamp >= from_date
        ).scalar()

        return float(result) if result is not None else None

    def get_charge_time_distribution(self, days: int = 30) -> Dict[str, float]:
        """Get distribution of charge levels over time."""
        from_date = datetime.now() - timedelta(days=days)

        bins = {
            "critical": (0, 20),
            "low": (20, 40),
            "medium": (40, 60),
            "high": (60, 80),
            "full": (80, 101),
        }

        result = {}
        for label, (low, high) in bins.items():
            count = self.session.query(BatteryReading).filter(
                BatteryReading.timestamp >= from_date,
                BatteryReading.percent >= low,
                BatteryReading.percent < high,
            ).count()
            result[label] = float(count)

        return result


class ChargeCycleRepository(BaseRepository):
    """Repository for ChargeCycleEvent entities."""

    model = ChargeCycleEvent

    def get_total_cycles(self) -> float:
        """Get total cycle count."""
        result = self.session.query(
            func.sum(ChargeCycleEvent.cycle_fraction)
        ).scalar()
        return float(result) if result is not None else 0.0

    def get_cycle_history(self, limit: int = 100) -> List[ChargeCycleEvent]:
        """Get recent charge cycle history."""
        return self.session.query(ChargeCycleEvent).order_by(
            desc(ChargeCycleEvent.started_at)
        ).limit(limit).all()


class AlarmEventRepository(BaseRepository):
    """Repository for AlarmEvent entities."""

    model = AlarmEvent

    def get_alarm_count(
        self,
        alarm_type: Optional[str] = None,
        days: int = 30,
    ) -> int:
        """Get alarm count filtered by type and days."""
        from_date = datetime.now() - timedelta(days=days)

        query = self.session.query(AlarmEvent).filter(
            AlarmEvent.timestamp >= from_date
        )

        if alarm_type:
            query = query.filter(AlarmEvent.alarm_type == alarm_type)

        return query.count()

    def get_alarm_history(
        self,
        alarm_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AlarmEvent]:
        """Get recent alarm history."""
        query = self.session.query(AlarmEvent)

        if alarm_type:
            query = query.filter(AlarmEvent.alarm_type == alarm_type)

        return query.order_by(desc(AlarmEvent.timestamp)).limit(limit).all()

    def get_snooze_rate(self, days: int = 30) -> float:
        """Get the rate at which alarms are snoozed."""
        from_date = datetime.now() - timedelta(days=days)

        total = self.session.query(AlarmEvent).filter(
            AlarmEvent.timestamp >= from_date
        ).count()

        if total == 0:
            return 0.0

        snoozed = self.session.query(AlarmEvent).filter(
            AlarmEvent.timestamp >= from_date,
            AlarmEvent.snoozed.is_(True),
        ).count()

        return snoozed / total


class CalibrationRepository(BaseRepository):
    """Repository for CalibrationRecord entities."""

    model = CalibrationRecord

    def get_latest_calibration(self) -> Optional[CalibrationRecord]:
        """Get the most recent calibration record."""
        return self.session.query(CalibrationRecord).order_by(
            desc(CalibrationRecord.started_at)
        ).first()

    def get_completed_calibrations(self) -> List[CalibrationRecord]:
        """Get all completed calibrations."""
        return self.session.query(CalibrationRecord).filter(
            CalibrationRecord.state == "complete"
        ).order_by(desc(CalibrationRecord.completed_at)).all()

    def get_aborted_calibrations(self) -> List[CalibrationRecord]:
        """Get all aborted calibrations."""
        return self.session.query(CalibrationRecord).filter(
            CalibrationRecord.state == "aborted"
        ).order_by(desc(CalibrationRecord.started_at)).all()

    def get_best_health_score(self) -> Optional[int]:
        """Get the best health score from any completed calibration."""
        result = self.session.query(
            func.max(CalibrationRecord.result_health_score)
        ).filter(
            CalibrationRecord.state == "complete",
            CalibrationRecord.result_health_score.isnot(None),
        ).scalar()

        return int(result) if result is not None else None


class AutomationHookRepository(BaseRepository):
    """Repository for AutomationHookLog entities."""

    model = AutomationHookLog

    def get_success_rate(
        self,
        hook_type: Optional[str] = None,
        days: int = 30,
    ) -> float:
        """Get success rate for automation hooks."""
        from_date = datetime.now() - timedelta(days=days)

        query = self.session.query(AutomationHookLog).filter(
            AutomationHookLog.timestamp >= from_date
        )

        if hook_type:
            query = query.filter(AutomationHookLog.hook_type == hook_type)

        total = query.count()
        if total == 0:
            return 0.0

        successes = query.filter(AutomationHookLog.success.is_(True)).count()
        return successes / total

    def get_recent_failures(
        self,
        limit: int = 10,
    ) -> List[AutomationHookLog]:
        """Get recent hook failures."""
        return self.session.query(AutomationHookLog).filter(
            AutomationHookLog.success.is_(False)
        ).order_by(desc(AutomationHookLog.timestamp)).limit(limit).all()


# ============================================================================
# Convenience Functions
# ============================================================================
def get_repository(repo_class, session: Optional[Session] = None):
    """Factory function to get a repository instance."""
    return repo_class(session)


def flush_all_pending() -> int:
    """Flush all pending writes across all repositories."""
    total = 0
    with get_session() as session:
        repos = [
            BatteryReadingRepository(session),
            ChargeCycleRepository(session),
            AlarmEventRepository(session),
            CalibrationRepository(session),
            AutomationHookRepository(session),
        ]
        for repo in repos:
            total += repo.flush_pending()
    return total