"""
FILE: src/voltsentry/services/snooze_manager.py
PATH: voltsentry/src/voltsentry/services/snooze_manager.py
DESCRIPTION: Snooze and quiet hours management
PHASE: 3.4 - Snooze & Quiet Hours

DISCIPLINES:
- 0.1 Logging Standard: INFO on snooze, DEBUG on quiet hours checks
- 0.2 Error Handling: Validate time formats
- 0.4 Fallback Standard: Fallback to manual quiet hours if Focus Assist unavailable
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, time
from enum import Enum
from typing import Optional, Callable

from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit
from ..core.validators import validate_time_format

logger = get_logger(__name__)


class SnoozeDuration(Enum):
    """Available snooze durations."""
    OFF = 0
    FIVE_MIN = 5
    TEN_MIN = 10
    FIFTEEN_MIN = 15
    THIRTY_MIN = 30


@dataclass
class QuietHoursConfig:
    """Configuration for quiet hours."""
    enabled: bool = False
    start_time: str = "22:00"  # HH:MM format
    end_time: str = "07:00"    # HH:MM format
    respect_focus_assist: bool = True


class SnoozeManager:
    """
    Manages alarm snooze and quiet hours.
    
    Features:
    - Snooze with configurable durations (5, 10, 15, 30 min)
    - Quiet hours with midnight wrap support
    - Optional Windows Focus Assist integration
    """
    
    def __init__(self):
        self._snooze_until: Optional[datetime] = None
        self._snooze_duration = SnoozeDuration.FIFTEEN_MIN
        self._quiet_hours = QuietHoursConfig()
        self._focus_assist_active = False
        self._on_quiet_hours_change: Optional[Callable[[bool], None]] = None
        self._focus_assist_available = self._check_focus_assist_available()
        
        logger.info(
            "SnoozeManager initialized: snooze_duration=%d min, quiet_hours=%s",
            self._snooze_duration.value,
            "enabled" if self._quiet_hours.enabled else "disabled",
        )
    
    def _check_focus_assist_available(self) -> bool:
        """Check if Windows Focus Assist API is available."""
        try:
            import ctypes
            # Verify shell32 dll availability for Windows notification state
            _ = ctypes.windll.shell32
            return True
        except (ImportError, AttributeError, OSError) as e:
            logger.debug("Focus Assist API unavailable, using scheduled quiet hours fallback: %s", e)
            return False
    
    def set_snooze_duration(self, duration: SnoozeDuration) -> None:
        """Set the default snooze duration."""
        if not isinstance(duration, SnoozeDuration):
            logger.warning("Invalid SnoozeDuration provided: %s. Ignoring.", duration)
            return

        if duration == SnoozeDuration.OFF:
            self._snooze_duration = duration
            logger.info("Snooze disabled")
        else:
            self._snooze_duration = duration
            logger.info("Snooze duration set to %d minutes", duration.value)
    
    @log_entry_exit()
    def snooze(self, duration_minutes: Optional[int] = None) -> datetime:
        """
        Snooze the current alarm.
        
        Args:
            duration_minutes: Override default duration (optional)
            
        Returns:
            Datetime when snooze expires
        """
        minutes = duration_minutes if duration_minutes is not None else self._snooze_duration.value
        
        if minutes <= 0:
            logger.debug("Snooze skipped (duration <= 0)")
            return datetime.now()
        
        self._snooze_until = datetime.now() + timedelta(minutes=minutes)
        logger.info("Alarm snoozed until %s", self._snooze_until.isoformat())
        
        return self._snooze_until
    
    def is_snoozed(self) -> bool:
        """Check if currently snoozed."""
        if self._snooze_until is None:
            return False
        return datetime.now() < self._snooze_until
    
    def get_snooze_remaining(self) -> Optional[int]:
        """Get remaining snooze time in seconds."""
        if self._snooze_until is None:
            return None
        remaining = (self._snooze_until - datetime.now()).total_seconds()
        return max(0, int(remaining)) if remaining > 0 else 0
    
    def clear_snooze(self) -> None:
        """Clear the current snooze."""
        self._snooze_until = None
        logger.debug("Snooze cleared")
    
    def set_quiet_hours(
        self,
        enabled: bool,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        respect_focus_assist: Optional[bool] = None,
    ) -> None:
        """
        Configure quiet hours.
        
        Args:
            enabled: Enable/disable quiet hours
            start_time: Start time (HH:MM format)
            end_time: End time (HH:MM format)
            respect_focus_assist: Respect Windows Focus Assist
        """
        self._quiet_hours.enabled = bool(enabled)
        
        if start_time is not None:
            try:
                validate_time_format(start_time)
                self._quiet_hours.start_time = start_time
            except ValueError as e:
                logger.error("Invalid start_time format '%s': %s. Retaining '%s'.", start_time, e, self._quiet_hours.start_time)
        
        if end_time is not None:
            try:
                validate_time_format(end_time)
                self._quiet_hours.end_time = end_time
            except ValueError as e:
                logger.error("Invalid end_time format '%s': %s. Retaining '%s'.", end_time, e, self._quiet_hours.end_time)
        
        if respect_focus_assist is not None:
            self._quiet_hours.respect_focus_assist = bool(respect_focus_assist)
        
        logger.info(
            "Quiet hours configured: enabled=%s, %s-%s, respect_focus_assist=%s",
            self._quiet_hours.enabled,
            self._quiet_hours.start_time,
            self._quiet_hours.end_time,
            self._quiet_hours.respect_focus_assist,
        )
    
    def is_quiet_hours(self) -> bool:
        """
        Check if currently in quiet hours.
        
        Handles midnight wrap correctly (e.g., 22:00-07:00).
        """
        if not self._quiet_hours.enabled:
            logger.debug("Quiet hours disabled")
            return False
        
        # Check Focus Assist
        if self._quiet_hours.respect_focus_assist and self._is_focus_assist_active():
            logger.debug("Focus Assist active, suppressing alarms via Focus Assist")
            return True
        
        # Scheduled quiet hours fallback logic
        in_quiet_range = self._is_time_in_range(
            self._quiet_hours.start_time,
            self._quiet_hours.end_time,
        )
        logger.debug("Scheduled quiet hours status: %s", in_quiet_range)
        return in_quiet_range
    
    def _is_time_in_range(self, start_time: str, end_time: str) -> bool:
        """
        Check if current time is within a range, handling midnight wrap.
        
        Args:
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM)
            
        Returns:
            True if current time is in range
        """
        try:
            now_dt = datetime.now()
            now = time(now_dt.hour, now_dt.minute, now_dt.second)
            
            start_parts = [int(p) for p in start_time.split(":")]
            end_parts = [int(p) for p in end_time.split(":")]
            
            start = time(start_parts[0], start_parts[1])
            end = time(end_parts[0], end_parts[1])
            
            if start <= end:
                # Same day range (e.g., 08:00-17:00)
                return start <= now <= end
            else:
                # Midnight wrap (e.g., 22:00-07:00)
                return now >= start or now <= end
        except (ValueError, IndexError, AttributeError) as e:
            logger.error("Error parsing quiet hours range (%s - %s): %s", start_time, end_time, e)
            return False
    
    def _is_focus_assist_active(self) -> bool:
        """Check if Windows Focus Assist is active."""
        if not self._focus_assist_available:
            return False
        
        try:
            import ctypes
            state = ctypes.c_int()
            res = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
            if res == 0:
                is_active = state.value in (2, 3, 4, 6)
                logger.debug("Focus Assist state retrieved: %d (active=%s)", state.value, is_active)
                return is_active
            return False
        except (AttributeError, OSError, Exception) as e:
            logger.debug("Focus Assist status query failed, falling back to schedule: %s", e)
            return False
    
    def update_quiet_hours_state(self, active: bool) -> None:
        """Update whether quiet hours are currently active."""
        if active != self._focus_assist_active:
            self._focus_assist_active = active
            logger.info("Quiet hours active state changed to: %s", active)
            if self._on_quiet_hours_change:
                try:
                    self._on_quiet_hours_change(active)
                except Exception as e:
                    logger.error("Quiet hours callback failed: %s", e)
    
    def set_on_quiet_hours_change(self, callback: Callable[[bool], None]) -> None:
        """Set callback for quiet hours state changes."""
        self._on_quiet_hours_change = callback
    
    def get_quiet_hours_config(self) -> QuietHoursConfig:
        """Get the current quiet hours configuration."""
        return self._quiet_hours
    
    def get_status(self) -> dict:
        """Get snooze manager status."""
        return {
            "snoozed": self.is_snoozed(),
            "snooze_remaining": self.get_snooze_remaining(),
            "snooze_duration_minutes": self._snooze_duration.value,
            "quiet_hours": {
                "enabled": self._quiet_hours.enabled,
                "start": self._quiet_hours.start_time,
                "end": self._quiet_hours.end_time,
                "active": self.is_quiet_hours(),
                "respect_focus_assist": self._quiet_hours.respect_focus_assist,
            },
            "focus_assist_available": self._focus_assist_available,
        }
    
    def __repr__(self) -> str:
        return f"<SnoozeManager snoozed={self.is_snoozed()}, quiet={self.is_quiet_hours()}>"