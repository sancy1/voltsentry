"""
FILE: tests/integration/test_battery_integration.py
DESCRIPTION: Integration tests for battery services
PATH: voltsentry/tests/integration/test_battery_integration.py
PHASE: 2.6 - Unit & Integration Tests
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
import pytest

from voltsentry.services.battery_poller import BatteryPoller
from voltsentry.services.battery_report import BatteryReportService, HealthSnapshot, HealthSource
from voltsentry.services.power_draw import PowerDrawMonitor


@pytest.mark.integration
class TestBatteryIntegration:
    """Integration tests for battery services."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create a QCoreApplication for testing."""
        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication([])
        return app

    def _wait_for_condition(self, condition_func, timeout_ms=5000):
        """Helper to process Qt events while waiting for a condition without thread starvation."""
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(50)

        def check():
            if condition_func():
                timer.stop()
                loop.quit()

        timer.timeout.connect(check)
        timer.start()

        # Safety timeout to prevent infinite loops
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()

    @patch.object(BatteryReportService, "_get_os_report")
    def test_full_poll_cycle(self, mock_os_report, app):
        """Test a complete poll cycle with all components."""
        mock_os_report.return_value = HealthSnapshot(
            design_capacity=50000,
            full_charge_capacity=45000,
            cycle_count=120,
            health_score=90.0,
            source=HealthSource.OS_REPORT,
        )

        poller = BatteryPoller(poll_interval=1)
        report_service = BatteryReportService()
        power_monitor = PowerDrawMonitor()

        poller.start()
        assert poller.is_running is True

        # Wait until poller yields at least one valid reading
        self._wait_for_condition(lambda: poller.current_reading is not None, timeout_ms=3000)

        poller.stop()
        assert poller.is_running is False
        assert poller.current_reading is not None

        snapshot = report_service.get_health_snapshot()
        assert snapshot.health_score > 0
        assert snapshot.source == HealthSource.OS_REPORT

        # Power draw check (gracefully handles None on unsupported systems)
        _ = power_monitor.get_power_draw()

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_fallback_chain(self, mock_sensors, app):
        """Test the fallback chain when components fail."""
        mock_sensors.side_effect = OSError("Battery sensor failed")

        poller = BatteryPoller(poll_interval=1)
        degraded_entered = False

        def on_degraded():
            nonlocal degraded_entered
            degraded_entered = True

        poller.degraded_mode_entered.connect(on_degraded)
        poller.start()

        # Wait for degraded mode to trigger without blocking Qt event loop
        self._wait_for_condition(lambda: poller.is_degraded, timeout_ms=8000)

        assert degraded_entered is True
        assert poller.is_degraded is True

        poller.stop()

    def test_heartbeat_integration(self, app):
        """Test heartbeat with poller integration."""
        from voltsentry.services.heartbeat import get_heartbeat_service

        heartbeat = get_heartbeat_service()
        poller = BatteryPoller(poll_interval=1)

        poller.reading_updated.connect(lambda reading: heartbeat.beat())
        poller.start()

        # Wait for at least one heartbeat signal
        self._wait_for_condition(
            lambda: heartbeat.get_heartbeat_age() is not None and heartbeat.get_heartbeat_age() < 5,
            timeout_ms=3000,
        )

        age = heartbeat.get_heartbeat_age()
        assert age is not None
        assert age < 5

        poller.stop()