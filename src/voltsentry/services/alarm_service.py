# """
# FILE: src/voltsentry/services/alarm_service.py
# PATH: voltsentry/src/voltsentry/services/alarm_service.py
# DESCRIPTION: Orchestrates all alarm components (threshold state, sound, notifications, tray UI)
# """

# from datetime import datetime, timezone
# from pathlib import Path
# from typing import Any, Optional

# from ..core.config import get_config
# from ..core.constants import HYSTERESIS_MARGIN
# from ..core.decorators import log_entry_exit
# from ..core.logging_config import get_logger, log_audit
# from ..core.types import BatteryReading
# from ..db.models import AlarmEvent
# from ..db.repositories import AlarmEventRepository
# from .alarm_manager import AlarmManager, AlarmType
# from .notification_manager import Notification, NotificationManager
# from .snooze_manager import SnoozeManager
# from .threshold_state import ThresholdConfig, ThresholdState, ThresholdStateMachine

# logger = get_logger(__name__)


# class AlarmService:
#     """
#     Central orchestration service for VoltSentry alerts.
#     Coordinates threshold transitions, audio alarms, desktop pop-ups,
#     and system tray icon animations.
#     """

#     def __init__(self):
#         self.config = get_config()
#         settings = self.config.settings

#         self.state_machine = ThresholdStateMachine(
#             config=ThresholdConfig(
#                 high_threshold=settings.charge_threshold_high,
#                 low_threshold=settings.charge_threshold_low,
#                 critical_threshold=15,
#                 hysteresis=HYSTERESIS_MARGIN,
#             ),
#             on_state_change=self._on_state_change,
#         )

#         self.alarm_manager = AlarmManager(volume=settings.alarm_volume)
#         self.notification_manager = NotificationManager()
#         self.snooze_manager = SnoozeManager()
#         self.repository = AlarmEventRepository()

#         # Connect fallbacks
#         self.alarm_manager.set_visual_only_callback(self._on_visual_only)
#         self.notification_manager.set_fallback_callback(
#             self._on_notification_fallback
#         )

#         self._last_state: Optional[ThresholdState] = None
#         self._last_percent: Optional[int] = None
#         self._was_snoozed: bool = False

#         # Reference to system tray icon for visual flashing & toast pop-ups
#         self._tray: Any = None

#         logger.info("AlarmService initialized")

#     def set_tray(self, tray: Any) -> None:
#         """Set system tray icon reference for notifications and visual flashing."""
#         self._tray = tray
#         logger.debug("Tray reference set in AlarmService")

#     @log_entry_exit()
#     def process_reading(self, reading: BatteryReading) -> None:
#         """Process battery reading through threshold state machine."""
#         try:
#             self._last_percent = reading.percent
#             currently_snoozed = self.snooze_manager.is_snoozed()
#             snooze_just_expired = self._was_snoozed and not currently_snoozed
#             self._was_snoozed = currently_snoozed

#             if snooze_just_expired:
#                 logger.info("Snooze period expired; re-evaluating state")

#             if currently_snoozed:
#                 logger.debug("Alarms suppressed due to active snooze")
#                 return

#             self.state_machine.update(reading.percent, reading.is_charging)
#         except Exception as e:
#             logger.error(
#                 "Error processing battery reading in AlarmService: %s",
#                 e,
#                 exc_info=True,
#             )

#     def _on_state_change(
#         self, old_state: ThresholdState, new_state: ThresholdState
#     ) -> None:
#         """Handle state transitions from state machine."""
#         self._last_state = new_state
#         logger.debug(
#             "Threshold state changed from %s to %s",
#             old_state.name,
#             new_state.name,
#         )

#         if new_state == ThresholdState.FULL_ALARM:
#             self._trigger_alarm(AlarmType.FULL_CHARGE)
#         elif new_state == ThresholdState.LOW_ALARM:
#             self._trigger_alarm(AlarmType.LOW_BATTERY)
#         elif new_state == ThresholdState.CRITICAL_LOW:
#             self._trigger_alarm(AlarmType.CRITICAL_LOW)
#         elif new_state == ThresholdState.NORMAL:
#             self._clear_alarm()

#     def _trigger_alarm(self, alarm_type: AlarmType) -> None:
#         """Trigger both audio sound and desktop notification."""
#         logger.info(
#             "🔔 Triggering alarm: %s (Battery at %s%%)",
#             alarm_type.value,
#             self._last_percent,
#         )

#         # Save to database (handle error gracefully)
#         self._save_alarm_event(alarm_type)

