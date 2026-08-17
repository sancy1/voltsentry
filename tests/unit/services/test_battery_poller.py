"""
FILE: tests/unit/services/test_battery_poller.py
PATH: voltsentry/tests/unit/services/test_battery_poller.py
DESCRIPTION: Unit tests for BatteryPoller service
PHASE: 2.1 - Battery Polling Service
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QCoreApplication
import pytest

from voltsentry.core.exceptions import BatteryReadError
from voltsentry.core.types import BatteryReading, ChargingState, HealthSource
from voltsentry.services.battery_poller import BatteryPoller


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QCoreApplication instance exists for Qt signals/timers."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app


@pytest.fixture
def mock_repo():
    """Mock BatteryReadingRepository."""
    return MagicMock()


@pytest.fixture
def poller(qapp, mock_repo):
    """Create a BatteryPoller instance with mock repository."""
    return BatteryPoller(repository=mock_repo, poll_interval=1)


class TestBatteryPoller:
    """Unit tests for BatteryPoller."""

    def test_initialization(self, poller):
        """Test initial state of poller."""
        assert poller.is_running is False
        assert poller.is_degraded is False
        assert poller.current_reading is None

    def test_start_stop(self, poller):
        """Test starting and stopping the poller."""
        with patch("voltsentry.services.battery_poller.psutil.sensors_battery") as mock_sensors:
            mock_sensors.return_value = MagicMock(percent=85, power_plugged=True)
            poller.start()
            assert poller.is_running is True

            poller.stop()
            assert poller.is_running is False

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_successful_poll(self, mock_sensors, poller):
        """Test successful battery polling."""
        mock_sensors.return_value = MagicMock(percent=80, power_plugged=False)
        poller._is_running = True

        poller._poll()

        assert poller.current_reading is not None
        assert poller.current_reading.percent == 80
        assert poller.current_reading.is_charging is False
        assert poller._consecutive_failures == 0
        poller.repository.save.assert_called_once()

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_poll_failure(self, mock_sensors, poller):
        """Test failure during battery polling."""
        mock_sensors.return_value = None  # psutil returns None when no battery found
        poller._is_running = True

        poller._poll()

        assert poller._consecutive_failures == 1
        assert poller.is_degraded is False

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_degraded_mode_entry(self, mock_sensors, poller):
        """Test entering degraded mode after 5 consecutive failures."""
        mock_sensors.return_value = None
        poller._is_running = True

        degraded_signal_emitted = False

        def on_degraded():
            nonlocal degraded_signal_emitted
            degraded_signal_emitted = True

        poller.degraded_mode_entered.connect(on_degraded)

        for i in range(5):
            poller._poll()
            assert poller._consecutive_failures == i + 1

        assert poller.is_degraded is True
        assert degraded_signal_emitted is True

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_degraded_mode_exit(self, mock_sensors, poller):
        """Test exiting degraded mode after a successful poll."""
        # Force poller into degraded mode
        poller._degraded_mode = True
        poller._consecutive_failures = 5
        poller._is_running = True

        mock_sensors.return_value = MagicMock(percent=90, power_plugged=True)

        degraded_exit_emitted = False

        def on_exit():
            nonlocal degraded_exit_emitted
            degraded_exit_emitted = True

        poller.degraded_mode_exited.connect(on_exit)

        poller._poll()

        assert poller.is_degraded is False
        assert poller._consecutive_failures == 0
        assert degraded_exit_emitted is True

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_state_change_detection(self, mock_sensors, poller):
        """Test emission of state_changed signal on charging state transition."""
        poller._is_running = True

        states_received = []

        def on_state_changed(old_state, new_state):
            states_received.append((old_state, new_state))

        poller.state_changed.connect(on_state_changed)

        # First poll: Discharging
        mock_sensors.return_value = MagicMock(percent=50, power_plugged=False)
        poller._poll()

        # Second poll: Charging
        mock_sensors.return_value = MagicMock(percent=51, power_plugged=True)
        poller._poll()

        assert len(states_received) == 2
        assert states_received[0] == ("unknown", "discharging")
        assert states_received[1] == ("discharging", "charging")

    @patch("voltsentry.services.battery_poller.psutil.sensors_battery")
    def test_circuit_breaker(self, mock_sensors, poller):
        """Test circuit breaker opens after maximum consecutive failures."""
        mock_sensors.return_value = None
        poller._is_running = True

        for _ in range(5):
            poller._poll()

        assert poller._circuit_breaker.is_open is True

        # Subsequent polls should be skipped
        call_count_before = poller._consecutive_failures
        poller._poll()
        assert poller._consecutive_failures == call_count_before