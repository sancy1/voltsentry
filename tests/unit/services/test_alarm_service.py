"""
FILE: tests/unit/services/test_alarm_service.py
PATH: voltsentry/tests/unit/services/test_alarm_service.py
DESCRIPTION: Unit tests for AlarmService orchestrator
PHASE: 3.5 - Alert Persistence & Weekly Report
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from voltsentry.core.types import BatteryReading
from voltsentry.services.alarm_manager import AlarmType
from voltsentry.services.alarm_service import AlarmService
from voltsentry.services.notification_manager import Notification
from voltsentry.services.threshold_state import ThresholdState


class TestAlarmService:
    """Unit tests for AlarmService orchestrator."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies and sub-managers used by AlarmService."""
        with patch("voltsentry.services.alarm_service.get_config") as mock_get_config, patch(
            "voltsentry.services.alarm_service.ThresholdStateMachine"
        ) as mock_tsm_cls, patch(
            "voltsentry.services.alarm_service.AlarmManager"
        ) as mock_am_cls, patch(
            "voltsentry.services.alarm_service.NotificationManager"
        ) as mock_nm_cls, patch(
            "voltsentry.services.alarm_service.SnoozeManager"
        ) as mock_sm_cls, patch(
            "voltsentry.services.alarm_service.AlarmEventRepository"
        ) as mock_repo_cls, patch(
            "voltsentry.services.alarm_service.AlarmEvent"
        ) as mock_alarm_event_cls:

            # Configure mock config settings
            mock_config = MagicMock()
            mock_config.settings.charge_threshold_high = 80
            mock_config.settings.charge_threshold_low = 20
            mock_config.settings.alarm_volume = 0.8
            mock_get_config.return_value = mock_config

            # Instantiate sub-manager mocks
            mock_tsm = MagicMock()
            mock_tsm.config = MagicMock()
            mock_tsm.config.high_threshold = 80
            mock_tsm.config.low_threshold = 20
            mock_tsm_cls.return_value = mock_tsm

            mock_am = MagicMock()
            mock_am.is_playing = False
            mock_am_cls.return_value = mock_am

            mock_nm = MagicMock()
            mock_nm_cls.return_value = mock_nm

            mock_sm = MagicMock()
            mock_sm.is_snoozed.return_value = False
            mock_sm.is_quiet_hours.return_value = False
            mock_sm_cls.return_value = mock_sm

            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            mock_alarm_event_cls.return_value = MagicMock()

            yield {
                "config": mock_config,
                "tsm": mock_tsm,
                "am": mock_am,
                "nm": mock_nm,
                "sm": mock_sm,
                "repo": mock_repo,
                "alarm_event": mock_alarm_event_cls,
            }

    @pytest.fixture
    def alarm_service(self, mock_dependencies):
        """Fixture providing an AlarmService instance with mocked dependencies."""
        return AlarmService()

    def test_initialization(self, alarm_service, mock_dependencies):
        """Test proper initialization and callback registrations."""
        assert alarm_service is not None
        mock_dependencies["am"].set_visual_only_callback.assert_called_once()
        mock_dependencies["nm"].set_fallback_callback.assert_called_once()

    def test_process_reading_updates_state_machine(self, alarm_service, mock_dependencies):
        """Test that processing a battery reading updates the state machine."""
        reading = BatteryReading(
            percent=85,
            is_charging=True,
            timestamp=datetime.now(timezone.utc),
            power_draw_watts=0.0,
            source="test",
        )

        alarm_service.process_reading(reading)

        mock_dependencies["tsm"].update.assert_called_once_with(85, True)
        assert alarm_service._last_percent == 85

    def test_process_reading_when_snoozed(self, alarm_service, mock_dependencies):
        """Test that active snooze bypasses processing new alarms."""
        mock_dependencies["sm"].is_snoozed.return_value = True
        reading = BatteryReading(
            percent=85,
            is_charging=True,
            timestamp=datetime.now(timezone.utc),
            power_draw_watts=0.0,
            source="test",
        )

        alarm_service.process_reading(reading)

        # State machine should not be called when snoozed
        mock_dependencies["am"].play.assert_not_called()

    def test_on_state_change_full_alarm(self, alarm_service, mock_dependencies):
        """Test triggering FULL_CHARGE alarm on transition to FULL_ALARM state."""
        alarm_service._on_state_change(ThresholdState.NORMAL, ThresholdState.FULL_ALARM)

        mock_dependencies["repo"].save.assert_called_once()
        mock_dependencies["am"].play.assert_called_once_with(AlarmType.FULL_CHARGE)
        mock_dependencies["nm"].notify.assert_called_once()

        notification_arg = mock_dependencies["nm"].notify.call_args[0][0]
        assert isinstance(notification_arg, Notification)
        assert notification_arg.title == "Battery Fully Charged"

    def test_on_state_change_low_alarm(self, alarm_service, mock_dependencies):
        """Test triggering LOW_BATTERY alarm on transition to LOW_ALARM state."""
        alarm_service._on_state_change(ThresholdState.NORMAL, ThresholdState.LOW_ALARM)

        mock_dependencies["repo"].save.assert_called_once()
        mock_dependencies["am"].play.assert_called_once_with(AlarmType.LOW_BATTERY)
        mock_dependencies["nm"].notify.assert_called_once()

    def test_on_state_change_critical_low(self, alarm_service, mock_dependencies):
        """Test triggering CRITICAL_LOW alarm on transition to CRITICAL_LOW state."""
        alarm_service._on_state_change(ThresholdState.LOW_ALARM, ThresholdState.CRITICAL_LOW)

        mock_dependencies["repo"].save.assert_called_once()
        mock_dependencies["am"].play.assert_called_once_with(AlarmType.CRITICAL_LOW)
        mock_dependencies["nm"].notify.assert_called_once()

    def test_on_state_change_normal_clears_alarm(self, alarm_service, mock_dependencies):
        """Test clearing alarm on transition back to NORMAL state."""
        mock_dependencies["am"].is_playing = True

        alarm_service._on_state_change(ThresholdState.FULL_ALARM, ThresholdState.NORMAL)

        mock_dependencies["am"].stop.assert_called_once()
        mock_dependencies["sm"].clear_snooze.assert_called_once()

    def test_quiet_hours_suppresses_alarm_playback(self, alarm_service, mock_dependencies):
        """Test quiet hours suppresses audio playback and notification during alarm trigger."""
        mock_dependencies["sm"].is_quiet_hours.return_value = True

        alarm_service._trigger_alarm(AlarmType.FULL_CHARGE)

        # Repository still records event
        mock_dependencies["repo"].save.assert_called_once()
        # Audio and Notification should be suppressed
        mock_dependencies["am"].play.assert_not_called()
        mock_dependencies["nm"].notify.assert_not_called()

    def test_repository_exception_handled_gracefully(self, alarm_service, mock_dependencies):
        """Test that database persistence failure does not crash alarm execution."""
        mock_dependencies["repo"].save.side_effect = Exception("DB Disk Full")

        # Should complete without raising an exception
        alarm_service._trigger_alarm(AlarmType.LOW_BATTERY)

        mock_dependencies["am"].play.assert_called_once_with(AlarmType.LOW_BATTERY)

    def test_snooze_alarm(self, alarm_service, mock_dependencies):
        """Test snooze action delegates to snooze_manager and stops audio."""
        alarm_service.snooze_alarm(duration_minutes=10)

        mock_dependencies["sm"].snooze.assert_called_once_with(10)
        mock_dependencies["am"].stop.assert_called_once()

    def test_stop_alarm(self, alarm_service, mock_dependencies):
        """Test stopping active alarm stops audio and clears snooze."""
        alarm_service.stop_alarm()

        mock_dependencies["am"].stop.assert_called_once()
        mock_dependencies["sm"].clear_snooze.assert_called_once()

    def test_update_thresholds(self, alarm_service, mock_dependencies):
        """Test updating state machine thresholds."""
        alarm_service.update_thresholds(high=85, low=15)

        if hasattr(alarm_service.state_machine, "update_thresholds"):
            mock_dependencies["tsm"].update_thresholds.assert_called_once_with(85, 15)
        else:
            assert alarm_service.state_machine.config.high_threshold == 85
            assert alarm_service.state_machine.config.low_threshold == 15

    def test_get_status(self, alarm_service, mock_dependencies):
        """Test get_status aggregates sub-component statuses."""
        mock_dependencies["tsm"].get_state_info.return_value = {"state": "normal"}
        mock_dependencies["am"].get_status.return_value = {"is_playing": False}
        mock_dependencies["nm"].get_status.return_value = {"native_available": True}
        mock_dependencies["sm"].get_status.return_value = {"snoozed": False}

        status = alarm_service.get_status()

        assert status["state"] == {"state": "normal"}
        assert status["alarm"] == {"is_playing": False}
        assert status["notification"] == {"native_available": True}
        assert status["snooze"] == {"snoozed": False}
        assert status["last_percent"] is None