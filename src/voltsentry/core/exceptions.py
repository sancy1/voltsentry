# File: exceptions.py
# Path: voltsentry/src/voltsentry/core/exceptions.py
# Description: Centralized exception hierarchy and retryability classifier for VoltSentry.

from typing import Optional


class VoltSentryError(Exception):
    """Base class for all VoltSentry-raised errors."""

    def __init__(self, message: str, original_error: Optional[BaseException] = None) -> None:
        self.message = message
        self.original_error = original_error
        if original_error is not None:
            self.__cause__ = original_error
        super().__init__(message)

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message} (caused by: {type(self.original_error).__name__}: {self.original_error})"
        return self.message


class ValidationError(VoltSentryError):
    """Raised when input validation fails."""

    pass


class CircuitBreakerOpenError(VoltSentryError):
    """Raised when execution is attempted while a circuit breaker is in the OPEN state."""

    pass


# ============================================================================
# Battery Exceptions
# ============================================================================
class BatteryError(VoltSentryError):
    """Base for battery-related errors."""

    pass


class BatteryReadError(BatteryError):
    """Raised when the OS battery/power API cannot be read."""

    pass


class BatteryReportUnavailableError(BatteryError):
    """Raised when powercfg / system_profiler cannot be parsed."""

    pass


class BatterySensorUnsupportedError(BatteryError):
    """Raised when a battery sensor is not supported on this hardware."""

    pass


# ============================================================================
# Database Exceptions
# ============================================================================
class DatabaseError(VoltSentryError):
    """Raised when a DB operation fails after retries are exhausted."""

    pass


class MigrationError(DatabaseError):
    """Raised when a database migration fails."""

    pass


class EntityNotFoundError(DatabaseError):
    """Raised when an entity is not found in the database."""

    pass


# ============================================================================
# Audio/UI Exceptions
# ============================================================================
class AudioError(VoltSentryError):
    """Base for audio-related errors."""

    pass


class AudioPlaybackError(AudioError):
    """Raised when the alarm audio engine cannot play a sound."""

    pass


class AudioInitError(AudioError):
    """Raised when the audio subsystem cannot be initialized."""

    pass


class NotificationError(VoltSentryError):
    """Raised when the native OS notification API fails."""

    pass


# ============================================================================
# Calibration Exceptions
# ============================================================================
class CalibrationError(VoltSentryError):
    """Raised when the guided calibration wizard hits an invalid state."""

    pass


class CalibrationAbortedError(CalibrationError):
    """Raised when calibration is explicitly aborted by the user."""

    pass


class CalibrationTimeoutError(CalibrationError):
    """Raised when calibration exceeds maximum allowed duration."""

    pass


# ============================================================================
# Automation Exceptions
# ============================================================================
class AutomationError(VoltSentryError):
    """Base for automation-related errors."""

    pass


class AutomationHookError(AutomationError):
    """Raised when a webhook or local script hook fails."""

    pass


class HookDisabledError(AutomationHookError):
    """Raised when trying to use a disabled hook."""

    pass


# ============================================================================
# Backup/Restore Exceptions
# ============================================================================
class BackupError(VoltSentryError):
    """Base for backup/restore errors."""

    pass


class BackupRestoreError(BackupError):
    """Raised on encrypted backup/restore failures."""

    pass


class InvalidPassphraseError(BackupRestoreError):
    """Raised when the decryption passphrase is incorrect."""

    pass


class BackupCorruptError(BackupRestoreError):
    """Raised when a backup file is corrupted."""

    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================
class ConfigError(VoltSentryError):
    """Raised when configuration fails."""

    pass


class ConfigNotFoundError(ConfigError):
    """Raised when configuration file is not found."""

    pass


class ConfigCorruptError(ConfigError):
    """Raised when configuration file is corrupt."""

    pass


# ============================================================================
# Watchdog Exceptions
# ============================================================================
class WatchdogError(VoltSentryError):
    """Raised when the watchdog service fails."""

    pass


class ProcessStoppedError(WatchdogError):
    """Raised when the monitored process stops unexpectedly."""

    pass


class WatchdogRestartError(WatchdogError):
    """Raised when watchdog fails to restart the process."""

    pass


# ============================================================================
# Network Exceptions
# ============================================================================
class NetworkError(VoltSentryError):
    """Base for network-related errors."""

    pass


class FleetConnectionError(NetworkError):
    """Raised when fleet aggregator is unreachable."""

    pass


# ============================================================================
# Exception Retryability Classifier
# ============================================================================
NON_RETRYABLE_EXCEPTIONS = (
    ValidationError,
    InvalidPassphraseError,
    BackupCorruptError,
    ConfigCorruptError,
    EntityNotFoundError,
    BatterySensorUnsupportedError,
    HookDisabledError,
    CircuitBreakerOpenError,
)


def is_retryable_error(error: BaseException) -> bool:
    """Check if an error is retryable (transient) or permanent.

    Returns:
        True if the error should be retried, False if it should fail fast.
    """
    # 1. Fail fast on non-retryable domain exceptions
    if isinstance(error, NON_RETRYABLE_EXCEPTIONS):
        return False

    # 2. Database lock/busy errors are transient and retryable
    if isinstance(error, DatabaseError) and any(
        kw in str(error).lower() for kw in ("lock", "locked", "busy", "timeout")
    ):
        return True

    # 3. Network and IO connection timeouts are retryable
    if isinstance(error, (ConnectionError, TimeoutError, FleetConnectionError)):
        return True

    # 4. OS errors that are transient (e.g. temporary file lock or resource busy)
    if isinstance(error, OSError) and getattr(error, "errno", None) in (11, 35, 36):  # EAGAIN, EWOULDBLOCK
        return True

    # Default: do not retry unknown or general errors
    return False