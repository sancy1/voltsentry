"""
FILE: src/voltsentry/services/battery_report.py
PATH: voltsentry/src/voltsentry/services/battery_report.py
DESCRIPTION: OS battery report parser (Windows powercfg / macOS system_profiler)
PHASE: 2.2 - OS Battery-Report Parser

DISCIPLINES:
- 0.1 Logging Standard: WARNING on fallback, INFO on successful parse
- 0.2 Error Handling: Specific exception catching for subprocess and XML parsing
- 0.3 Retry Standard: 2 attempts on subprocess.TimeoutExpired only
- 0.4 Fallback Standard: Falls back to estimated health with "estimated" badge
"""

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET

import psutil

from ..core.constants import (
    BATTERY_REPORT_INTERVAL_SECONDS,
    BATTERY_REPORT_PATH,
    DATA_DIR,
    IS_MACOS,
    IS_WINDOWS,
)
from ..core.decorators import log_entry_exit, timed
from ..core.exceptions import BatteryReportUnavailableError
from ..core.logging_config import get_logger
from ..core.resilience import resilient
from ..core.types import HealthSnapshot, HealthSource

logger = get_logger(__name__)


class BatteryReportService:
    """
    Service for parsing OS battery reports.

    Fetches manufacturer-reported battery data including:
    - Design capacity
    - Full charge capacity
    - Cycle count
    - Health score

    Falls back to estimated health if OS report is unavailable.
    """

    def __init__(self):
        self._report_path = BATTERY_REPORT_PATH
        self._last_report_time: Optional[datetime] = None
        self._cached_snapshot: Optional[HealthSnapshot] = None
        self._report_interval = BATTERY_REPORT_INTERVAL_SECONDS

        logger.info("BatteryReportService initialized")

    @log_entry_exit()
    @timed()
    def get_health_snapshot(self, force_refresh: bool = False) -> HealthSnapshot:
        """
        Get the latest battery health snapshot.

        Args:
            force_refresh: Force a refresh even if within cache window

        Returns:
            HealthSnapshot object with health data
        """
        # Check cache
        if not force_refresh and self._cached_snapshot is not None:
            if self._last_report_time is not None:
                age = (datetime.now() - self._last_report_time).total_seconds()
                if age < self._report_interval:
                    logger.debug(
                        "Using cached health snapshot (age: %.1f hours)", age / 3600
                    )
                    return self._cached_snapshot

        # Try to get OS report
        try:
            snapshot = self._get_os_report()
            self._cached_snapshot = snapshot
            self._last_report_time = datetime.now()
            logger.info(
                "Health snapshot from OS report: score=%.1f%%, cycles=%d",
                snapshot.health_score,
                snapshot.cycle_count,
            )
            return snapshot
        except BatteryReportUnavailableError as e:
            logger.warning("OS battery report unavailable: %s", e)

            # Fallback to estimated health
            snapshot = self._get_estimated_health()
            self._cached_snapshot = snapshot
            self._last_report_time = datetime.now()
            logger.info(
                "Health snapshot from estimate: score=%.1f%% (ESTIMATED)",
                snapshot.health_score,
            )
            return snapshot

    @log_entry_exit()
    @resilient(exceptions=(subprocess.TimeoutExpired,), attempts=2)
    def _get_os_report(self) -> HealthSnapshot:
        """
        Get battery report from the operating system.

        Returns:
            HealthSnapshot with OS-reported data

        Raises:
            BatteryReportUnavailableError: If report cannot be obtained
        """
        if IS_WINDOWS:
            return self._get_windows_report()
        elif IS_MACOS:
            return self._get_macos_report()
        else:
            raise BatteryReportUnavailableError(
                "Unsupported platform for OS battery report"
            )

    def _get_windows_report(self) -> HealthSnapshot:
        """
        Get battery report on Windows using powercfg.

        Returns:
            HealthSnapshot with Windows-reported data

        Raises:
            BatteryReportUnavailableError: If Windows battery report generation fails
        """
        # Ensure directory exists
        self._report_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Generate XML battery report
            subprocess.run(
                [
                    "powercfg",
                    "/batteryreport",
                    "/xml",
                    "/output",
                    str(self._report_path),
                ],
                timeout=10,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug("powercfg XML battery report generated")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.debug("XML battery report generation failed or timed out: %s", e)
            # Try falling back to HTML report generation
            try:
                return self._parse_windows_html_report()
            except Exception as html_err:
                raise BatteryReportUnavailableError(
                    f"Windows battery report generation failed: {html_err}"
                ) from html_err
        except FileNotFoundError as e:
            raise BatteryReportUnavailableError("powercfg not found") from e
        except Exception as e:
            raise BatteryReportUnavailableError(
                f"Windows battery report generation failed: {e}"
            ) from e

        # Parse the XML report
        try:
            return self._parse_windows_xml_report(self._report_path)
        except (ET.ParseError, FileNotFoundError, BatteryReportUnavailableError) as e:
            logger.debug("XML report parsing failed, falling back to HTML: %s", e)
            try:
                return self._parse_windows_html_report()
            except Exception as html_err:
                raise BatteryReportUnavailableError(
                    f"Windows battery report parsing failed: {html_err}"
                ) from html_err

    def _parse_windows_xml_report(self, xml_path: Path) -> HealthSnapshot:
        """
        Parse the Windows battery report XML.

        Returns:
            HealthSnapshot extracted from XML
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        design_capacity = None
        full_charge_capacity = None
        cycle_count = 0

        # Traverse tags ignoring namespace prefix differences
        for elem in root.iter():
            tag_name = elem.tag.rsplit("}", 1)[-1] if "}" in elem.tag else elem.tag

            if tag_name == "DesignCapacity" and elem.text and not design_capacity:
                try:
                    design_capacity = int(elem.text.strip())
                except ValueError:
                    pass

            elif tag_name == "FullChargeCapacity" and elem.text and not full_charge_capacity:
                try:
                    full_charge_capacity = int(elem.text.strip())
                except ValueError:
                    pass

            elif tag_name == "CycleCount" and elem.text and not cycle_count:
                try:
                    cycle_count = int(elem.text.strip())
                except ValueError:
                    pass

        # If XML parsing failed to locate key figures, fallback to HTML parser
        if design_capacity is None or full_charge_capacity is None:
            return self._parse_windows_html_report()

        health_score = self._calculate_health_score(
            design_capacity, full_charge_capacity
        )

        return HealthSnapshot(
            source=HealthSource.OS_REPORT,
            design_capacity=design_capacity,
            full_charge_capacity=full_charge_capacity,
            cycle_count=cycle_count,
            health_score=health_score,
        )

    def _parse_windows_html_report(self) -> HealthSnapshot:
        """
        Parse Windows battery report from HTML as fallback.

        Returns:
            HealthSnapshot extracted from HTML
        """
        try:
            html_path = self._report_path.with_suffix(".html")
            subprocess.run(
                ["powercfg", "/batteryreport", "/output", str(html_path)],
                timeout=10,
                capture_output=True,
                text=True,
                check=True,
            )

            content = html_path.read_text(encoding="utf-8", errors="ignore")

            def clean_num(val_str: Optional[str]) -> Optional[int]:
                if not val_str:
                    return None
                cleaned = re.sub(r"[^\d]", "", val_str)
                return int(cleaned) if cleaned else None

            design_match = re.search(
                r"DESIGN CAPACITY[^\d]*([\d, ]+)\s*mWh", content, re.IGNORECASE
            )
            full_match = re.search(
                r"FULL CHARGE CAPACITY[^\d]*([\d, ]+)\s*mWh", content, re.IGNORECASE
            )
            cycle_match = re.search(
                r"CYCLE COUNT[^\d]*([\d, ]+)", content, re.IGNORECASE
            )

            design_capacity = clean_num(design_match.group(1)) if design_match else None
            full_charge_capacity = (
                clean_num(full_match.group(1)) if full_match else None
            )
            cycle_count = clean_num(cycle_match.group(1)) if cycle_match else 0

            if design_capacity is None or full_charge_capacity is None:
                raise BatteryReportUnavailableError(
                    "Could not parse battery capacities from HTML"
                )

            health_score = self._calculate_health_score(
                design_capacity, full_charge_capacity
            )

            return HealthSnapshot(
                source=HealthSource.OS_REPORT,
                design_capacity=design_capacity,
                full_charge_capacity=full_charge_capacity,
                cycle_count=cycle_count,
                health_score=health_score,
            )

        except Exception as e:
            raise BatteryReportUnavailableError(
                f"HTML report parsing failed: {e}"
            ) from e

    def _get_macos_report(self) -> HealthSnapshot:
        """
        Get battery report on macOS using system_profiler.

        Returns:
            HealthSnapshot with macOS-reported data
        """
        try:
            result = subprocess.run(
                ["system_profiler", "SPPowerDataType", "-json"],
                timeout=10,
                capture_output=True,
                text=True,
                check=True,
            )

            data = json.loads(result.stdout)

            for item in data.get("SPPowerDataType", []):
                # Parse JSON structure or text fallback
                if "sppower_battery_health_info" in item:
                    health_info = item.get("sppower_battery_health_info", {})
                    cycle_count = int(health_info.get("sppower_battery_cycle_count", 0))
                    max_capacity = health_info.get("sppower_battery_max_capacity")
                    design_capacity = health_info.get("sppower_battery_design_capacity")
                    
                    if max_capacity:
                        full_charge_capacity = int(max_capacity)
                        design_cap = int(design_capacity) if design_capacity else full_charge_capacity
                        health_score = self._calculate_health_score(
                            design_cap, full_charge_capacity
                        )
                        return HealthSnapshot(
                            source=HealthSource.OS_REPORT,
                            design_capacity=design_cap,
                            full_charge_capacity=full_charge_capacity,
                            cycle_count=cycle_count,
                            health_score=health_score,
                        )

                if "battery" in item.get("_name", "").lower():
                    design_capacity = item.get("design_capacity")
                    full_charge_capacity = item.get("max_capacity")
                    cycle_count = item.get("cycle_count", 0)

                    if design_capacity and full_charge_capacity:
                        health_score = self._calculate_health_score(
                            design_capacity, full_charge_capacity
                        )

                        return HealthSnapshot(
                            source=HealthSource.OS_REPORT,
                            design_capacity=design_capacity,
                            full_charge_capacity=full_charge_capacity,
                            cycle_count=cycle_count,
                            health_score=cycle_count,
                        )

            # Text parsing fallback if JSON output structure is raw text
            stdout = result.stdout
            if "Maximum Capacity" in stdout or "Cycle Count" in stdout:
                max_cap_match = re.search(r"Maximum Capacity:\s*(\d+)%", stdout)
                cycle_match = re.search(r"Cycle Count:\s*(\d+)", stdout)
                
                health_score = float(max_cap_match.group(1)) if max_cap_match else 100.0
                cycle_count = int(cycle_match.group(1)) if cycle_match else 0
                
                design_cap = 50000
                full_cap = int(design_cap * health_score / 100)
                
                return HealthSnapshot(
                    source=HealthSource.OS_REPORT,
                    design_capacity=design_cap,
                    full_charge_capacity=full_cap,
                    cycle_count=cycle_count,
                    health_score=health_score,
                )

            raise BatteryReportUnavailableError(
                "Battery information not found in system_profiler output"
            )

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise BatteryReportUnavailableError(f"macOS report failed: {e}") from e
        except FileNotFoundError as e:
            raise BatteryReportUnavailableError("system_profiler not found") from e
        except Exception as e:
            raise BatteryReportUnavailableError(f"macOS report failed: {e}") from e

    def _calculate_health_score(
        self, design_capacity: int, full_charge_capacity: int
    ) -> float:
        """
        Calculate battery health score as percentage.

        Args:
            design_capacity: Original design capacity (mWh)
            full_charge_capacity: Current full charge capacity (mWh)

        Returns:
            Health score as percentage (0-100)
        """
        if design_capacity <= 0:
            return 100.0

        score = (full_charge_capacity / design_capacity) * 100
        return round(max(0.0, min(100.0, score)), 2)

    def _get_estimated_health(self) -> HealthSnapshot:
        """
        Get estimated battery health when OS report is unavailable.

        Returns:
            HealthSnapshot with estimated data (marked as ESTIMATED)
        """
        default_design_capacity = 50000  # 50Wh typical

        try:
            battery = psutil.sensors_battery()
            if battery:
                health_estimate = float(battery.percent)
            else:
                health_estimate = 85.0
        except Exception:
            health_estimate = 85.0

        return HealthSnapshot(
            source=HealthSource.ESTIMATED,
            design_capacity=default_design_capacity,
            full_charge_capacity=int(
                default_design_capacity * health_estimate / 100
            ),
            cycle_count=0,
            health_score=health_estimate,
        )

    def get_report_age(self) -> Optional[float]:
        """
        Get the age of the last report in seconds.

        Returns:
            Age in seconds, or None if no report exists
        """
        if self._last_report_time is None:
            return None
        return (datetime.now() - self._last_report_time).total_seconds()