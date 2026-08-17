"""
FILE: src/voltsentry/services/heartbeat.py
PATH: voltsentry/src/voltsentry/services/heartbeat.py
DESCRIPTION: Heartbeat service for watchdog monitoring
PHASE: 2.4 - Polling Scheduler & Heartbeat

DISCIPLINES:
- 0.1 Logging Standard: CRITICAL if heartbeat stops updating
- 0.2 Error Handling: Wrapped in try/except
- 0.4 Fallback Standard: Heartbeat file as fallback for DB
"""

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from threading import Lock
import time
from typing import Optional

import psutil

from ..core.constants import DATA_DIR
from ..core.decorators import log_entry_exit
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class HeartbeatService:
    """
    Heartbeat service for watchdog monitoring.

    Writes a timestamp at regular intervals so the watchdog can
    detect if the main process has stopped.
    """

    def __init__(self):
        self._heartbeat_path = DATA_DIR / "heartbeat.json"
        self._last_heartbeat: Optional[datetime] = None
        self._lock = Lock()
        self._enabled = True

        # Ensure directory exists
        self._heartbeat_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("HeartbeatService initialized: %s", self._heartbeat_path)

    @log_entry_exit()
    def beat(self) -> None:
        """Record a heartbeat (timestamp)."""
        if not self._enabled:
            return

        try:
            now = datetime.now()
            with self._lock:
                self._last_heartbeat = now

            # Write to file (for watchdog)
            self._write_heartbeat(now)

            logger.debug("Heartbeat: %s", now.isoformat())

        except Exception as e:
            logger.error("Failed to write heartbeat: %s", e)

    def _write_heartbeat(self, timestamp: datetime) -> None:
        """Write heartbeat to file atomically."""
        try:
            data = {
                "timestamp": timestamp.isoformat(),
                "pid": self._get_pid(),
                "uptime": self._get_uptime(),
            }
            # Write to temporary file then swap atomically to avoid race conditions
            tmp_file = self._heartbeat_path.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            tmp_file.replace(self._heartbeat_path)
        except Exception as e:
            logger.warning("Failed to write heartbeat file: %s", e)

    def get_last_heartbeat(self) -> Optional[datetime]:
        """Get the timestamp of the last heartbeat."""
        with self._lock:
            if self._last_heartbeat is not None:
                return self._last_heartbeat

        # Try to read from file
        try:
            if self._heartbeat_path.exists():
                data = json.loads(self._heartbeat_path.read_text(encoding="utf-8"))
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
        except Exception:
            pass

        return None

    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        """
        Check if the heartbeat is healthy.

        Args:
            timeout_seconds: Maximum age of last heartbeat in seconds

        Returns:
            True if last heartbeat is within timeout
        """
        last = self.get_last_heartbeat()
        if last is None:
            return False

        age = (datetime.now() - last).total_seconds()
        return age < timeout_seconds

    def get_heartbeat_age(self) -> Optional[float]:
        """Get the age of the last heartbeat in seconds."""
        last = self.get_last_heartbeat()
        if last is None:
            return None
        return (datetime.now() - last).total_seconds()

    def enable(self) -> None:
        """Enable heartbeat recording."""
        self._enabled = True

    def disable(self) -> None:
        """Disable heartbeat recording."""
        self._enabled = False

    def _get_pid(self) -> int:
        """Get the current process ID."""
        return os.getpid()

    def _get_uptime(self) -> float:
        """Get process uptime in seconds."""
        try:
            process = psutil.Process(os.getpid())
            return time.time() - process.create_time()
        except Exception:
            return 0.0

    def get_status(self) -> dict:
        """Get heartbeat status information."""
        last = self.get_last_heartbeat()
        age = self.get_heartbeat_age()
        healthy = self.is_healthy() if age is not None else False

        return {
            "enabled": self._enabled,
            "last_heartbeat": last.isoformat() if last else None,
            "age_seconds": age,
            "healthy": healthy,
            "pid": self._get_pid(),
            "heartbeat_file": str(self._heartbeat_path),
        }


# ============================================================================
# Global instance
# ============================================================================
_heartbeat_service: Optional[HeartbeatService] = None


def get_heartbeat_service() -> HeartbeatService:
    """Get or create the global heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service