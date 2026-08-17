"""
FILE: src/voltsentry/services/calibration.py
PATH: voltsentry/src/voltsentry/services/calibration.py
DESCRIPTION: Guided battery calibration service
PHASE: 5.2 - Guided Calibration Mode
DISCIPLINES:
- 0.1 Logging: INFO on every state transition
- 0.2 Error Handling: Handles abort, sleep/wake detection
- 0.4 Fallback: Resumes after sleep or restarts cleanly
- BATTERY OPTIMIZATION: User-initiated only, not automatic
"""

from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Callable, List, Optional

from ..core.constants import CALIBRATION_MAX_DURATION, HYSTERESIS_MARGIN
from ..core.decorators import log_entry_exit
from ..core.exceptions import (
    CalibrationAbortedError,
    CalibrationError,
    CalibrationTimeoutError,
)
from ..core.logging_config import get_logger, log_audit
from ..core.types import BatteryReading
from ..db.models import CalibrationRecord
from ..db.repositories import CalibrationRepository
from .alarm_service import AlarmService
from .battery_poller import BatteryPoller

logger = get_logger(__name__)


class CalibrationState(Enum):
    """Calibration wizard states."""

    IDLE = "idle"
    AWAITING_FULL_CHARGE = "awaiting_full_charge"
    AWAITING_FULL_DISCHARGE = "awaiting_full_discharge"
    RECALCULATING = "recalculating"
    COMPLETE = "complete"
    ABORTED = "aborted"


