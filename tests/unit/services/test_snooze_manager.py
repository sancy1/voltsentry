"""
FILE: tests/unit/services/test_snooze_manager.py
PATH: voltsentry/tests/unit/services/test_snooze_manager.py
DESCRIPTION: Unit tests for SnoozeManager
PHASE: 3.4 - Snooze & Quiet Hours
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from voltsentry.core.exceptions import ValidationError
from voltsentry.services.snooze_manager import SnoozeDuration, SnoozeManager


class TestSnoozeManager:
    """Unit tests for SnoozeManager."""

    @pytest.fixture
    def snooze_manager(self):
        """Fixture providing a SnoozeManager instance with Focus Assist disabled for test isolation."""
        with patch.object(SnoozeManager, "_check_focus_assist_available", return_value=False):
            sm = SnoozeManager()
            yield sm

    def test_default_initialization(self, snooze_manager):
        """Test default snooze manager state."""
        assert not snooze_manager.is_snoozed()
        assert snooze_manager.get_snooze_remaining() is None
        config = snooze_manager.get_quiet_hours_config()
        assert not config.enabled
        assert config.start_time == "22:00"
        assert config.end_time == "07:00"

    def test_snooze_default_duration(self, snooze_manager):
        """Test snoozing with default duration (15 min)."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = now

            snooze_until = snooze_manager.snooze()

            assert snooze_until == datetime(2026, 1, 1, 12, 15, 0)
            assert snooze_manager.is_snoozed()
            assert snooze_manager.get_snooze_remaining() == 900

    def test_snooze_custom_duration(self, snooze_manager):
        """Test snoozing with explicit duration parameter."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = now

            snooze_until = snooze_manager.snooze(duration_minutes=5)

            assert snooze_until == datetime(2026, 1, 1, 12, 5, 0)
            assert snooze_manager.get_snooze_remaining() == 300

    def test_snooze_zero_or_negative_duration(self, snooze_manager):
        """Test snoozing with 0 or negative duration skips snooze."""
        snooze_manager.snooze(duration_minutes=0)
        assert not snooze_manager.is_snoozed()

        snooze_manager.snooze(duration_minutes=-5)
        assert not snooze_manager.is_snoozed()

    def test_clear_snooze(self, snooze_manager):
        """Test clearing active snooze."""
        snooze_manager.snooze(duration_minutes=10)
        assert snooze_manager.is_snoozed()

        snooze_manager.clear_snooze()
        assert not snooze_manager.is_snoozed()
        assert snooze_manager.get_snooze_remaining() is None

    def test_set_snooze_duration_enum(self, snooze_manager):
        """Test changing default snooze duration enum."""
        snooze_manager.set_snooze_duration(SnoozeDuration.THIRTY_MIN)

        now = datetime(2026, 1, 1, 12, 0, 0)
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = now
            snooze_until = snooze_manager.snooze()
            assert snooze_until == datetime(2026, 1, 1, 12, 30, 0)

    def test_quiet_hours_disabled_by_default(self, snooze_manager):
        """Test is_quiet_hours returns False when disabled."""
        assert not snooze_manager.is_quiet_hours()

    def test_quiet_hours_midnight_wrap_during_night(self, snooze_manager):
        """Test midnight wrap (22:00-07:00) during quiet hours (e.g., 23:00 and 02:00)."""
        snooze_manager.set_quiet_hours(
            enabled=True,
            start_time="22:00",
            end_time="07:00",
            respect_focus_assist=False,
        )

        # 23:00 - should be quiet hours
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, 23, 0, 0)
            assert snooze_manager.is_quiet_hours() is True

        # 02:00 - should be quiet hours
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 2, 2, 0, 0)
            assert snooze_manager.is_quiet_hours() is True

    def test_quiet_hours_midnight_wrap_during_day(self, snooze_manager):
        """Test midnight wrap (22:00-07:00) during daytime (e.g., 12:00)."""
        snooze_manager.set_quiet_hours(
            enabled=True,
            start_time="22:00",
            end_time="07:00",
            respect_focus_assist=False,
        )

        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
            assert snooze_manager.is_quiet_hours() is False

    def test_quiet_hours_same_day_range(self, snooze_manager):
        """Test same-day range (09:00-17:00)."""
        snooze_manager.set_quiet_hours(
            enabled=True,
            start_time="09:00",
            end_time="17:00",
            respect_focus_assist=False,
        )

        # 12:00 - inside quiet hours
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
            assert snooze_manager.is_quiet_hours() is True

        # 20:00 - outside quiet hours
        with patch("voltsentry.services.snooze_manager.datetime", wraps=datetime) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, 20, 0, 0)
            assert snooze_manager.is_quiet_hours() is False

    def test_invalid_time_format_retains_previous(self, snooze_manager):
        snooze_manager.set_quiet_hours(enabled=True, start_time="22:00", end_time="07:00")

        with pytest.raises(ValidationError):
            snooze_manager.set_quiet_hours(enabled=True, start_time="invalid_time")

        # Verify previous valid times were retained
        config = snooze_manager.get_quiet_hours_config()
        assert config.start_time == "22:00"

    def test_focus_assist_active_triggers_quiet_hours(self, snooze_manager):
        """Test active Focus Assist triggers quiet hours when enabled."""
        snooze_manager.set_quiet_hours(enabled=True, respect_focus_assist=True)

        with patch.object(snooze_manager, "_is_focus_assist_active", return_value=True):
            assert snooze_manager.is_quiet_hours() is True

    def test_quiet_hours_callback(self, snooze_manager):
        """Test callback triggered on quiet hours state change."""
        callback = MagicMock()
        snooze_manager.set_on_quiet_hours_change(callback)

        snooze_manager.update_quiet_hours_state(True)
        callback.assert_called_once_with(True)

        # Same state should not trigger callback again
        callback.reset_mock()
        snooze_manager.update_quiet_hours_state(True)
        callback.assert_not_called()