#         if self.snooze_manager.is_quiet_hours():
#             logger.info(
#                 "Alarm %s suppressed (quiet hours active)", alarm_type.value
#             )
#             return

#         settings = self.config.settings

#         # Resolve optional custom sound file
#         custom_sound_path: Optional[Path] = None
#         if alarm_type == AlarmType.FULL_CHARGE:
#             custom_sound = getattr(settings, "custom_full_sound", None)
#             if custom_sound:
#                 custom_sound_path = Path(custom_sound)
#         elif alarm_type in (AlarmType.LOW_BATTERY, AlarmType.CRITICAL_LOW):
#             custom_sound = getattr(settings, "custom_low_sound", None)
#             if custom_sound:
#                 custom_sound_path = Path(custom_sound)

#         # ===== 1. PLAY AUDIO ALARM =====
#         sound_played = False
#         try:
#             sound_played = self.alarm_manager.play(
#                 alarm_type, custom_sound_path=custom_sound_path
#             )
#             if sound_played:
#                 logger.info("🔊 Alarm sound playing for: %s", alarm_type.value)
#             else:
#                 logger.warning(
#                     "⚠️ Alarm sound failed, visual only for: %s",
#                     alarm_type.value,
#                 )
#         except Exception as e:
#             logger.error("Failed to play alarm audio: %s", e, exc_info=True)

#         # ===== 2. TRIGGER SYSTEM TRAY & NOTIFICATIONS =====
#         try:
#             # Update Tray state to flash icon and show notification
#             if self._tray:
#                 self._tray.update_alarm(True, alarm_type=alarm_type.value)

#             # Send system desktop notification
#             notification = self._create_notification(alarm_type)
#             self.notification_manager.notify(notification)
#             logger.info("🔔 Notification posted for: %s", alarm_type.value)

#         except Exception as e:
#             logger.error(
#                 "Failed to post desktop notification: %s", e, exc_info=True
#             )

#         log_audit("INFO", f"Alarm triggered: {alarm_type.value}")

#     def _clear_alarm(self) -> None:
#         """Clear active alarm state and reset visual components."""
#         if self.alarm_manager.is_playing:
#             self.alarm_manager.stop()
#             self.snooze_manager.clear_snooze()

#         if self._tray:
#             self._tray.update_alarm(False)

#         logger.info("Alarm cleared")

#     def _create_notification(self, alarm_type: AlarmType) -> Notification:
#         """Construct notification object based on alarm type."""
#         if alarm_type == AlarmType.FULL_CHARGE:
#             return Notification(
#                 title="🔋 Battery Fully Charged",
#                 message="Your battery has reached the target charge level. Unplug to extend battery life.",
#                 duration=5,
#             )
#         elif alarm_type == AlarmType.LOW_BATTERY:
#             return Notification(
#                 title="⚠️ Battery Low",
#                 message="Your battery is below the recommended level. Plug in to charge.",
#                 duration=5,
#             )
#         elif alarm_type == AlarmType.CRITICAL_LOW:
#             return Notification(
#                 title="🔴 Battery Critical!",
#                 message="Battery level is critically low. Plug in immediately to avoid shutdown.",
#                 duration=10,
#             )
#         else:
#             return Notification(
#                 title="Battery Alert",
#                 message="Battery needs attention.",
#                 duration=5,
#             )

#     def _save_alarm_event(self, alarm_type: AlarmType) -> None:
#         """Persist alarm event to database."""
#         try:
#             # Only pass fields that exist in AlarmEvent model
#             # AlarmEvent has: id, timestamp, alarm_type, acknowledged_at, snoozed, snooze_until
#             event_kwargs = {
#                 "timestamp": datetime.now(timezone.utc),
#                 "alarm_type": alarm_type.value,
#                 "snoozed": False,
#             }
#             # Note: alarm_type is a string field, not an enum
#             event = AlarmEvent(**event_kwargs)
#             self.repository.save(event)
#             logger.debug(
#                 "Alarm event saved to database: %s", alarm_type.value
#             )
#         except Exception as e:
#             logger.error(
#                 "Failed to save alarm event to database: %s", e, exc_info=True
#             )

#     def _on_visual_only(self, alarm_type: AlarmType) -> None:
#         """Fallback callback when audio playback fails entirely."""
#         logger.warning(
#             "Audio playback unavailable. Triggering visual-only fallback for: %s",
#             alarm_type.value,
#         )
#         try:
#             fallback_notification = Notification(
#                 title=f"Alert: {alarm_type.value.replace('_', ' ').title()}",
#                 message="Audio alert failed to play. Please check your battery status.",
#                 duration=7,
#             )
#             self.notification_manager.notify(fallback_notification)

