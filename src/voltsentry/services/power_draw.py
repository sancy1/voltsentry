"""
FILE: src/voltsentry/services/power_draw.py
PATH: voltsentry/src/voltsentry/services/power_draw.py
DESCRIPTION: Real-time power draw monitor (Windows WMI / macOS IOKit)
PHASE: 2.3 - Real-Time Power-Draw Monitor

DISCIPLINES:
- 0.1 Logging Standard: INFO once for unsupported, DEBUG for successful reads
- 0.2 Error Handling: Specific exception catching for WMI/IOKit
- 0.3 Retry Standard: 1 attempt per poll (no retry for unsupported)
- 0.4 Fallback Standard: Hide widget if unsupported, re-probe monthly
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..core.constants import IS_LINUX, IS_MACOS, IS_WINDOWS
from ..core.decorators import log_entry_exit, timed
from ..core.exceptions import BatterySensorUnsupportedError
from ..core.logging_config import get_logger
from ..core.types import BatteryReading

logger = get_logger(__name__)


class PowerDrawMonitor:
    """
    Real-time power draw monitor.

    Reads power draw from OS APIs on supported hardware.
    Falls back gracefully if not supported.
    """

    def __init__(self):
        self._supported: Optional[bool] = None  # None = unknown, True = supported, False = unsupported
        self._last_check_time: Optional[datetime] = None
        self._recheck_interval = timedelta(days=30)

        # Platform-specific implementations
        if IS_WINDOWS:
            self._read_power = self._read_windows_power
        elif IS_MACOS:
            self._read_power = self._read_macos_power
        else:
            self._read_power = self._read_unsupported
            self._supported = False

        logger.info(
            "PowerDrawMonitor initialized for %s",
            "Windows" if IS_WINDOWS else "macOS" if IS_MACOS else "Linux",
        )

    @log_entry_exit()
    @timed()
    def get_power_draw(self, force_check: bool = False) -> Optional[float]:
        """
        Get current power draw in watts.

        Args:
            force_check: Force a recheck even if marked unsupported

        Returns:
            Power draw in watts, or None if unsupported
        """
        now = datetime.now()

        # Check if 30 days have elapsed since last support check
        should_recheck = False
        if self._last_check_time is not None:
            if (now - self._last_check_time) > self._recheck_interval:
                should_recheck = True

        # If unsupported and not due for recheck, return early
        if self._supported is False and not force_check and not should_recheck:
            return None

        # Check support if unknown, forced, or recheck interval hit
        if self._supported is None or force_check or should_recheck:
            self._supported = self._check_support()
            self._last_check_time = now

        if not self._supported:
            return None

        # Read power draw
        try:
            power_watts = self._read_power()
            if power_watts is not None and power_watts > 0:
                logger.debug("Power draw: %.2f W", power_watts)
            return power_watts
        except Exception as e:
            logger.warning("Power draw read failed: %s", e)
            return None

    def _check_support(self) -> bool:
        """Check if power draw is supported on this device."""
        try:
            test = self._read_power()
            if test is not None and test > 0:
                logger.info("Power draw sensor supported: %.2f W", test)
                return True
            elif test is not None:
                logger.info("Power draw sensor supported but reading zero")
                return True
            else:
                logger.info("Power draw sensor not supported on this device")
                return False
        except BatterySensorUnsupportedError:
            logger.info("Power draw sensor not supported on this device")
            return False
        except Exception as e:
            logger.warning("Error checking power draw support: %s", e)
            return False

    def _read_windows_power(self) -> Optional[float]:
        """
        Read power draw on Windows using WMI.

        Returns:
            Power draw in watts, or None if unavailable
        """
        try:
            import wmi

            # Connect to WMI
            c = wmi.WMI()

            # Query battery status
            for battery in c.Win32_Battery():
                if hasattr(battery, "DischargeRate") and battery.DischargeRate:
                    if battery.DischargeRate > 0:
                        # DischargeRate is reported in mW on Win32_Battery
                        return float(battery.DischargeRate) / 1000.0

            return None

        except ImportError:
            logger.debug("wmi module not installed, WMI power draw unavailable")
            return None
        except Exception as e:
            logger.debug("WMI power draw query failed: %s", e)
            return None

    def _read_macos_power(self) -> Optional[float]:
        """
        Read power draw on macOS using IOKit.

        Returns:
            Power draw in watts, or None if unavailable
        """
        try:
            from Foundation import NSBundle
            from IOKit import (
                IOPSCopyPowerSourcesInfo,
                IOPSCopyPowerSourcesList,
                IOPSGetPowerSourceDescription,
            )

            ps_info = IOPSCopyPowerSourcesInfo()
            if ps_info is None:
                return None

            try:
                ps_list = IOPSCopyPowerSourcesList(ps_info)
                if ps_list:
                    for ps in ps_list:
                        desc = IOPSGetPowerSourceDescription(ps_info, ps)
                        if desc:
                            if "DrawingCurrent" in desc and "Voltage" in desc:
                                current_ma = desc["DrawingCurrent"]
                                voltage_mv = desc["Voltage"]
                                if current_ma and voltage_mv:
                                    power_mw = (voltage_mv * current_ma) / 1000
                                    return float(power_mw) / 1000.0
            except Exception as e:
                logger.debug("IOKit power draw query failed: %s", e)

            return None

        except ImportError:
            logger.debug("IOKit module not available")
            return None
        except Exception as e:
            logger.debug("macOS power draw query failed: %s", e)
            return None

    def _read_unsupported(self) -> Optional[float]:
        """Placeholder for unsupported platforms."""
        raise BatterySensorUnsupportedError("Power draw not supported on this platform")

    def is_supported(self) -> bool:
        """Check if power draw is supported on this device."""
        if self._supported is None:
            self._supported = self._check_support()
            self._last_check_time = datetime.now()
        return self._supported is True

    def get_status(self) -> dict:
        """Get status information."""
        return {
            "supported": self.is_supported(),
            "last_check": self._last_check_time.isoformat()
            if self._last_check_time
            else None,
            "recheck_interval_days": self._recheck_interval.days,
        }


# ============================================================================
# Global instance for easy access
# ============================================================================
_power_draw_monitor: Optional[PowerDrawMonitor] = None


def get_power_draw_monitor() -> PowerDrawMonitor:
    """Get or create the global power draw monitor."""
    global _power_draw_monitor
    if _power_draw_monitor is None:
        _power_draw_monitor = PowerDrawMonitor()
    return _power_draw_monitor