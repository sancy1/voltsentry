"""
FILE: tests/unit/services/test_weekly_report.py
PATH: voltsentry/tests/unit/services/test_weekly_report.py
DESCRIPTION: Unit tests for Weekly Battery Health Report Generator (WeeklyReportService)
PHASE: 3.5 - Alert Persistence & Weekly Report
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from voltsentry.services.weekly_report import WeeklyReportService


class TestWeeklyReportService:
    """Unit tests for WeeklyReportService."""

    @pytest.fixture
    def mock_repositories(self):
        """Mock data repositories for WeeklyReportService dependencies."""
        with patch("voltsentry.services.weekly_report.get_config") as mock_get_config, patch(
            "voltsentry.services.weekly_report.BatteryReadingRepository"
        ) as mock_battery_cls, patch(
            "voltsentry.services.weekly_report.AlarmEventRepository"
        ) as mock_alarm_cls, patch(
            "voltsentry.services.weekly_report.ChargeCycleRepository"
        ) as mock_cycle_cls:

            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            mock_battery_repo = MagicMock()
            mock_battery_cls.return_value = mock_battery_repo

            mock_alarm_repo = MagicMock()
            mock_alarm_cls.return_value = mock_alarm_repo

            mock_cycle_repo = MagicMock()
            mock_cycle_cls.return_value = mock_cycle_repo

            yield {
                "config": mock_config,
                "battery_repo": mock_battery_repo,
                "alarm_repo": mock_alarm_repo,
                "cycle_repo": mock_cycle_repo,
            }

    @pytest.fixture
    def report_service(self, mock_repositories):
        """Fixture providing a WeeklyReportService instance."""
        return WeeklyReportService()

    def test_initialization(self, report_service):
        """Test initial state of WeeklyReportService."""
        assert report_service._last_report_date is None
        assert report_service.get_report_age() is None
        assert report_service.should_generate_report() is True

    def test_generate_report_success(self, report_service, mock_repositories):
        """Test successful weekly report generation and calculations."""
        # Setup mock readings
        r1 = MagicMock(percent=50, is_charging=True)
        r2 = MagicMock(percent=80, is_charging=False)
        r3 = MagicMock(percent=20, is_charging=False)
        mock_repositories["battery_repo"].get_history.return_value = [r1, r2, r3]

        # Setup mock alarm counts
        mock_repositories["alarm_repo"].get_alarm_count.side_effect = lambda alarm_type, days: {
            "full_charge": 2,
            "low_battery": 4,
            "critical_low": 1,
        }.get(alarm_type, 0)

        # Setup mock charge cycles
        mock_repositories["cycle_repo"].get_total_cycles.return_value = 12

        report = report_service.generate_report(days=7)

        assert report is not None
        assert report["period_days"] == 7
        assert report["readings_count"] == 3

        # Statistics checks
        stats = report["statistics"]
        assert stats["average_battery_percent"] == 50.0  # (50+80+20)/3 = 50.0
        assert stats["max_battery_percent"] == 80
        assert stats["min_battery_percent"] == 20
        assert stats["total_cycles"] == 12
        assert stats["charging_time_percent"] == 33.3  # (1/3)*100 = 33.3%

        # Alarm breakdown checks
        alarms = report["alarms"]
        assert alarms["full_charge"] == 2
        assert alarms["low_battery"] == 4
        assert alarms["critical_low"] == 1
        assert alarms["total"] == 7

        assert report_service._last_report_date is not None
        assert report_service.should_generate_report(days=7) is False

    def test_generate_report_empty_readings(self, report_service, mock_repositories):
        """Test report calculations when no battery readings exist in the database."""
        mock_repositories["battery_repo"].get_history.return_value = []
        mock_repositories["alarm_repo"].get_alarm_count.return_value = 0
        mock_repositories["cycle_repo"].get_total_cycles.return_value = 0

        report = report_service.generate_report(days=7)

        assert report is not None
        stats = report["statistics"]
        assert stats["average_battery_percent"] is None
        assert stats["max_battery_percent"] is None
        assert stats["min_battery_percent"] is None
        assert stats["charging_time_percent"] is None
        assert report["readings_count"] == 0

    def test_generate_report_repository_exception_returns_none(
        self, report_service, mock_repositories
    ):
        """Test that database failures return None and do not crash the application."""
        mock_repositories["battery_repo"].get_history.side_effect = Exception("DB Connection Lost")

        report = report_service.generate_report(days=7)

        assert report is None
        assert report_service._last_report_date is None

    def test_should_generate_report_and_get_report_age(self, report_service):
        """Test report schedule timing logic and age calculations."""
        base_time = datetime(2026, 8, 15, 12, 0, 0)

        with patch("voltsentry.services.weekly_report.datetime") as mock_datetime:
            mock_datetime.now.return_value = base_time
            report_service._last_report_date = base_time

            # Same day -> False
            assert report_service.should_generate_report(days=7) is False
            assert report_service.get_report_age() == 0

            # 8 days later -> True
            mock_datetime.now.return_value = base_time + timedelta(days=8)
            assert report_service.get_report_age() == 8
            assert report_service.should_generate_report(days=7) is True