#             if self._tray:
#                 self._tray.show_notification(
#                     fallback_notification.title,
#                     fallback_notification.message,
#                     urgency="critical",
#                 )
#         except Exception as e:
#             logger.error("Visual fallback notification failed: %s", e)

#     def _on_notification_fallback(self, notification: Notification) -> None:
#         """Callback when desktop notification system fails."""
#         logger.warning(
#             "OS Notification system failed. Fallback triggered: %s - %s",
#             notification.title,
#             notification.message,
#         )

#     def snooze_alarm(self, duration_minutes: Optional[int] = None) -> None:
#         """Snooze active alarm."""
#         self.snooze_manager.snooze(duration_minutes)
#         self.alarm_manager.stop()
#         if self._tray:
#             self._tray.update_alarm(False)
#         self._was_snoozed = True
#         logger.info("Alarm snoozed manually")

#     def stop_alarm(self) -> None:
#         """Stop active alarm manually."""
#         self.alarm_manager.stop()
#         self.snooze_manager.clear_snooze()
#         if self._tray:
#             self._tray.update_alarm(False)
#         self._was_snoozed = False
#         logger.info("Alarm stopped manually")

#     def update_thresholds(self, high: int, low: int) -> None:
#         """Update charge threshold limits."""
#         if hasattr(self.state_machine, "update_thresholds"):
#             self.state_machine.update_thresholds(high, low)
#         else:
#             self.state_machine.config.high_threshold = high
#             self.state_machine.config.low_threshold = low
#         logger.info("Thresholds updated: high=%d%%, low=%d%%", high, low)

#     def get_status(self) -> dict:
#         """Get current status of alarm service components."""
#         return {
#             "state": self.state_machine.get_state_info(),
#             "alarm": self.alarm_manager.get_status(),
#             "notification": self.notification_manager.get_status(),
#             "snooze": self.snooze_manager.get_status(),
#             "last_percent": self._last_percent,
#         }

#     def __repr__(self) -> str:
#         return f"<AlarmService state={self._last_state}, last_percent={self._last_percent}%>"










































# """
# FILE: src/voltsentry/services/alarm_service.py
# PATH: voltsentry/src/voltsentry/services/alarm_service.py
# DESCRIPTION: Orchestrates all alarm components (threshold state, sound, notifications, tray UI)
# """

# from datetime import datetime, timezone
# from pathlib import Path
# from typing import Any, Optional

# from ..core.config import get_config
# from ..core.constants import HYSTERESIS_MARGIN
# from ..core.decorators import log_entry_exit
# from ..core.logging_config import get_logger, log_audit
# from ..core.types import BatteryReading
# from ..db.models import AlarmEvent
# from ..db.repositories import AlarmEventRepository
# from .alarm_manager import AlarmManager, AlarmType
# from .notification_manager import Notification, NotificationManager
# from .snooze_manager import SnoozeManager
# from .threshold_state import ThresholdConfig, ThresholdState, ThresholdStateMachine

# logger = get_logger(__name__)


# class AlarmService:
#     """
#     Central orchestration service for VoltSentry alerts.
#     Coordinates threshold transitions, audio alarms, desktop pop-ups,
#     and system tray icon animations.
#     """

#     def __init__(self):
#         self.config = get_config()
#         settings = self.config.settings

#         # ✅ READ FROM SETTINGS - NOT HARDCODED!
#         logger.info(
#             "🔧 AlarmService: Loading thresholds from settings: high=%d%%, low=%d%%",
#             settings.charge_threshold_high,
#             settings.charge_threshold_low,
#         )

#         self.state_machine = ThresholdStateMachine(
#             config=ThresholdConfig(
#                 high_threshold=settings.charge_threshold_high,  # ✅ From settings
#                 low_threshold=settings.charge_threshold_low,    # ✅ From settings
#                 critical_threshold=5,  # ✅ Fixed safety critical (5%)
#                 hysteresis=HYSTERESIS_MARGIN,
#             ),
#             on_state_change=self._on_state_change,
#         )

#         self.alarm_manager = AlarmManager(volume=settings.alarm_volume)
#         self.notification_manager = NotificationManager()
#         self.snooze_manager = SnoozeManager()
#         self.repository = AlarmEventRepository()

#         # Connect fallbacks
#         self.alarm_manager.set_visual_only_callback(self._on_visual_only)
#         self.notification_manager.set_fallback_callback(
#             self._on_notification_fallback
#         )

#         self._last_state: Optional[ThresholdState] = None
#         self._last_percent: Optional[int] = None
#         self._was_snoozed: bool = False

