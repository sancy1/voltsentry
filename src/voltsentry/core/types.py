# File: types.py
# Path: voltsentry/src/voltsentry/core/types.py
# Description: Centralized type definitions, Enums, DTO dataclasses, Protocols, and TypedDicts for VoltSentry.

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Protocol, TypeVar, TypedDict, Union

# ============================================================================
# Enums
# ============================================================================
class ChargingState(Enum):
    """Battery charging state."""

    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULL = "full"
    UNKNOWN = "unknown"


class AlarmType(Enum):
    """Types of alarms."""

    NONE = "none"
    FULL_CHARGE = "full_charge"
    LOW_BATTERY = "low_battery"
    CRITICAL_LOW = "critical_low"


class AlarmPriority(Enum):
    """Alarm priority (higher number = higher priority)."""

    NONE = 0
    FULL_CHARGE = 1
    LOW_BATTERY = 2
    CRITICAL_LOW = 3


class HealthSource(Enum):
    """Source of health data."""

    OS_REPORT = "os_report"
    ESTIMATED = "estimated"


class CalibrationState(Enum):
    """Calibration wizard states."""

    IDLE = "idle"
    AWAITING_FULL_CHARGE = "awaiting_full_charge"
    AWAITING_FULL_DISCHARGE = "awaiting_full_discharge"
    RECALCULATING = "recalculating"
    COMPLETE = "complete"
    ABORTED = "aborted"


class HookType(Enum):
    """Automation hook types."""

    WEBHOOK = "webhook"
    SCRIPT = "script"


# ============================================================================
# Dataclasses (Data Transfer Objects)
# ============================================================================
@dataclass(frozen=True)
class BatteryReading:
    """Immutable battery reading snapshot."""

    timestamp: datetime
    percent: int
    is_charging: bool
    power_draw_watts: Optional[float]
    source: HealthSource

    def __post_init__(self) -> None:
        """Validate that percent is within 0-100 range."""
        if not 0 <= self.percent <= 100:
            raise ValueError(f"Percent must be 0-100, got {self.percent}")


@dataclass
class HealthSnapshot:
    """Battery health snapshot from OS report."""

    source: HealthSource
    design_capacity: int  # mWh
    full_charge_capacity: int  # mWh
    cycle_count: int
    health_score: float  # 0-100


@dataclass
class AlarmEvent:
    """Alarm event record."""

    timestamp: datetime
    alarm_type: AlarmType
    acknowledged_at: Optional[datetime] = None
    snoozed: bool = False
    snooze_until: Optional[datetime] = None


@dataclass
class CalibrationRecord:
    """Calibration session record."""

    started_at: datetime
    completed_at: Optional[datetime] = None
    result_health_score: Optional[int] = None
    state: CalibrationState = CalibrationState.IDLE


@dataclass
class AutomationHookConfig:
    """Configuration for an automation hook."""

    hook_type: HookType
    url: Optional[str] = None  # For webhooks
    script_path: Optional[str] = None  # For scripts
    enabled: bool = True
    failure_count: int = 0
    max_failures: int = 5


# ============================================================================
# Protocols (Interfaces)
# ============================================================================
T = TypeVar("T")


class BatteryReader(Protocol):
    """Protocol for battery reading sources."""

    def read(self) -> Optional[BatteryReading]:
        """Read current battery state."""
        ...

    def supports_power_draw(self) -> bool:
        """Check if power draw is supported."""
        ...


class AlarmPlayer(Protocol):
    """Protocol for alarm playback."""

    def play(self, alarm_type: AlarmType) -> bool:
        """Play alarm sound. Returns True if successful."""
        ...

    def stop(self) -> None:
        """Stop currently playing alarm."""
        ...

    def set_volume(self, volume: float) -> None:
        """Set alarm volume (0.0 to 1.0)."""
        ...


class Repository(Protocol[T]):
    """Protocol for generic repository pattern."""

    def save(self, entity: T) -> None:
        """Save an entity."""
        ...

    def find_by_id(self, id_val: int) -> Optional[T]:
        """Find entity by ID."""
        ...


# ============================================================================
# TypedDicts
# ============================================================================
class BatteryReportData(TypedDict, total=False):
    """Windows powercfg / macOS system_profiler output structure."""

    design_capacity: int
    full_charge_capacity: int
    cycle_count: int
    serial_number: str
    manufacturer: str


class ConfigData(TypedDict, total=False):
    """Application configuration schema."""

    charge_threshold_high: int
    charge_threshold_low: int
    poll_interval_seconds: int
    quiet_hours_start: str
    quiet_hours_end: str
    alarm_volume: float
    custom_alarm_path: Optional[str]
    start_with_os: bool
    weekly_report_enabled: bool
    weekly_report_time: str  # HH:MM format


class FleetSnapshot(TypedDict):
    """Fleet view health snapshot."""

    device_id: str
    timestamp: str
    health_score: float
    cycle_count: int
    charge_threshold_high: int
    charge_threshold_low: int
    is_compliant: bool


# ============================================================================
# Callbacks & Type Aliases
# ============================================================================
ReadingCallback = Callable[[BatteryReading], None]
ErrorCallback = Callable[[Exception], None]
AlarmCallback = Callable[[AlarmType], None]