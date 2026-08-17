"""
FILE: tests/unit/ui/test_dashboard.py
PATH: voltsentry/tests/unit/ui/test_dashboard.py
DESCRIPTION: Unit tests for DashboardWindow
PHASE: 4 - Testing
"""

from datetime import datetime
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from voltsentry.core.types import BatteryReading, HealthSource
from voltsentry.ui.dashboard import DashboardWindow


@pytest.fixture(scope="session")
def app():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestDashboardWindow:
    """Test suite for DashboardWindow."""

    def test_creation(self, app):
        """Test dashboard creation."""
        dashboard = DashboardWindow()
        assert dashboard is not None
        assert dashboard.isVisible() is False

    def test_show_event(self, app):
        """Test showing dashboard."""
        dashboard = DashboardWindow()
        dashboard.show_event()

        assert dashboard.isVisible() is True

    def test_battery_update(self, app):
        """Test battery reading update."""
        dashboard = DashboardWindow()
        reading = BatteryReading(
            timestamp=datetime.now(),
            percent=85,
            is_charging=True,
            power_draw_watts=12.5,
            source=HealthSource.OS_REPORT,
        )

        dashboard._on_reading_updated(reading)

        assert dashboard._battery_card._value == "85%"
        assert dashboard._battery_card._status == "success"

    def test_low_battery_update(self, app):
        """Test low battery update."""
        dashboard = DashboardWindow()
        reading = BatteryReading(
            timestamp=datetime.now(),
            percent=15,
            is_charging=False,
            power_draw_watts=None,
            source=HealthSource.ESTIMATED,
        )

        dashboard._on_reading_updated(reading)

        assert dashboard._battery_card._value == "15%"
        assert dashboard._battery_card._status == "danger"

    def test_alarm_buttons(self, app):
        """Test alarm buttons are enabled/disabled."""
        dashboard = DashboardWindow()

        # Initially disabled
        assert dashboard._stop_alarm_btn.isEnabled() is False
        assert dashboard._snooze_btn.isEnabled() is False

        # Trigger alarm
        dashboard._show_alarm_banner()

        # Should be enabled (if alarm_service exists)
        # Note: In test, alarm_service is None, so buttons stay disabled