#         # Reference to system tray icon for visual flashing & toast pop-ups
#         self._tray: Any = None

#         logger.info(
#             "✅ AlarmService initialized with thresholds: high=%d%%, low=%d%%, critical=5%%",
#             settings.charge_threshold_high,
#             settings.charge_threshold_low,
#         )

#     def set_tray(self, tray: Any) -> None:
#         """Set system tray icon reference for notifications and visual flashing."""
#         self._tray = tray
#         logger.debug("Tray reference set in AlarmService")

#     @log_entry_exit()
#     def process_reading(self, reading: BatteryReading) -> None:
#         """Process battery reading through threshold state machine."""
#         try:
#             self._last_percent = reading.percent
#             currently_snoozed = self.snooze_manager.is_snoozed()
#             snooze_just_expired = self._was_snoozed and not currently_snoozed
#             self._was_snoozed = currently_snoozed

#             if snooze_just_expired:
#                 logger.info("Snooze period expired; re-evaluating state")

#             if currently_snoozed:
#                 logger.debug("Alarms suppressed due to active snooze")
#                 return

#             self.state_machine.update(reading.percent, reading.is_charging)
#         except Exception as e:
#             logger.error(
#                 "Error processing battery reading in AlarmService: %s",
#                 e,
#                 exc_info=True,
#             )

#     def _on_state_change(
#         self, old_state: ThresholdState, new_state: ThresholdState
#     ) -> None:
#         """Handle state transitions from state machine."""
#         self._last_state = new_state
#         logger.debug(
#             "Threshold state changed from %s to %s",
#             old_state.name,
#             new_state.name,
#         )

#         if new_state == ThresholdState.FULL_ALARM:
#             self._trigger_alarm(AlarmType.FULL_CHARGE)
#         elif new_state == ThresholdState.LOW_ALARM:
#             self._trigger_alarm(AlarmType.LOW_BATTERY)
#         elif new_state == ThresholdState.CRITICAL_LOW:
#             self._trigger_alarm(AlarmType.CRITICAL_LOW)
#         elif new_state == ThresholdState.NORMAL:
#             self._clear_alarm()

#     def _trigger_alarm(self, alarm_type: AlarmType) -> None:
#         """Trigger both audio sound and desktop notification."""
#         logger.info(
#             "🔔 Triggering alarm: %s (Battery at %s%%)",
#             alarm_type.value,
#             self._last_percent,
#         )

#         # Save to database (handle error gracefully)
#         self._save_alarm_event(alarm_type)

#         if self.snooze_manager.is_quiet_hours():
#             logger.info(
#                 "Alarm %s suppressed (quiet hours active)", alarm_type.value
#             )
#             return

#         settings = self.config.settings

#         # Resolve optional custom sound file
#         custom_sound_path: Optional[Path] = None
#         if alarm_type == AlarmType.FULL_CHARGE:
#             custom_sound = getattr(settings, "custom_full_sound", None)
#             if custom_sound:
#                 custom_sound_path = Path(custom_sound)
#         elif alarm_type in (AlarmType.LOW_BATTERY, AlarmType.CRITICAL_LOW):
#             custom_sound = getattr(settings, "custom_low_sound", None)
#             if custom_sound:
#                 custom_sound_path = Path(custom_sound)

#         # ===== 1. PLAY AUDIO ALARM =====
#         sound_played = False
#         try:
#             sound_played = self.alarm_manager.play(
#                 alarm_type, custom_sound_path=custom_sound_path
#             )
#             if sound_played:
#                 logger.info("🔊 Alarm sound playing for: %s", alarm_type.value)
#             else:
#                 logger.warning(
#                     "⚠️ Alarm sound failed, visual only for: %s",
#                     alarm_type.value,
#                 )
#         except Exception as e:
#             logger.error("Failed to play alarm audio: %s", e, exc_info=True)

#         # ===== 2. TRIGGER SYSTEM TRAY & NOTIFICATIONS =====
#         try:
#             # Update Tray state to flash icon and show notification
#             if self._tray:
#                 self._tray.update_alarm(True, alarm_type=alarm_type.value)

#             # Send system desktop notification
#             notification = self._create_notification(alarm_type)
#             self.notification_manager.notify(notification)
#             logger.info("🔔 Notification posted for: %s", alarm_type.value)

#         except Exception as e:
#             logger.error(
#                 "Failed to post desktop notification: %s", e, exc_info=True
#             )

#         log_audit("INFO", f"Alarm triggered: {alarm_type.value}")

