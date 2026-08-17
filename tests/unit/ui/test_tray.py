"""
FILE: tests/unit/ui/test_tray.py
PATH: voltsentry/tests/unit/ui/test_tray.py
DESCRIPTION: Unit tests for TrayIcon
PHASE: 4 - Testing
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from voltsentry.ui.tray import TrayIcon


@pytest.fixture(scope="session")
def app():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestTrayIcon:
    """Test suite for TrayIcon."""

    def test_creation(self, app):
        """Test tray icon creation."""
        tray = TrayIcon()
        assert tray is not None
        assert tray._current_percent == 0
        assert tray._is_charging is False

    def test_update_battery(self, app):
        """Test battery update."""
        tray = TrayIcon()
        tray.update_battery(75, True)

        assert tray._current_percent == 75
        assert tray._is_charging is True

    def test_update_alarm(self, app):
        """Test alarm update."""
        tray = TrayIcon()
        tray.update_alarm(True, "full_charge")

        assert tray._alarm_active is True
        assert tray._alarm_type == "full_charge"
        assert tray._snooze_action.isEnabled() is True

    def test_clear_alarm(self, app):
        """Test clearing alarm."""
        tray = TrayIcon()
        tray.update_alarm(True, "full_charge")
        tray.update_alarm(False)

        assert tray._alarm_active is False
        assert tray._alarm_type is None
        assert tray._snooze_action.isEnabled() is False

    def test_toggle_pause(self, app):
        """Test pause toggle."""
        tray = TrayIcon()

        tray._toggle_pause()
        assert tray._is_paused is True
        assert tray._pause_action.text() == "▶️ Resume Monitoring"

        tray._toggle_pause()
        assert tray._is_paused is False
        assert tray._pause_action.text() == "⏸️ Pause Monitoring"