# File: logging_config.py
# Path: voltsentry/src/voltsentry/core/logging_config.py
# Description: Unified, thread-safe logging setup and audit logger for VoltSentry.

import datetime
import logging
import logging.handlers
import sys
import tempfile
from pathlib import Path
from threading import Lock
from typing import Dict, Optional
from typing import Any

from voltsentry.core.constants import (
    AUDIT_LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    LOGS_DIR,
)

# Global registries and locks
_loggers: Dict[str, logging.Logger] = {}
_is_production: bool = False
_logger_lock = Lock()


def setup_logging(
    log_dir: Optional[Path] = None,
    is_production: bool = False,
    verbose: bool = False,
) -> None:
    """Set up the unified logging system.

    Args:
        log_dir: Custom log directory (defaults to LOGS_DIR)
        is_production: If True, disables console logging (reduces noise)
        verbose: If True, enables DEBUG logging globally
    """
    global _is_production
    _is_production = is_production

    # Determine log directory
    target_dir = log_dir or LOGS_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        target_dir = Path(tempfile.gettempdir()) / "voltsentry_logs"
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"WARNING: Cannot write to log dir. Falling back to {target_dir}", file=sys.stderr)

    log_file = target_dir / LOG_FILE.name
    audit_log_file = target_dir / AUDIT_LOG_FILE.name

    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    audit_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        LOG_DATE_FORMAT,
    )

    # --- Main Root Logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # File handler
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        print(f"ERROR: Failed to create file logger at {log_file}: {e}", file=sys.stderr)

    # Console handler (only when not in production)
    if not is_production:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # --- Audit Logger ---
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.WARNING)
    audit_logger.propagate = False

    for handler in list(audit_logger.handlers):
        audit_logger.removeHandler(handler)

    try:
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=5,
            encoding="utf-8",
        )
        audit_handler.setLevel(logging.WARNING)
        audit_handler.setFormatter(audit_formatter)
        audit_logger.addHandler(audit_handler)
    except (OSError, PermissionError) as e:
        print(f"ERROR: Failed to create audit logger at {audit_log_file}: {e}", file=sys.stderr)

    # Log startup summary
    root_logger.info("=" * 60)
    root_logger.info("VoltSentry logging system initialized")
    root_logger.info("Log file: %s", log_file)
    root_logger.info("Audit log file: %s", audit_log_file)
    root_logger.info("Production mode: %s", is_production)
    root_logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with standard configuration."""
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = logging.getLogger(name)
        return _loggers[name]


def log_audit(level: str, message: str) -> None:
    """Log to the audit log (WARNING+ events)."""
    audit_logger = logging.getLogger("audit")
    log_method = getattr(audit_logger, level.lower(), audit_logger.warning)
    log_method(message)


def _log_to_audit(level: str, message: str, audit_file: Path, formatter: logging.Formatter) -> None:
    """Internal: write directly to audit log file."""
    try:
        timestamp = datetime.datetime.now().strftime(LOG_DATE_FORMAT)
        log_line = f"{timestamp} | {level:<8} | {message}\n"

        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass


def get_log_level() -> int:
    """Get the current root log level."""
    return logging.getLogger().getEffectiveLevel()


def set_log_level(level: int) -> None:
    """Set the global log level."""
    logging.getLogger().setLevel(level)


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(self, level: int) -> None:
        self.level = level
        self.original_level: Optional[int] = None

    def __enter__(self) -> "LogContext":
        self.original_level = get_log_level()
        set_log_level(self.level)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.original_level is not None:
            set_log_level(self.original_level)
            