#     def _clear_alarm(self) -> None:
#         """Clear active alarm state and reset visual components."""
#         if self.alarm_manager.is_playing:
#             self.alarm_manager.stop()
#             self.snooze_manager.clear_snooze()

#         if self._tray:
#             self._tray.update_alarm(False)

#         logger.info("Alarm cleared")

#     def _create_notification(self, alarm_type: AlarmType) -> Notification:
#         """Construct notification object based on alarm type."""
#         if alarm_type == AlarmType.FULL_CHARGE:
#             return Notification(
#                 title="🔋 Battery Fully Charged",
#                 message="Your battery has reached the target charge level. Unplug to extend battery life.",
#                 duration=5,
#             )
#         elif alarm_type == AlarmType.LOW_BATTERY:
#             return Notification(
#                 title="⚠️ Battery Low",
#                 message="Your battery is below the recommended level. Plug in to charge.",
#                 duration=5,
#             )
#         elif alarm_type == AlarmType.CRITICAL_LOW:
#             return Notification(
#                 title="🔴 Battery Critical!",
#                 message="Battery level is critically low. Plug in immediately to avoid shutdown.",
#                 duration=10,
#             )
#         else:
#             return Notification(
#                 title="Battery Alert",
#                 message="Battery needs attention.",
#                 duration=5,
#             )

#     def _save_alarm_event(self, alarm_type: AlarmType) -> None:
#         """Persist alarm event to database."""
#         try:
#             # Only pass fields that exist in AlarmEvent model
#             # AlarmEvent has: id, timestamp, alarm_type, acknowledged_at, snoozed, snooze_until
#             event_kwargs = {
#                 "timestamp": datetime.now(timezone.utc),
#                 "alarm_type": alarm_type.value,
#                 "snoozed": False,
#             }
#             # Note: alarm_type is a string field, not an enum
#             event = AlarmEvent(**event_kwargs)
#             self.repository.save(event)
#             logger.debug(
#                 "Alarm event saved to database: %s", alarm_type.value
#             )
#         except Exception as e:
#             logger.error(
#                 "Failed to save alarm event to database: %s", e, exc_info=True
#             )

#     def _on_visual_only(self, alarm_type: AlarmType) -> None:
#         """Fallback callback when audio playback fails entirely."""
#         logger.warning(
#             "Audio playback unavailable. Triggering visual-only fallback for: %s",
#             alarm_type.value,
#         )
#         try:
#             fallback_notification = Notification(
#                 title=f"Alert: {alarm_type.value.replace('_', ' ').title()}",
#                 message="Audio alert failed to play. Please check your battery status.",
#                 duration=7,
#             )
#             self.notification_manager.notify(fallback_notification)

#             if self._tray:
#                 self._tray.show_notification(
#                     fallback_notification.title,
#                     fallback_notification.message,
#                     urgency="critical",
#                 )
#         except Exception as e:
#             logger.error("Visual fallback notification failed: %s", e)

#     def _on_notification_fallback(self, notification: Notification) -> None:
#         """Callback when desktop notification system fails."""
#         logger.warning(
#             "OS Notification system failed. Fallback triggered: %s - %s",
#             notification.title,
#             notification.message,
#         )

#     def snooze_alarm(self, duration_minutes: Optional[int] = None) -> None:
#         """Snooze active alarm."""
#         self.snooze_manager.snooze(duration_minutes)
#         self.alarm_manager.stop()
#         if self._tray:
#             self._tray.update_alarm(False)
#         self._was_snoozed = True
#         logger.info("Alarm snoozed manually")

#     def stop_alarm(self) -> None:
#         """Stop active alarm manually."""
#         self.alarm_manager.stop()
#         self.snooze_manager.clear_snooze()
#         if self._tray:
#             self._tray.update_alarm(False)
#         self._was_snoozed = False
#         logger.info("Alarm stopped manually")

#     def update_thresholds(self, high: int, low: int) -> None:
#         """
#         Update charge threshold limits.
        
#         Args:
#             high: New high threshold (stop charging %)
#             low: New low threshold (start charging %)
#         """
#         # Update the state machine config
#         self.state_machine.config.high_threshold = high
#         self.state_machine.config.low_threshold = low
        
#         # Also update the config in memory
#         settings = self.config.settings
#         settings.charge_threshold_high = high
#         settings.charge_threshold_low = low
        
#         # Save to disk
#         self.config.save()
        
#         logger.info(
#             "✅ Thresholds updated: high=%d%%, low=%d%%",
#             high,
#             low,
#         )
#         log_audit("INFO", f"Thresholds updated: high={high}%, low={low}%")

