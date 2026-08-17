"""
FILE: src/voltsentry/services/battery_poller.py
PATH: voltsentry/src/voltsentry/services/battery_poller.py
DESCRIPTION: Core battery polling service with degraded mode support
PHASE: 2.1 - Battery Polling Service

DISCIPLINES:
- 0.1 Logging Standard: DEBUG per poll, INFO on state changes, ERROR on failures
- 0.2 Error Handling: Specific exception catching, no bare except
- 0.3 Retry Standard: 3 attempts with exponential backoff on OSError
- 0.4 Fallback Standard: Degraded mode after 5 consecutive failures
"""

import time
from datetime import datetime
from threading import Lock
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
import psutil

from ..core.constants import DEFAULT_POLL_INTERVAL_SECONDS, HYSTERESIS_MARGIN
from ..core.decorators import log_entry_exit, timed, with_retry
from ..core.exceptions import BatteryReadError
from ..core.logging_config import get_logger
from ..core.resilience import CircuitBreaker, resilient
from ..core.types import BatteryReading, ChargingState, HealthSource
from ..db.models import BatteryReading as BatteryReadingModel
from ..db.repositories import BatteryReadingRepository

logger = get_logger(__name__)


class BatteryPollerSignals(QObject):
    """Signals for battery poller events."""

    reading_updated = pyqtSignal(object)  # BatteryReading
    state_changed = pyqtSignal(str, str)  # old_state, new_state
    error_occurred = pyqtSignal(str)
    degraded_mode_entered = pyqtSignal()
    degraded_mode_exited = pyqtSignal()


