"""
FILE: src/voltsentry/services/weekly_report.py
PATH: voltsentry/src/voltsentry/services/weekly_report.py
DESCRIPTION: Weekly battery health report generation
PHASE: 3.5 - Alert Persistence & Weekly Report

DISCIPLINES:
- 0.1 Logging Standard: ERROR if report generation fails
- 0.2 Error Handling: Independent error handling (never crashes main app)
- 0.4 Fallback Standard: Skip week's report if generation fails
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..core.config import get_config
from ..core.logging_config import get_logger, log_audit
from ..core.decorators import log_entry_exit, timed
from ..db.repositories import (
    BatteryReadingRepository,
    AlarmEventRepository,
    ChargeCycleRepository,
)

logger = get_logger(__name__)


class WeeklyReportService:
    """
    Weekly battery health report generation.
    
    Generates a summary report each week including:
    - Average battery level
    - Alarm count by type
    - Charge cycles
    - Health score
    - Usage patterns
    """
    
    def __init__(self):
        self.config = get_config()
        self.battery_repo = BatteryReadingRepository()
        self.alarm_repo = AlarmEventRepository()
        self.cycle_repo = ChargeCycleRepository()
        self._last_report_date: Optional[datetime] = None
        
        logger.info("WeeklyReportService initialized")
    
    @log_entry_exit()
    @timed()
    def generate_report(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Generate a weekly report.
        
        Args:
            days: Number of days to include in report
            
        Returns:
            Report data dictionary, or None if generation failed
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get data
            readings = self.battery_repo.get_history(
                limit=10000,
                from_date=start_date,
                to_date=end_date,
            )
            
            alarm_count_full = self.alarm_repo.get_alarm_count(
                alarm_type="full_charge",
                days=days,
            )
            alarm_count_low = self.alarm_repo.get_alarm_count(
                alarm_type="low_battery",
                days=days,
            )
            alarm_count_critical = self.alarm_repo.get_alarm_count(
                alarm_type="critical_low",
                days=days,
            )
            
            total_cycles = self.cycle_repo.get_total_cycles()
            
            # Calculate statistics
            avg_percent = self._calculate_average_percent(readings)
            max_percent = self._calculate_max_percent(readings)
            min_percent = self._calculate_min_percent(readings)
            charging_time = self._calculate_charging_time(readings)
            
            report = {
                "report_date": end_date.isoformat(),
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "statistics": {
                    "average_battery_percent": avg_percent,
                    "max_battery_percent": max_percent,
                    "min_battery_percent": min_percent,
                    "total_cycles": total_cycles,
                    "charging_time_percent": charging_time,
                },
                "alarms": {
                    "full_charge": alarm_count_full,
                    "low_battery": alarm_count_low,
                    "critical_low": alarm_count_critical,
                    "total": alarm_count_full + alarm_count_low + alarm_count_critical,
                },
                "readings_count": len(readings),
            }
            
            self._last_report_date = end_date
            logger.info("Weekly report generated: %d readings", len(readings))
            
            return report
            
        except Exception as e:
            logger.error("Weekly report generation failed: %s", e)
            log_audit("ERROR", f"Weekly report failed: {e}")
            return None
    
    def _calculate_average_percent(self, readings) -> Optional[float]:
        """Calculate average battery percentage."""
        if not readings:
            return None
        total = sum(r.percent for r in readings)
        return round(total / len(readings), 1)
    
    def _calculate_max_percent(self, readings) -> Optional[int]:
        """Calculate maximum battery percentage."""
        if not readings:
            return None
        return max(r.percent for r in readings)
    
    def _calculate_min_percent(self, readings) -> Optional[int]:
        """Calculate minimum battery percentage."""
        if not readings:
            return None
        return min(r.percent for r in readings)
    
    def _calculate_charging_time(self, readings) -> Optional[float]:
        """Calculate percentage of time spent charging."""
        if not readings:
            return None
        charging_count = sum(1 for r in readings if r.is_charging)
        return round((charging_count / len(readings)) * 100, 1)
    
    def get_report_age(self) -> Optional[int]:
        """Get age of last report in days."""
        if self._last_report_date is None:
            return None
        return (datetime.now() - self._last_report_date).days
    
    def should_generate_report(self, days: int = 7) -> bool:
        """Check if a new report should be generated."""
        if self._last_report_date is None:
            return True
        return (datetime.now() - self._last_report_date).days >= days
    
    def __repr__(self) -> str:
        return f"<WeeklyReportService last_report={self._last_report_date}>"