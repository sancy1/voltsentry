"""Tests for AlarmService orchestration."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from voltsentry.core.types import BatteryReading
from voltsentry.services.alarm_manager import AlarmType
from voltsentry.services.alarm_service import AlarmService


@pytest.fixture
def mock_dependencies():
    """Patch all underlying managers and repositories created in AlarmService.__init__."""
    with patch("voltsentry.services.alarm_service.get_config") as mock_get_config, \
         patch("voltsentry.services.alarm_service.AlarmManager") as mock_alarm_mgr_cls, \
         patch("voltsentry.services.alarm_service.NotificationManager") as mock_notif_mgr_cls, \
         patch("voltsentry.services.alarm_service.SnoozeManager") as mock_snooze_mgr_cls, \
         patch("voltsentry.services.alarm_service.AlarmEventRepository") as mock_repo_cls:

        # Explicitly configure default settings mock values
        mock_settings = MagicMock()
        mock_settings.charge_threshold_high = 80
        mock_settings.charge_threshold_low = 20
        mock_settings.alarm_volume = 100
        mock_settings.custom_full_sound = None
        mock_settings.custom_low_sound = None
        mock_get_config.return_value.settings = mock_settings

        yield {
            "config": mock_get_config.return_value,
            "alarm_mgr": mock_alarm_mgr_cls.return_value,
            "notif_mgr": mock_notif_mgr_cls.return_value,
            "snooze_mgr": mock_snooze_mgr_cls.return_value,
            "repo": mock_repo_cls.return_value,
        }


@pytest.fixture
def alarm_service(mock_dependencies):
    """Instantiate AlarmService with mocked sub-components."""
    return AlarmService()


def test_initialization_thresholds(alarm_service, mock_dependencies):
    """Verify state machine initializes with values from app settings."""
    config = alarm_service.state_machine.config
    assert config.high_threshold == 80
    assert config.low_threshold == 20
    assert config.critical_threshold == 5


def test_process_reading_suppression_when_snoozed(alarm_service, mock_dependencies):
    """Verify that processing readings does not update state when snoozed."""
    mock_snooze = mock_dependencies["snooze_mgr"]
    mock_snooze.is_snoozed.return_value = True

    reading = BatteryReading(
        percent=95,
        is_charging=True,
        timestamp=datetime.now(),
        power_draw_watts=0.0,
        source="system",
    )

    with patch.object(alarm_service.state_machine, "update") as mock_update:
        alarm_service.process_reading(reading)
        mock_update.assert_not_called()


def test_trigger_alarm_full_charge(alarm_service, mock_dependencies):
    """Verify audio, desktop notification, and DB persistence when triggering FULL_CHARGE alarm."""
    mock_snooze = mock_dependencies["snooze_mgr"]
    mock_snooze.is_quiet_hours.return_value = False

    mock_tray = MagicMock()
    alarm_service.set_tray(mock_tray)
    alarm_service._last_percent = 85

    alarm_service._trigger_alarm(AlarmType.FULL_CHARGE)

    # 1. DB Save
    assert mock_dependencies["repo"].save.called
    saved_event = mock_dependencies["repo"].save.call_args[0][0]
    assert saved_event.alarm_type == "full_charge"

    # 2. Audio Playback
    mock_dependencies["alarm_mgr"].play.assert_called_once_with(
        AlarmType.FULL_CHARGE, custom_sound_path=None
    )

    # 3. Tray & Desktop Notification
    mock_tray.update_alarm.assert_called_once_with(True, alarm_type="full_charge")
    assert mock_dependencies["notif_mgr"].notify.called


def test_clear_alarm(alarm_service, mock_dependencies):
    """Verify that clearing an alarm stops playback and resets tray status."""
    mock_alarm_mgr = mock_dependencies["alarm_mgr"]
    mock_alarm_mgr.is_playing = True

    mock_tray = MagicMock()
    alarm_service.set_tray(mock_tray)

    alarm_service._clear_alarm()

    mock_alarm_mgr.stop.assert_called_once()
    mock_dependencies["snooze_mgr"].clear_snooze.assert_called_once()
    mock_tray.update_alarm.assert_called_once_with(False)


def test_update_thresholds(alarm_service, mock_dependencies):
    """Verify threshold updates apply to state machine, memory settings, and persist to disk."""
    alarm_service.update_thresholds(high=85, low=15)

    # Check state machine updated
    assert alarm_service.state_machine.config.high_threshold == 85
    assert alarm_service.state_machine.config.low_threshold == 15

    # Check config saved
    assert mock_dependencies["config"].settings.charge_threshold_high == 85
    assert mock_dependencies["config"].settings.charge_threshold_low == 15
    mock_dependencies["config"].save.assert_called_once()