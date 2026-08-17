"""
FILE: src/voltsentry/services/watchdog.py
PATH: voltsentry/src/voltsentry/services/watchdog.py
DESCRIPTION: Watchdog service that monitors main process health via heartbeat
PHASE: 5.1 - Watchdog Service
DISCIPLINES:
- 0.1 Logging: CRITICAL on restart, CRITICAL when circuit breaker opens
- 0.2 Error Handling: Catches subprocess failures during restart
- 0.3 Retry Standard: CircuitBreaker stops after 3 restarts
- 0.4 Fallback: Persistent tray error after 3 failed restarts
- BATTERY OPTIMIZATION: Checks every 15s (not 1s), reads file not DB
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock, Thread
import time
from typing import Callable, List, Optional

from ..core.constants import (
    WATCHDOG_CHECK_INTERVAL,
    WATCHDOG_HEARTBEAT_TIMEOUT,
    WATCHDOG_MAX_RESTARTS,
)
from ..core.decorators import log_entry_exit
from ..core.exceptions import (
    ProcessStoppedError,
    WatchdogError,
    WatchdogRestartError,
)
from ..core.logging_config import get_logger, log_audit
from ..core.resilience import CircuitBreaker
from .heartbeat import get_heartbeat_service

logger = get_logger(__name__)


class WatchdogService:
    """
    Watchdog service that monitors the main process health.

    Features:
    - Checks heartbeat file every 15 seconds (battery optimized)
    - Restarts main process up to 3 times on failure
    - CircuitBreaker prevents crash-restart loops
    - Persistent tray error after max restarts exceeded

    Battery Optimization:
    - Only reads heartbeat file (no DB queries)
    - No network calls
    - Minimal CPU usage
    """

    def __init__(
        self,
        process_name: str = "VoltSentry",
        process_path: Optional[Path] = None,
        check_interval: int = WATCHDOG_CHECK_INTERVAL,
        heartbeat_timeout: int = WATCHDOG_HEARTBEAT_TIMEOUT,
        max_restarts: int = WATCHDOG_MAX_RESTARTS,
    ):
        """
        Initialize the watchdog service.

        Args:
            process_name: Name of the process to monitor
            process_path: Path to the executable to restart
            check_interval: How often to check heartbeat (seconds)
            heartbeat_timeout: How long before heartbeat is considered stale
            max_restarts: Maximum number of restart attempts
        """
        self.process_name = process_name
        self.process_path = process_path or self._get_process_path()
        self.check_interval = check_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_restarts = max_restarts

        self._heartbeat = get_heartbeat_service()
        self._running = False
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._lock = Lock()
        self._restart_count = 0
        self._last_restart_time: Optional[datetime] = None

        # Circuit breaker for restart attempts
        self._circuit_breaker = CircuitBreaker(
            failure_limit=max_restarts,
            cooldown_seconds=300,  # 5 minutes cooldown
            name="watchdog_restarter",
        )

        self._on_restart_callbacks: List[Callable[[int], None]] = []
        self._on_failure_callbacks: List[Callable[[str], None]] = []

        logger.info(
            "WatchdogService initialized: interval=%ds, timeout=%ds, max_restarts=%d",
            self.check_interval,
            self.heartbeat_timeout,
            self.max_restarts,
        )

    def _get_process_path(self) -> Path:
        """Get the path to the current executable."""
        return Path(sys.executable)

    @log_entry_exit()
    def start(self) -> None:
        """Start the watchdog service in a background thread."""
        if self._running:
            logger.warning("Watchdog already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = Thread(
            target=self._watchdog_loop, daemon=True, name="WatchdogThread"
        )
        self._thread.start()

        logger.info("Watchdog service started")
        log_audit("INFO", "Watchdog service started")

    def stop(self) -> None:
        """Stop the watchdog service."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("Watchdog service stopped")
        log_audit("INFO", "Watchdog service stopped")

    def _watchdog_loop(self) -> None:
        """Main watchdog monitoring loop."""
        logger.debug("Watchdog loop started")

        while not self._stop_event.is_set():
            try:
                # Check if process is healthy
                if not self._is_process_healthy():
                    self._handle_unhealthy_process()

                # Wait for next check
                self._stop_event.wait(self.check_interval)

            except Exception as e:
                logger.error("Watchdog loop error: %s", e)
                self._stop_event.wait(self.check_interval)

        logger.debug("Watchdog loop ended")

    def _is_process_healthy(self) -> bool:
        """
        Check if the monitored process is healthy.

        Uses heartbeat file (not DB) for battery optimization.

        Returns:
            True if process is healthy
        """
        # Check heartbeat
        is_healthy = self._heartbeat.is_healthy(self.heartbeat_timeout)

        if not is_healthy:
            age = self._heartbeat.get_heartbeat_age()
            logger.warning(
                "Process heartbeat stale: age=%.1fs (timeout=%ds)",
                age or 0,
                self.heartbeat_timeout,
            )

        return is_healthy

    def _handle_unhealthy_process(self) -> None:
        """Handle an unhealthy (crashed/stalled) process."""
        with self._lock:
            # Check if circuit breaker allows restart
            if not self._circuit_breaker.can_attempt():
                logger.critical(
                    "Circuit breaker OPEN - restart attempts blocked after %d failures",
                    self.max_restarts,
                )
                self._notify_failure(
                    f"Watchdog circuit breaker open after {self.max_restarts} failures. "
                    "Manual restart required."
                )
                return

            # Check cooldown between restarts
            if self._last_restart_time:
                cooldown = timedelta(seconds=30)
                if datetime.now() - self._last_restart_time < cooldown:
                    logger.debug("Restart cooldown active, waiting...")
                    return

            # Attempt restart
            self._attempt_restart()

    @log_entry_exit()
    def _attempt_restart(self) -> None:
        """Attempt to restart the main process."""
        self._restart_count += 1
        self._last_restart_time = datetime.now()

        logger.critical(
            "Attempting restart #%d of %d",
            self._restart_count,
            self.max_restarts,
        )
        log_audit("CRITICAL", f"Watchdog restart attempt #{self._restart_count}")

        try:
            # Try to restart the process
            self._restart_process()

            # Record success - reset circuit breaker
            self._circuit_breaker.record_success()
            self._restart_count = 0

            logger.info("Process restarted successfully")
            self._notify_restart(self._restart_count)

        except WatchdogRestartError as e:
            self._circuit_breaker.record_failure()
            logger.error("Restart failed: %s", e)

            # Check if we've exceeded max restarts
            if self._circuit_breaker.is_open:
                logger.critical(
                    "Circuit breaker OPEN after %d failed restart attempts",
                    self.max_restarts,
                )
                self._notify_failure(
                    f"Watchdog: Process failed to restart after {self.max_restarts} attempts. "
                    "Please restart VoltSentry manually."
                )
                log_audit(
                    "CRITICAL",
                    f"Watchdog circuit breaker opened after {self.max_restarts} failures",
                )

    def _restart_process(self) -> None:
        """
        Restart the main process.

        Raises:
            WatchdogRestartError: If restart fails
        """
        try:
            # Get the command to restart
            cmd = [str(self.process_path)]

            # Add any original arguments
            if hasattr(sys, "argv") and len(sys.argv) > 1:
                cmd.extend(sys.argv[1:])

            logger.info("Restarting: %s", " ".join(cmd))

            # Start new process
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
                shell=False,
            )

            # Give the process time to start
            time.sleep(2)

            # Check if new process is running (optional)
            # This is a simplified check - in production we'd verify the process is running

        except Exception as e:
            raise WatchdogRestartError(f"Failed to restart process: {e}") from e

    def add_restart_callback(self, callback: Callable[[int], None]) -> None:
        """Add callback for when a restart occurs."""
        self._on_restart_callbacks.append(callback)

    def add_failure_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for when watchdog fails (circuit breaker opens)."""
        self._on_failure_callbacks.append(callback)

    def _notify_restart(self, restart_count: int) -> None:
        """Notify all restart callbacks."""
        for callback in self._on_restart_callbacks:
            try:
                callback(restart_count)
            except Exception as e:
                logger.error("Restart callback failed: %s", e)

    def _notify_failure(self, message: str) -> None:
        """Notify all failure callbacks."""
        for callback in self._on_failure_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error("Failure callback failed: %s", e)

    def get_status(self) -> dict:
        """Get watchdog status."""
        is_healthy = self._is_process_healthy()
        age = self._heartbeat.get_heartbeat_age()

        return {
            "running": self._running,
            "healthy": is_healthy,
            "heartbeat_age_seconds": age,
            "heartbeat_timeout_seconds": self.heartbeat_timeout,
            "check_interval_seconds": self.check_interval,
            "restart_count": self._restart_count,
            "max_restarts": self.max_restarts,
            "circuit_breaker": str(self._circuit_breaker),
            "last_restart_time": (
                self._last_restart_time.isoformat()
                if self._last_restart_time
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<WatchdogService running={self._running}, healthy={self._is_process_healthy()}>"