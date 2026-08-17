# File: config.py
# Path: voltsentry/src/voltsentry/core/config.py
# Description: Configuration management with atomic writes, Thread Safety, backups, and fallbacks.

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

from voltsentry.core.constants import (
    CONFIG_BACKUP_PATH,
    CONFIG_PATH,
    DEFAULT_ALARM_VOLUME,
    DEFAULT_CHARGE_THRESHOLD_HIGH,
    DEFAULT_CHARGE_THRESHOLD_LOW,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
)
from voltsentry.core.decorators import singleton
from voltsentry.core.exceptions import ConfigCorruptError, ConfigError, ConfigNotFoundError
from voltsentry.core.logging_config import get_logger, log_audit
from voltsentry.core.validators import (
    validate_percent,
    validate_quiet_hours,
    validate_threshold_pair,
    validate_time_format,
)

logger = get_logger(__name__)


@dataclass
class VoltSentrySettings:
    """Application settings with strict validation."""

    # Battery thresholds
    charge_threshold_high: int = DEFAULT_CHARGE_THRESHOLD_HIGH
    charge_threshold_low: int = DEFAULT_CHARGE_THRESHOLD_LOW

    # Polling
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS

    # Quiet hours
    quiet_hours_start: str = DEFAULT_QUIET_HOURS_START
    quiet_hours_end: str = DEFAULT_QUIET_HOURS_END

    # Audio
    alarm_volume: float = DEFAULT_ALARM_VOLUME
    custom_alarm_path: Optional[str] = None

    # Startup
    start_with_os: bool = False

    # Reports
    weekly_report_enabled: bool = True
    weekly_report_time: str = "09:00"

    # Advanced
    debug_mode: bool = False
    data_collection_opt_in: bool = False
    last_known_good: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate settings on creation."""
        self.validate()

    def validate(self) -> None:
        """Validate all settings properties."""
        validate_threshold_pair(
            self.charge_threshold_high,
            self.charge_threshold_low,
        )

        if not isinstance(self.alarm_volume, (int, float)):
            raise TypeError("alarm_volume must be a float or int")
        validate_percent(int(self.alarm_volume * 100))

        validate_quiet_hours(self.quiet_hours_start, self.quiet_hours_end)
        validate_time_format(self.weekly_report_time)

        if self.poll_interval_seconds < 1:
            raise ValueError("Poll interval must be at least 1 second")

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings dataclass to dictionary."""
        data = asdict(self)
        if self.last_known_good:
            data["last_known_good"] = self.last_known_good
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoltSentrySettings":
        """Create settings from a dictionary, safely filtering unknown fields."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def update(self, **kwargs: Any) -> None:
        """Update settings with runtime validation."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.validate()
        self.last_known_good = datetime.now().isoformat()

    @property
    def threshold_gap(self) -> int:
        """Get the gap between high and low battery thresholds."""
        return self.charge_threshold_high - self.charge_threshold_low


class ConfigManager:
    """Configuration manager handling thread-safe reads, atomic writes, auto-backup, and fallback."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        backup_path: Optional[Path] = None,
    ):
        self.config_path = config_path or CONFIG_PATH
        self.backup_path = backup_path or CONFIG_BACKUP_PATH
        self._settings: Optional[VoltSentrySettings] = None
        self._dirty = False
        self._reset_notified = False
        self._lock = RLock()

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def settings(self) -> VoltSentrySettings:
        """Get current settings (loads from disk if uninitialized)."""
        with self._lock:
            if self._settings is None:
                self.load()
            return self._settings

    def load(self) -> VoltSentrySettings:
        """Load configuration with fallback chain: Primary -> Backup -> Default Settings."""
        with self._lock:
            try:
                self._settings = self._load_from_path(self.config_path)
                logger.info("Loaded config from %s", self.config_path)
                return self._settings
            except ConfigError as e:
                logger.warning("Config load failed: %s, attempting backup recovery", e)

                try:
                    self._settings = self._load_from_path(self.backup_path)
                    logger.warning("Loaded config from backup: %s", self.backup_path)
                    log_audit("WARNING", f"Config restored from backup: {self.backup_path}")
                    return self._settings
                except ConfigError:
                    logger.warning("Backup recovery failed. Resetting configuration to defaults.")
                    self._settings = VoltSentrySettings()
                    self._reset_notified = True
                    log_audit("WARNING", "Config reset to defaults (both primary and backup failed)")
                    return self._settings

    def _load_from_path(self, path: Path) -> VoltSentrySettings:
        """Load and parse config file from disk path."""
        if not path.exists():
            raise ConfigNotFoundError(f"Config file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return VoltSentrySettings.from_dict(data)
        except json.JSONDecodeError as e:
            raise ConfigCorruptError(f"Invalid JSON format in {path}: {e}") from e
        except (TypeError, ValueError) as e:
            raise ConfigError(f"Invalid config data schema in {path}: {e}") from e

    def save(self) -> None:
        """Atomically save current configuration to disk with automatic file backing."""
        with self._lock:
            if self._settings is None:
                raise ConfigError("No settings instance present to save")

            self._settings.validate()

            # Backup current active file before overwriting
            if self.config_path.exists():
                try:
                    shutil.copy2(self.config_path, self.backup_path)
                except (OSError, PermissionError) as e:
                    logger.warning("Failed to update configuration backup file: %s", e)

            # Atomic write via temporary file
            data = self._settings.to_dict()
            temp_file = self.config_path.with_suffix(".tmp")
            try:
                temp_file.write_text(
                    json.dumps(data, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                temp_file.replace(self.config_path)
                logger.info("Saved config atomically to %s", self.config_path)
                self._dirty = False
            except (OSError, PermissionError) as e:
                if temp_file.exists():
                    temp_file.unlink(missing_ok=True)
                raise ConfigError(f"Failed to save configuration: {e}") from e

    def reset_to_defaults(self, save: bool = True) -> None:
        """Reset settings state to initial default parameters."""
        with self._lock:
            self._settings = VoltSentrySettings()
            self._reset_notified = True
            log_audit("INFO", "Config reset to defaults")

            if save:
                self.save()

    def was_reset(self) -> bool:
        """Check if settings state experienced a forced fallback reset."""
        with self._lock:
            return self._reset_notified

    def get_path(self) -> Path:
        """Get path to the active configuration file."""
        return self.config_path

    def update_and_save(self, **kwargs: Any) -> None:
        """Atomically update settings and save parameters."""
        with self._lock:
            self.settings.update(**kwargs)
            self.save()

    def __repr__(self) -> str:
        return (
            f"ConfigManager(path={self.config_path}, "
            f"loaded={self._settings is not None}, "
            f"dirty={self._dirty})"
        )


# ============================================================================
# Global config singleton
# ============================================================================
@singleton
class GlobalConfig:
    """Global access wrapper for configuration management."""

    def __init__(self) -> None:
        self.manager = ConfigManager()

    @property
    def settings(self) -> VoltSentrySettings:
        return self.manager.settings

    def load(self) -> VoltSentrySettings:
        return self.manager.load()

    def save(self) -> None:
        self.manager.save()

    def reset(self) -> None:
        self.manager.reset_to_defaults()

    def was_reset(self) -> bool:
        return self.manager.was_reset()


def get_config() -> GlobalConfig:
    """Get global configuration singleton instance."""
    return GlobalConfig()