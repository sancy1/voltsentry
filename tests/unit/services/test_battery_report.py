"""
FILE: tests/unit/services/test_battery_report.py
PATH: voltsentry/tests/unit/services/test_battery_report.py
DESCRIPTION: Unit tests for BatteryReportService
PHASE: 3.5 - Battery Health Report
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from voltsentry.core.exceptions import BatteryReportUnavailableError
from voltsentry.services.battery_report import BatteryReportService, HealthSnapshot, HealthSource


class TestBatteryReportService:
    """Unit tests for BatteryReportService."""

    @pytest.fixture
    def report_service(self):
        """Fixture providing BatteryReportService instance."""
        return BatteryReportService()

    @patch("voltsentry.services.battery_report.IS_WINDOWS", True)
    @patch("voltsentry.services.battery_report.IS_MACOS", False)
    @patch("subprocess.run")
    @patch("builtins.open")
    @patch("os.path.exists", return_value=True)
    def test_windows_report_success(self, mock_exists, mock_open, mock_subproc, report_service):
        """Test generating battery health snapshot on Windows."""
        mock_subproc.return_value = MagicMock(returncode=0)

        with patch.object(report_service, "_parse_windows_html_report") as mock_parse:
            mock_parse.return_value = HealthSnapshot(
                design_capacity=50000,
                full_charge_capacity=45000,
                cycle_count=120,
                health_score=90.0,
                source=HealthSource.OS_REPORT,
            )
            snapshot = report_service._get_os_report()

            assert snapshot.design_capacity == 50000
            assert snapshot.full_charge_capacity == 45000
            assert snapshot.cycle_count == 120
            assert snapshot.health_score == 90.0
            assert snapshot.source == HealthSource.OS_REPORT

    @patch("voltsentry.services.battery_report.IS_WINDOWS", True)
    @patch("subprocess.run")
    def test_windows_report_failure(self, mock_subproc, report_service):
        """Test Windows report generation failure throws BatteryReportUnavailableError."""
        mock_subproc.side_effect = Exception("powercfg failed")

        with pytest.raises(BatteryReportUnavailableError):
            report_service._get_windows_report()

    @patch("voltsentry.services.battery_report.IS_MACOS", True)
    @patch("voltsentry.services.battery_report.IS_WINDOWS", False)
    @patch("subprocess.run")
    def test_macos_report_success(self, mock_subproc, report_service):
        """Test generating battery health snapshot on macOS via system_profiler JSON output."""
        mock_data = {
            "SPPowerDataType": [
                {
                    "_name": "sppower_battery_charge_info",
                    "sppower_battery_health_info": {
                        "sppower_battery_cycle_count": 120,
                        "sppower_battery_max_capacity": 45000,
                        "sppower_battery_design_capacity": 50000,
                    },
                }
            ]
        }
        mock_subproc.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data))

        snapshot = report_service._get_os_report()

        assert int(snapshot.design_capacity) == 50000
        assert int(snapshot.full_charge_capacity) == 45000
        assert int(snapshot.cycle_count) == 120
        assert snapshot.health_score == 90.0

    def test_calculate_health_score(self, report_service):
        """Test health score percentage calculation."""
        # _calculate_health_score(design_capacity, full_charge_capacity)
        score = report_service._calculate_health_score(50000, 45000)
        assert score == 90.0

        score_zero = report_service._calculate_health_score(0, 45000)
        assert score_zero == 100.0

    def test_cache_behavior(self, report_service):
        """Test health snapshot caching."""
        dummy_snapshot = HealthSnapshot(
            design_capacity=50000,
            full_charge_capacity=45000,
            cycle_count=100,
            health_score=90.0,
            source=HealthSource.OS_REPORT,
        )

        with patch.object(report_service, "_get_os_report", return_value=dummy_snapshot) as mock_get:
            res1 = report_service.get_health_snapshot(force_refresh=False)
            res2 = report_service.get_health_snapshot(force_refresh=False)

            assert res1 == dummy_snapshot
            assert res2 == dummy_snapshot
            mock_get.assert_called_once()