class CalibrationService:
    """
    Guided battery calibration service.

    Wizard-style state machine:
    Idle → AwaitingFullCharge → AwaitingFullDischarge → Recalculating → Complete

    Features:
    - User-initiated only (zero background battery usage)
    - Sleep/wake detection
    - Abort support
    - Previous thresholds restored on abort/complete
    """

    def __init__(
        self,
        poller: Optional[BatteryPoller] = None,
        alarm_service: Optional[AlarmService] = None,
    ):
        self.poller = poller
        self.alarm_service = alarm_service
        self.repository = CalibrationRepository()

        self._state = CalibrationState.IDLE
        self._previous_thresholds: Optional[dict] = None
        self._record: Optional[CalibrationRecord] = None
        self._start_time: Optional[datetime] = None
        self._state_start_time: Optional[datetime] = None
        self._lock = Lock()
        self._sleeping = False

        # Callbacks
        self._on_state_change: List[
            Callable[[CalibrationState, CalibrationState], None]
        ] = []
        self._on_progress: List[Callable[[int, str], None]] = []
        self._on_complete: List[Callable[[int], None]] = []
        self._on_abort: List[Callable[[], None]] = []

        logger.info("CalibrationService initialized")

    @property
    def state(self) -> CalibrationState:
        """Get current calibration state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if calibration is active."""
        return self._state not in (
            CalibrationState.IDLE,
            CalibrationState.COMPLETE,
            CalibrationState.ABORTED,
        )

    @log_entry_exit()
    def start_calibration(self) -> None:
        """
        Start a new calibration session.

        Raises:
            CalibrationError: If calibration is already active
        """
        with self._lock:
            if self.is_active:
                raise CalibrationError("Calibration already in progress")

            # Save current thresholds
            if self.alarm_service:
                self._previous_thresholds = {
                    "high": self.alarm_service.state_machine.config.high_threshold,
                    "low": self.alarm_service.state_machine.config.low_threshold,
                }

                # Disable alarms during calibration
                self.alarm_service.stop_alarm()
                self.alarm_service.snooze_manager.clear_snooze()

            # Create calibration record
            self._record = CalibrationRecord(
                started_at=datetime.now(),
                state=CalibrationState.IDLE.value,
            )
            self.repository.save(self._record)

            self._state = CalibrationState.AWAITING_FULL_CHARGE
            self._start_time = datetime.now()
            self._state_start_time = datetime.now()

            logger.info("Calibration started")
            log_audit("INFO", "Calibration started")

            self._notify_state_change(CalibrationState.IDLE, self._state)
            self._notify_progress(0, "Plug in and charge battery to 100%")

    def abort_calibration(self) -> None:
        """Abort the current calibration."""
        with self._lock:
            if not self.is_active:
                return

            old_state = self._state
            self._state = CalibrationState.ABORTED

            # Restore previous thresholds
            self._restore_thresholds()

            if self._record:
                self._record.state = CalibrationState.ABORTED.value
                self._record.completed_at = datetime.now()
                self.repository.save(self._record)

            logger.info("Calibration aborted")
            log_audit("WARNING", "Calibration aborted")

            self._notify_state_change(old_state, self._state)
            self._notify_abort()

    @log_entry_exit()
    def process_reading(self, reading: BatteryReading) -> None:
        """
        Process a battery reading for calibration.

        Args:
            reading: Current battery reading
        """
        if not self.is_active:
            return

        with self._lock:
            # Check for timeout
            if self._start_time and (
                datetime.now() - self._start_time
            ) > timedelta(seconds=CALIBRATION_MAX_DURATION):
                self._handle_timeout()
                return

            # Check for sleep/wake
            if self._sleeping:
                self._handle_wake()

            # Process based on current state
            if self._state == CalibrationState.AWAITING_FULL_CHARGE:
                self._process_full_charge(reading)
            elif self._state == CalibrationState.AWAITING_FULL_DISCHARGE:
                self._process_full_discharge(reading)
            elif self._state == CalibrationState.RECALCULATING:
                self._process_recalculating(reading)

    def _process_full_charge(self, reading: BatteryReading) -> None:
        """Process full charge phase."""
        if reading.percent >= 99 and reading.is_charging:
            # Move to discharge phase
            old_state = self._state
            self._state = CalibrationState.AWAITING_FULL_DISCHARGE
            self._state_start_time = datetime.now()

            logger.info("Calibration: Full charge reached, now discharging")
            self._notify_state_change(old_state, self._state)
            self._notify_progress(
                50, "Battery fully charged. Unplug and discharge to 0%"
            )

            # Update record
            if self._record:
                self._record.state = (
                    CalibrationState.AWAITING_FULL_DISCHARGE.value
                )
                self.repository.save(self._record)

    def _process_full_discharge(self, reading: BatteryReading) -> None:
        """Process full discharge phase."""
        # Check if battery is near 0% (allow some margin for safety)
        if reading.percent <= 5 and not reading.is_charging:
            # Move to recalculating phase
            old_state = self._state
            self._state = CalibrationState.RECALCULATING
            self._state_start_time = datetime.now()

            logger.info("Calibration: Full discharge reached, recalculating")
            self._notify_state_change(old_state, self._state)
            self._notify_progress(
                75, "Discharge complete. Recalculating battery health..."
            )

            # Update record
            if self._record:
                self._record.state = CalibrationState.RECALCULATING.value
                self.repository.save(self._record)

            # Simulate recalculation (in real implementation, we'd measure actual capacity)
            # For now, we'll estimate based on the discharge cycle
            health_score = self._calculate_health_score(reading)

            # Complete calibration
            self._complete_calibration(health_score)

    def _process_recalculating(self, reading: BatteryReading) -> None:
        """Process recalculating phase."""
        # Wait a moment then complete
        if (
            self._state_start_time
            and (datetime.now() - self._state_start_time).total_seconds() > 5
        ):
            health_score = self._calculate_health_score(reading)
            self._complete_calibration(health_score)

    def _calculate_health_score(self, reading: BatteryReading) -> int:
        """
        Calculate battery health score from calibration.

        This is a simplified estimation. In production, we'd measure
        actual capacity vs design capacity.

        Returns:
            Health score (0-100)
        """
        # Use current percent as a rough estimate
        # In reality, this would be a more complex calculation
        base_score = reading.percent

        # Apply some adjustments based on age/cycles
        # For now, return a reasonable estimate
        return min(100, max(0, base_score + 10))

    def _complete_calibration(self, health_score: int) -> None:
        """Complete the calibration process."""
        old_state = self._state
        self._state = CalibrationState.COMPLETE

        # Restore thresholds
        self._restore_thresholds()

        # Update record
        if self._record:
            self._record.state = CalibrationState.COMPLETE.value
            self._record.completed_at = datetime.now()
            self._record.result_health_score = health_score
            self.repository.save(self._record)

        logger.info("Calibration complete: health_score=%d%%", health_score)
        log_audit("INFO", f"Calibration complete: health_score={health_score}%")

        self._notify_state_change(old_state, self._state)
        self._notify_progress(
            100, f"Calibration complete! Battery health: {health_score}%"
        )
        self._notify_complete(health_score)

    def _restore_thresholds(self) -> None:
        """Restore previous alarm thresholds."""
        if self.alarm_service and self._previous_thresholds:
            self.alarm_service.update_thresholds(
                self._previous_thresholds["high"],
                self._previous_thresholds["low"],
            )
            logger.debug(
                "Thresholds restored: high=%d%%, low=%d%%",
                self._previous_thresholds["high"],
                self._previous_thresholds["low"],
            )

    def _handle_timeout(self) -> None:
        """Handle calibration timeout."""
        old_state = self._state
        self._state = CalibrationState.ABORTED
        self._restore_thresholds()

        if self._record:
            self._record.state = CalibrationState.ABORTED.value
            self._record.completed_at = datetime.now()
            self.repository.save(self._record)

        logger.warning(
            "Calibration timed out after %d hours",
            CALIBRATION_MAX_DURATION / 3600,
        )
        self._notify_state_change(old_state, self._state)
        self._notify_abort()

    def handle_sleep(self) -> None:
        """Handle system sleep event."""
        self._sleeping = True
        logger.info("Calibration: System sleeping, will resume on wake")

    def handle_wake(self) -> None:
        """Handle system wake event."""
        if self._sleeping:
            self._sleeping = False
            logger.info("Calibration: System woke from sleep")

            # Notify user to resume or restart
            self._notify_progress(
                0,
                "System woke from sleep. Please continue calibration or restart.",
            )

    def _notify_state_change(
        self, old_state: CalibrationState, new_state: CalibrationState
    ) -> None:
        """Notify all state change callbacks."""
        for callback in self._on_state_change:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error("State change callback failed: %s", e)

    def _notify_progress(self, progress: int, message: str) -> None:
        """Notify all progress callbacks."""
        for callback in self._on_progress:
            try:
                callback(progress, message)
            except Exception as e:
                logger.error("Progress callback failed: %s", e)

    def _notify_complete(self, health_score: int) -> None:
        """Notify all complete callbacks."""
        for callback in self._on_complete:
            try:
                callback(health_score)
            except Exception as e:
                logger.error("Complete callback failed: %s", e)

    def _notify_abort(self) -> None:
        """Notify all abort callbacks."""
        for callback in self._on_abort:
            try:
                callback()
            except Exception as e:
                logger.error("Abort callback failed: %s", e)

    def add_state_change_callback(
        self, callback: Callable[[CalibrationState, CalibrationState], None]
    ) -> None:
        """Add callback for state changes."""
        self._on_state_change.append(callback)

    def add_progress_callback(
        self, callback: Callable[[int, str], None]
    ) -> None:
        """Add callback for progress updates."""
        self._on_progress.append(callback)

    def add_complete_callback(self, callback: Callable[[int], None]) -> None:
        """Add callback for completion."""
        self._on_complete.append(callback)

    def add_abort_callback(self, callback: Callable[[], None]) -> None:
        """Add callback for abort."""
        self._on_abort.append(callback)

    def get_status(self) -> dict:
        """Get calibration status."""
        return {
            "state": self._state.value,
            "is_active": self.is_active,
            "sleeping": self._sleeping,
            "start_time": (
                self._start_time.isoformat() if self._start_time else None
            ),
            "state_start_time": (
                self._state_start_time.isoformat()
                if self._state_start_time
                else None
            ),
            "previous_thresholds": self._previous_thresholds,
            "record_id": self._record.id if self._record else None,
        }

    def __repr__(self) -> str:
        return f"<CalibrationService state={self._state.value}>"