#     def get_status(self) -> dict:
#         """Get current status of alarm service components."""
#         return {
#             "state": self.state_machine.get_state_info(),
#             "alarm": self.alarm_manager.get_status(),
#             "notification": self.notification_manager.get_status(),
#             "snooze": self.snooze_manager.get_status(),
#             "last_percent": self._last_percent,
#         }

#     def __repr__(self) -> str:
#         return f"<AlarmService state={self._last_state}, last_percent={self._last_percent}%>"




































































"""
FILE: src/voltsentry/services/alarm_service.py
PATH: voltsentry/src/voltsentry/services/alarm_service.py
DESCRIPTION: Orchestrates all alarm components (threshold state, sound, notifications, tray UI)
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from ..core.constants import HYSTERESIS_MARGIN
from ..core.decorators import log_entry_exit
from ..core.logging_config import get_logger, log_audit
from ..core.types import BatteryReading
from ..db.models import AlarmEvent
from ..db.repositories import AlarmEventRepository
from .alarm_manager import AlarmManager, AlarmType
from .notification_manager import Notification, NotificationManager
from .snooze_manager import SnoozeManager
from .threshold_state import ThresholdConfig, ThresholdState, ThresholdStateMachine

logger = get_logger(__name__)


class AlarmService:
    """
    Central orchestration service for VoltSentry alerts.
    Coordinates threshold transitions, audio alarms, desktop pop-ups,
    and system tray icon animations.
    """

    def __init__(self):
        self.config = get_config()
        settings = self.config.settings

        # ✅ READ FROM SETTINGS - NOT HARDCODED!
        logger.info(
            "🔧 AlarmService: Loading thresholds from settings: high=%d%%, low=%d%%",
            settings.charge_threshold_high,
            settings.charge_threshold_low,
        )

        self.state_machine = ThresholdStateMachine(
            config=ThresholdConfig(
                high_threshold=settings.charge_threshold_high,  # ✅ From settings
                low_threshold=settings.charge_threshold_low,    # ✅ From settings
                critical_threshold=5,  # ✅ Fixed safety critical (5%)
                hysteresis=HYSTERESIS_MARGIN,
            ),
            on_state_change=self._on_state_change,
        )

        self.alarm_manager = AlarmManager(volume=settings.alarm_volume)
        self.notification_manager = NotificationManager()
        self.snooze_manager = SnoozeManager()
        self.repository = AlarmEventRepository()

        # Connect fallbacks
        self.alarm_manager.set_visual_only_callback(self._on_visual_only)
        self.notification_manager.set_fallback_callback(
            self._on_notification_fallback
        )

        self._last_state: Optional[ThresholdState] = None
        self._last_percent: Optional[int] = None
        self._was_snoozed: bool = False
        self._last_charging: Optional[bool] = None  # Track charger state

        # Reference to system tray icon for visual flashing & toast pop-ups
        self._tray: Any = None

        logger.info(
            "✅ AlarmService initialized with thresholds: high=%d%%, low=%d%%, critical=5%%",
            settings.charge_threshold_high,
            settings.charge_threshold_low,
        )

    def set_tray(self, tray: Any) -> None:
        """Set system tray icon reference for notifications and visual flashing."""
        self._tray = tray
        logger.debug("Tray reference set in AlarmService")

    # ============================================================
    # ✅ STATE RESET METHODS
    # ============================================================

    def reset_alarm_state(self, reason: str = "Manual reset") -> None:
        """
        Reset all alarm state flags to allow fresh evaluation.
        
        This is called when:
        - Charger is plugged/unplugged (automatic)
        - User clicks Refresh button
        - User clicks Reset State button
        
        Args:
            reason: Why the reset was triggered (for logging)
        """
        logger.info("🔄 Resetting alarm state: %s", reason)
        
        # Clear snooze state
        self._was_snoozed = False
        self.snooze_manager.clear_snooze()
        
        # Stop any playing alarm
        if self.alarm_manager.is_playing:
            self.alarm_manager.stop()
        
        # Reset state machine to force re-evaluation
        # The state machine will re-evaluate on next reading
        
        # Clear tray alarm state
        if self._tray:
            self._tray.update_alarm(False)
            self._tray._stop_repeating_notification()
        
        log_audit("INFO", f"Alarm state reset: {reason}")
        logger.info("✅ Alarm state reset complete")

    def _check_charger_state_transition(self, reading: BatteryReading) -> bool:
        """
        Check if charger state changed.
        
        Returns:
            True if charger state changed, False otherwise
        """
        if self._last_charging is None:
            self._last_charging = reading.is_charging
            return False
        
        if self._last_charging != reading.is_charging:
            old_state = "plugged" if self._last_charging else "unplugged"
            new_state = "plugged" if reading.is_charging else "unplugged"
            logger.info("🔌 Charger state changed: %s → %s", old_state, new_state)
            self._last_charging = reading.is_charging
            return True
        
        self._last_charging = reading.is_charging
        return False

    @log_entry_exit()
    def process_reading(self, reading: BatteryReading) -> None:
        """Process battery reading through threshold state machine."""
        try:
            self._last_percent = reading.percent
            
            # ✅ Check for charger state transition
            if self._check_charger_state_transition(reading):
                # Charger was plugged or unplugged - reset alarm state
                self.reset_alarm_state(
                    reason=f"Charger state changed to {'plugged' if reading.is_charging else 'unplugged'}"
                )
            
            currently_snoozed = self.snooze_manager.is_snoozed()
            snooze_just_expired = self._was_snoozed and not currently_snoozed
            self._was_snoozed = currently_snoozed

            if snooze_just_expired:
                logger.info("Snooze period expired; re-evaluating state")

            if currently_snoozed:
                logger.debug("Alarms suppressed due to active snooze")
                return

            self.state_machine.update(reading.percent, reading.is_charging)
        except Exception as e:
            logger.error(
                "Error processing battery reading in AlarmService: %s",
                e,
                exc_info=True,
            )

    def _on_state_change(
        self, old_state: ThresholdState, new_state: ThresholdState
    ) -> None:
        """Handle state transitions from state machine."""
        self._last_state = new_state
        logger.debug(
            "Threshold state changed from %s to %s",
            old_state.name,
            new_state.name,
        )

        if new_state == ThresholdState.FULL_ALARM:
            self._trigger_alarm(AlarmType.FULL_CHARGE)
        elif new_state == ThresholdState.LOW_ALARM:
            self._trigger_alarm(AlarmType.LOW_BATTERY)
        elif new_state == ThresholdState.CRITICAL_LOW:
            self._trigger_alarm(AlarmType.CRITICAL_LOW)
        elif new_state == ThresholdState.NORMAL:
            self._clear_alarm()

    def _trigger_alarm(self, alarm_type: AlarmType) -> None:
        """Trigger both audio sound and desktop notification."""
        logger.info(
            "🔔 Triggering alarm: %s (Battery at %s%%)",
            alarm_type.value,
            self._last_percent,
        )

        # Save to database (handle error gracefully)
        self._save_alarm_event(alarm_type)

        if self.snooze_manager.is_quiet_hours():
            logger.info(
                "Alarm %s suppressed (quiet hours active)", alarm_type.value
            )
            return

        settings = self.config.settings

        # Resolve optional custom sound file
        custom_sound_path: Optional[Path] = None
        if alarm_type == AlarmType.FULL_CHARGE:
            custom_sound = getattr(settings, "custom_full_sound", None)
            if custom_sound:
                custom_sound_path = Path(custom_sound)
        elif alarm_type in (AlarmType.LOW_BATTERY, AlarmType.CRITICAL_LOW):
            custom_sound = getattr(settings, "custom_low_sound", None)
            if custom_sound:
                custom_sound_path = Path(custom_sound)

        # ===== 1. PLAY AUDIO ALARM =====
        sound_played = False
        try:
            sound_played = self.alarm_manager.play(
                alarm_type, custom_sound_path=custom_sound_path
            )
            if sound_played:
                logger.info("🔊 Alarm sound playing for: %s", alarm_type.value)
            else:
                logger.warning(
                    "⚠️ Alarm sound failed, visual only for: %s",
                    alarm_type.value,
                )
        except Exception as e:
            logger.error("Failed to play alarm audio: %s", e, exc_info=True)

        # ===== 2. TRIGGER SYSTEM TRAY & NOTIFICATIONS =====
        try:
            # Update Tray state to flash icon and show notification
            if self._tray:
                self._tray.update_alarm(True, alarm_type=alarm_type.value)

            # Send system desktop notification
            notification = self._create_notification(alarm_type)
            self.notification_manager.notify(notification)
            logger.info("🔔 Notification posted for: %s", alarm_type.value)

        except Exception as e:
            logger.error(
                "Failed to post desktop notification: %s", e, exc_info=True
            )

        log_audit("INFO", f"Alarm triggered: {alarm_type.value}")

    def _clear_alarm(self) -> None:
        """Clear active alarm state and reset visual components."""
        if self.alarm_manager.is_playing:
            self.alarm_manager.stop()
            self.snooze_manager.clear_snooze()

        if self._tray:
            self._tray.update_alarm(False)

        logger.info("Alarm cleared")

    def _create_notification(self, alarm_type: AlarmType) -> Notification:
        """Construct notification object based on alarm type."""
        if alarm_type == AlarmType.FULL_CHARGE:
            return Notification(
                title="🔋 Battery Fully Charged",
                message="Your battery has reached the target charge level. Unplug to extend battery life.",
                duration=5,
            )
        elif alarm_type == AlarmType.LOW_BATTERY:
            return Notification(
                title="⚠️ Battery Low",
                message="Your battery is below the recommended level. Plug in to charge.",
                duration=5,
            )
        elif alarm_type == AlarmType.CRITICAL_LOW:
            return Notification(
                title="🔴 Battery Critical!",
                message="Battery level is critically low. Plug in immediately to avoid shutdown.",
                duration=10,
            )
        else:
            return Notification(
                title="Battery Alert",
                message="Battery needs attention.",
                duration=5,
            )

    def _save_alarm_event(self, alarm_type: AlarmType) -> None:
        """Persist alarm event to database."""
        try:
            # Only pass fields that exist in AlarmEvent model
            # AlarmEvent has: id, timestamp, alarm_type, acknowledged_at, snoozed, snooze_until
            event_kwargs = {
                "timestamp": datetime.now(timezone.utc),
                "alarm_type": alarm_type.value,
                "snoozed": False,
            }
            # Note: alarm_type is a string field, not an enum
            event = AlarmEvent(**event_kwargs)
            self.repository.save(event)
            logger.debug(
                "Alarm event saved to database: %s", alarm_type.value
            )
        except Exception as e:
            logger.error(
                "Failed to save alarm event to database: %s", e, exc_info=True
            )

    def _on_visual_only(self, alarm_type: AlarmType) -> None:
        """Fallback callback when audio playback fails entirely."""
        logger.warning(
            "Audio playback unavailable. Triggering visual-only fallback for: %s",
            alarm_type.value,
        )
        try:
            fallback_notification = Notification(
                title=f"Alert: {alarm_type.value.replace('_', ' ').title()}",
                message="Audio alert failed to play. Please check your battery status.",
                duration=7,
            )
            self.notification_manager.notify(fallback_notification)

            if self._tray:
                self._tray.show_notification(
                    fallback_notification.title,
                    fallback_notification.message,
                    urgency="critical",
                )
        except Exception as e:
            logger.error("Visual fallback notification failed: %s", e)

    def _on_notification_fallback(self, notification: Notification) -> None:
        """Callback when desktop notification system fails."""
        logger.warning(
            "OS Notification system failed. Fallback triggered: %s - %s",
            notification.title,
            notification.message,
        )

    def snooze_alarm(self, duration_minutes: Optional[int] = None) -> None:
        """Snooze active alarm."""
        self.snooze_manager.snooze(duration_minutes)
        self.alarm_manager.stop()
        if self._tray:
            self._tray.update_alarm(False)
        self._was_snoozed = True
        logger.info("Alarm snoozed manually")

    def stop_alarm(self) -> None:
        """Stop active alarm manually."""
        self.alarm_manager.stop()
        self.snooze_manager.clear_snooze()
        if self._tray:
            self._tray.update_alarm(False)
        self._was_snoozed = False
        logger.info("Alarm stopped manually")

    def update_thresholds(self, high: int, low: int) -> None:
        """
        Update charge threshold limits.
        
        Args:
            high: New high threshold (stop charging %)
            low: New low threshold (start charging %)
        """
        # Update the state machine config
        self.state_machine.update_config(
            high_threshold=high,
            low_threshold=low,
        )
        
        # Also update the config in memory
        settings = self.config.settings
        settings.charge_threshold_high = high
        settings.charge_threshold_low = low
        
        # Save to disk
        self.config.save()
        
        logger.info(
            "✅ Thresholds updated: high=%d%%, low=%d%%",
            high,
            low,
        )
        log_audit("INFO", f"Thresholds updated: high={high}%, low={low}%")

    def get_status(self) -> dict:
        """Get current status of alarm service components."""
        return {
            "state": self.state_machine.get_state_info(),
            "alarm": self.alarm_manager.get_status(),
            "notification": self.notification_manager.get_status(),
            "snooze": self.snooze_manager.get_status(),
            "last_percent": self._last_percent,
        }

    def __repr__(self) -> str:
        return f"<AlarmService state={self._last_state}, last_percent={self._last_percent}%>"
    
    