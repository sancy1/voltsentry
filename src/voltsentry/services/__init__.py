"""
FILE: src/voltsentry/services/__init__.py
PATH: voltsentry/src/voltsentry/services/__init__.py
DESCRIPTION: Services module exports
PHASE: 5 - All services exported
"""

"""Services layer - business logic for VoltSentry."""

from .alarm_manager import AlarmManager
from .alarm_service import AlarmService
from .automation_hooks import AutomationHookManager, ScriptHook, WebhookHook
from .backup_restore import BackupRestoreService
from .base_service import BaseService
from .battery_poller import BatteryPoller
from .battery_report import BatteryReportService
from .calibration import CalibrationService, CalibrationState
from .heartbeat import HeartbeatService, get_heartbeat_service
from .notification_manager import NotificationManager
from .power_draw import PowerDrawMonitor, get_power_draw_monitor
from .snooze_manager import SnoozeManager
from .threshold_state import ThresholdConfig, ThresholdState, ThresholdStateMachine
from .watchdog import WatchdogService
from .weekly_report import WeeklyReportService

__all__ = [
    # Phase 2
    "BatteryPoller",
    "BatteryReportService",
    "BaseService",
    "PowerDrawMonitor",
    "get_power_draw_monitor",
    "HeartbeatService",
    "get_heartbeat_service",
    # Phase 3
    "AlarmManager",
    "NotificationManager",
    "SnoozeManager",
    "ThresholdStateMachine",
    "ThresholdState",
    "ThresholdConfig",
    "AlarmService",
    "WeeklyReportService",
    # Phase 5
    "WatchdogService",
    "CalibrationService",
    "CalibrationState",
    "WebhookHook",
    "ScriptHook",
    "AutomationHookManager",
    "BackupRestoreService",
]