class BatteryPoller(QObject):
    """
    Battery polling service with degraded mode support.

    Polls battery status every `poll_interval_seconds` and emits signals
    with the latest reading. Enters degraded mode after 5 consecutive
    failures, backing off to 30-second polling intervals.
    """

    # Signals for UI & service communication
    reading_updated = pyqtSignal(object)  # BatteryReading
    state_changed = pyqtSignal(str, str)  # old_state, new_state
    error_occurred = pyqtSignal(str)
    degraded_mode_entered = pyqtSignal()
    degraded_mode_exited = pyqtSignal()

    def __init__(
        self,
        repository: Optional[BatteryReadingRepository] = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        """
        Initialize the battery poller.

        Args:
            repository: BatteryReadingRepository instance
            poll_interval: Polling interval in seconds
        """
        super().__init__()

        self.repository = repository or BatteryReadingRepository()
        self.poll_interval = poll_interval
        self._current_reading: Optional[BatteryReading] = None
        self._previous_reading: Optional[BatteryReading] = None
        self._charging_state = ChargingState.UNKNOWN
        self._consecutive_failures = 0
        self._degraded_mode = False
        self._degraded_poll_interval = 30  # seconds
        self._is_running = False
        self._lock = Lock()

        # Circuit breaker for persistent failures
        self._circuit_breaker = CircuitBreaker(
            failure_limit=5, name="battery_poller"
        )

        # Set up the polling timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.setInterval(self.poll_interval * 1000)  # Convert to ms

        logger.info(
            "BatteryPoller initialized: interval=%ds, degraded_interval=%ds",
            self.poll_interval,
            self._degraded_poll_interval,
        )

    @property
    def current_reading(self) -> Optional[BatteryReading]:
        """Get the most recent battery reading."""
        with self._lock:
            return self._current_reading

    @property
    def is_running(self) -> bool:       
        return self._is_running

    @property
    def is_degraded(self) -> bool:
        """Check if the poller is in degraded mode."""
        return self._degraded_mode

    def start(self) -> None:
        """Start the polling service."""
        if self._is_running:
            logger.warning("Poller already running")
            return

        self._is_running = True
        self._timer.start()
        logger.info("Battery poller started with interval %ds", self.poll_interval)

        # Do an immediate initial poll
        self._poll()

    def stop(self) -> None:
        """Stop the polling service."""
        if not self._is_running:
            return

        self._is_running = False
        self._timer.stop()
        logger.info("Battery poller stopped")

    def set_poll_interval(self, interval_seconds: int) -> None:
        """Change the polling interval."""
        if interval_seconds < 1:
            raise ValueError("Poll interval must be at least 1 second")

        self.poll_interval = interval_seconds
        if self._is_running and not self._degraded_mode:
            self._timer.setInterval(interval_seconds * 1000)
            logger.info("Poll interval updated to %ds", interval_seconds)

    @log_entry_exit()
    @timed()
    def _poll(self) -> None:
        """
        Perform a single battery poll.

        Called by the timer at the specified interval.
        """
        if not self._is_running:
            return

        # Check if circuit breaker is open
        if self._circuit_breaker.is_open:
            logger.warning("Circuit breaker open, skipping poll")
            return

        try:
            reading = self._read_battery()
            self._consecutive_failures = 0
            self._circuit_breaker.record_success()

            # Exit degraded mode if previously degraded
            if self._degraded_mode:
                self._degraded_mode = False
                self._timer.setInterval(self.poll_interval * 1000)
                self.degraded_mode_exited.emit()
                logger.info(
                    "Exited degraded mode, restored %ds interval", self.poll_interval
                )

            # Process the reading
            self._process_reading(reading)

        except BatteryReadError as e:
            self._consecutive_failures += 1
            self._circuit_breaker.record_failure()
            logger.error(
                "Battery read failed (%d consecutive failures): %s",
                self._consecutive_failures,
                e,
            )

            # Check if we should enter degraded mode
            if self._consecutive_failures >= 5 and not self._degraded_mode:
                self._degraded_mode = True
                self._timer.setInterval(self._degraded_poll_interval * 1000)
                self.degraded_mode_entered.emit()
                self.error_occurred.emit(
                    f"Entering degraded mode: {self._consecutive_failures} consecutive failures"
                )
                logger.warning(
                    "Entered degraded mode: polling every %ds",
                    self._degraded_poll_interval,
                )

            self.error_occurred.emit(str(e))

    @with_retry(attempts=3, exceptions=(OSError,))
    def _read_battery(self) -> BatteryReading:
        """
        Read battery status from the system.

        Returns:
            BatteryReading object

        Raises:
            BatteryReadError: If battery status cannot be obtained
        """
        try:
            battery = psutil.sensors_battery()
        except (OSError, AttributeError) as e:
            raise BatteryReadError(f"psutil battery sensor failed: {e}") from e

        if battery is None:
            raise BatteryReadError("No battery detected on this system")

        # Create reading data struct
        reading = BatteryReading(
            timestamp=datetime.now(),
            percent=int(battery.percent),
            is_charging=bool(battery.power_plugged),
            power_draw_watts=None,  # Updated by power_draw service
            source=HealthSource.ESTIMATED,  # Updated by battery_report service
        )

        logger.debug(
            "Battery reading: %d%%, charging=%s",
            reading.percent,
            reading.is_charging,
        )

        return reading

    def _process_reading(self, reading: BatteryReading) -> None:
        """
        Process a new battery reading.

        Detects state changes and emits signals.
        """
        with self._lock:
            self._previous_reading = self._current_reading
            self._current_reading = reading

            # Detect state change
            old_state = self._charging_state
            new_state = self._determine_charging_state(reading)

            if old_state != new_state:
                self._charging_state = new_state
                self.state_changed.emit(old_state.value, new_state.value)
                logger.info(
                    "Charging state changed: %s → %s",
                    old_state.value,
                    new_state.value,
                )

            # Emit the reading
            self.reading_updated.emit(reading)

            # Save to database (if not in degraded mode)
            if not self._degraded_mode:
                self._save_reading(reading)

    def _determine_charging_state(self, reading: BatteryReading) -> ChargingState:
        """Determine the charging state from a reading."""
        if reading.is_charging:
            if reading.percent >= 100:
                return ChargingState.FULL
            return ChargingState.CHARGING
        return ChargingState.DISCHARGING

    def _save_reading(self, reading: BatteryReading) -> None:
        """Save a reading to the database."""
        try:
            model = BatteryReadingModel(
                timestamp=reading.timestamp,
                percent=reading.percent,
                is_charging=reading.is_charging,
                power_draw_watts=reading.power_draw_watts,
                source=reading.source.value
                if hasattr(reading.source, "value")
                else str(reading.source),
            )
            self.repository.save(model)
        except Exception as e:
            logger.error("Failed to save reading to database: %s", e)
            # Suppress exception so poller loop continues seamlessly

    def get_state_info(self) -> dict:
        """Get current poller state information."""
        with self._lock:
            return {
                "is_running": self._is_running,
                "is_degraded": self._degraded_mode,
                "poll_interval": self.poll_interval,
                "consecutive_failures": self._consecutive_failures,
                "current_percent": self._current_reading.percent
                if self._current_reading
                else None,
                "charging_state": self._charging_state.value
                if self._charging_state
                else None,
                "circuit_breaker": str(self._circuit_breaker),
            }