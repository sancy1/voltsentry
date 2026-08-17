# """
# FILE: src/voltsentry/core/constants.py
# PATH: voltsentry/src/voltsentry/core/constants.py
# DESCRIPTION: Application-wide constants, platform-specific path definitions, and environment variable loading.
# """

# import os
# import platform
# import sys
# from pathlib import Path
# from dotenv import load_dotenv

# # ============================================================================
# # Centralized .env Loading (Project Root)
# # ============================================================================
# ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
# ENV_FILE = ROOT_DIR / ".env"

# if ENV_FILE.exists():
#     load_dotenv(dotenv_path=ENV_FILE)

# # ============================================================================
# # Application Identity
# # ============================================================================
# APP_NAME = os.getenv("APP_NAME", "VoltSentry")
# APP_ID = os.getenv("APP_ID", "com.voltsentry.app")
# APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
# APP_ENV = os.getenv("APP_ENV", "development")
# DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# # ============================================================================
# # Windows App User Model ID (AUMID) Registration
# # Forces Windows Action Center to allow toast notifications to display
# # above the system tray even during Focus Assist/Do Not Disturb.
# # ============================================================================
# IS_WINDOWS = sys.platform == "win32"
# IS_MACOS = sys.platform == "darwin"
# IS_LINUX = sys.platform.startswith("linux")

# if IS_WINDOWS:
#     try:
#         import ctypes

#         # Set explicit AUMID for notification routing in Windows shell
#         ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
#     except Exception:
#         pass


# # ============================================================================
# # Paths - Platform-specific with .env Override Support
# # ============================================================================
# def get_app_data_dir() -> Path:
#     """Get the platform-appropriate application data directory or .env override."""
#     env_data_dir = os.getenv("VOLTSENTRY_DATA_DIR")
#     if env_data_dir and env_data_dir.strip():
#         path = Path(env_data_dir.strip())
#     elif sys.platform == "win32":
#         path = Path.home() / "AppData" / "Local" / APP_NAME
#     elif sys.platform == "darwin":
#         path = Path.home() / "Library" / "Application Support" / APP_NAME
#     else:  # Linux and others
#         path = Path.home() / ".config" / APP_NAME.lower()

#     path.mkdir(parents=True, exist_ok=True)
#     return path


# def get_logs_dir() -> Path:
#     """Get the platform-appropriate logs directory."""
#     path = get_app_data_dir() / "logs"
#     path.mkdir(parents=True, exist_ok=True)
#     return path


# def get_resources_dir() -> Path:
#     """Get the resources directory (icons, sounds)."""
#     return Path(__file__).resolve().parent.parent / "resources"


# DATA_DIR = get_app_data_dir()
# LOGS_DIR = get_logs_dir()
# RESOURCES_DIR = get_resources_dir()

# # ============================================================================
# # Database
# # ============================================================================
# CUSTOM_DB_PATH = os.getenv("DB_PATH")
# if CUSTOM_DB_PATH and CUSTOM_DB_PATH.strip():
#     DB_PATH = Path(CUSTOM_DB_PATH.strip())
# else:
#     DB_PATH = DATA_DIR / "voltsentry.db"

# DB_PENDING_QUEUE = DATA_DIR / "pending_writes.jsonl"
# DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))
# DB_BUSY_TIMEOUT = int(os.getenv("DB_BUSY_TIMEOUT", "5000"))
# DB_CACHE_SIZE = int(os.getenv("DB_CACHE_SIZE", "-20000"))

# # ============================================================================
# # Configuration
# # ============================================================================
# CONFIG_PATH = DATA_DIR / "config.json"
# CONFIG_BACKUP_PATH = DATA_DIR / "config.json.bak"

# # ============================================================================
# # Battery Defaults & Thresholds
# # ============================================================================
# DEFAULT_CHARGE_THRESHOLD_HIGH = int(os.getenv("BATTERY_FULL_CHARGE", "85"))
# DEFAULT_CHARGE_THRESHOLD_LOW = int(os.getenv("BATTERY_LOW", "20"))
# DEFAULT_CHARGE_THRESHOLD_CRITICAL = int(os.getenv("BATTERY_CRITICAL_LOW", "15"))
# DEFAULT_POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
# DEFAULT_ALARM_VOLUME = float(os.getenv("DEFAULT_ALARM_VOLUME", "0.8"))
# DEFAULT_QUIET_HOURS_START = os.getenv("DEFAULT_QUIET_HOURS_START", "22:00")
# DEFAULT_QUIET_HOURS_END = os.getenv("DEFAULT_QUIET_HOURS_END", "07:00")

# # ============================================================================
# # Logging
# # ============================================================================
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# LOG_FILE = LOGS_DIR / "voltsentry.log"
# AUDIT_LOG_FILE = LOGS_DIR / "audit.log"
# LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
# LOG_BACKUP_COUNT = 5
# LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
# LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# # ============================================================================
# # Battery Report
# # ============================================================================
# BATTERY_REPORT_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours
# BATTERY_REPORT_PATH = DATA_DIR / "battery_report.xml"

# # ============================================================================
# # Alarm System - MP3 Support
# # ============================================================================
# FULL_CHARGE_SOUND = RESOURCES_DIR / "sounds" / "alarm_full_charge.mp3"
# LOW_BATTERY_SOUND = RESOURCES_DIR / "sounds" / "alarm_low_battery.mp3"
# MAX_CUSTOM_SOUND_SIZE = 5 * 1024 * 1024  # 5 MB
# SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg"}
# SNOOZE_DURATION_MINUTES = int(os.getenv("SNOOZE_DURATION_MINUTES", "15"))
# WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))

# # ============================================================================
# # Watchdog
# # ============================================================================
# WATCHDOG_HEARTBEAT_TIMEOUT = int(os.getenv("WATCHDOG_HEARTBEAT_TIMEOUT", "30"))
# WATCHDOG_CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "15"))
# WATCHDOG_MAX_RESTARTS = 3

# # ============================================================================
# # Hysteresis
# # ============================================================================
# HYSTERESIS_MARGIN = 3  # percent

# # ============================================================================
# # Circuit Breaker & Retries
# # ============================================================================
# CIRCUIT_BREAKER_FAILURE_LIMIT = 5
# DEFAULT_RETRY_ATTEMPTS = 3
# DEFAULT_RETRY_MAX_WAIT = 5  # seconds
# DEFAULT_RETRY_MULTIPLIER = 0.5

# # ============================================================================
# # Platform Details
# # ============================================================================
# IS_64_BIT = sys.maxsize > 2**32
# PLATFORM_NAME = platform.system()
# PLATFORM_RELEASE = platform.release()
# PLATFORM_VERSION = platform.version()

# # ============================================================================
# # UI Constants
# # ============================================================================
# TRAY_ICON_COLORS = {
#     "green": (60, 100),   # Healthy
#     "yellow": (20, 59),   # Moderate
#     "red": (0, 19),       # Critical
# }
# TRAY_ICON_SIZE = 32  # pixels

# # ============================================================================
# # Health Score Ranges
# # ============================================================================
# HEALTH_EXCELLENT = 90
# HEALTH_GOOD = 80
# HEALTH_FAIR = 60
# HEALTH_POOR = 40

# # ============================================================================
# # Calibration
# # ============================================================================
# CALIBRATION_MAX_DURATION = 24 * 60 * 60  # 24 hours

# # ============================================================================
# # Export / Backup
# # ============================================================================
# EXPORT_FILE_EXTENSION = ".vsbak"  # VoltSentry backup
# EXPORT_SALT_LENGTH = 32  # bytes
# EXPORT_KEY_LENGTH = 32  # bytes (256-bit AES)

# # ============================================================================
# # Fleet View (Enterprise)
# # ============================================================================
# FLEET_REPORT_INTERVAL = 60 * 60  # 1 hour
# FLEET_STALE_THRESHOLD = 24 * 60 * 60  # 24 hours
# DEFAULT_AGGREGATOR_PORT = int(os.getenv("DEFAULT_AGGREGATOR_PORT", "8080"))
















































"""
FILE: src/voltsentry/core/constants.py
PATH: voltsentry/src/voltsentry/core/constants.py
DESCRIPTION: Application-wide constants, platform-specific path definitions, and environment variable loading.
"""

import os
import platform
import sys
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# Centralized .env Loading (Project Root)
# ============================================================================
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

# ============================================================================
# Application Identity
# ============================================================================
APP_NAME = os.getenv("APP_NAME", "VoltSentry")
APP_ID = os.getenv("APP_ID", "com.voltsentry.app")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# ============================================================================
# Windows App User Model ID (AUMID) Registration
# Forces Windows Action Center to allow toast notifications to display
# above the system tray even during Focus Assist/Do Not Disturb.
# ============================================================================
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    try:
        import ctypes

        # Set explicit AUMID for notification routing in Windows shell
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

# ============================================================================
# Dynamic Path Helpers for Development and Packaged Executable
# ============================================================================
def get_app_data_dir() -> Path:
    """
    Get the application data directory for user-specific files.
    Works for normal development AND PyInstaller packaged executables.
    
    Returns:
        Path to app data folder (e.g., %LOCALAPPDATA%\VoltSentry)
    """
    if sys.platform == "win32":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    
    app_data = base / APP_NAME
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs = get_app_data_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def get_resources_dir() -> Path:
    """
    Get the resources directory (icons, sounds).
    Works for normal development AND PyInstaller packaged executables.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as a compiled PyInstaller executable
        base_path = Path(sys._MEIPASS)
    else:
        # Running in normal Python development environment
        base_path = Path(__file__).resolve().parent.parent
    
    return base_path / "resources"


# ============================================================================
# Application Data & Logs Directories
# ============================================================================
DATA_DIR = get_app_data_dir()
LOGS_DIR = get_logs_dir()
RESOURCES_DIR = get_resources_dir()

# ============================================================================
# Database
# ============================================================================
CUSTOM_DB_PATH = os.getenv("DB_PATH")
if CUSTOM_DB_PATH and CUSTOM_DB_PATH.strip():
    DB_PATH = Path(CUSTOM_DB_PATH.strip())
else:
    DB_PATH = DATA_DIR / "voltsentry.db"

DB_PENDING_QUEUE = DATA_DIR / "pending_writes.jsonl"
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))
DB_BUSY_TIMEOUT = int(os.getenv("DB_BUSY_TIMEOUT", "5000"))
DB_CACHE_SIZE = int(os.getenv("DB_CACHE_SIZE", "-20000"))

# ============================================================================
# Configuration
# ============================================================================
CONFIG_PATH = DATA_DIR / "config.json"
CONFIG_BACKUP_PATH = DATA_DIR / "config.json.bak"

# ============================================================================
# Battery Defaults & Thresholds
# ============================================================================
DEFAULT_CHARGE_THRESHOLD_HIGH = int(os.getenv("BATTERY_FULL_CHARGE", "85"))
DEFAULT_CHARGE_THRESHOLD_LOW = int(os.getenv("BATTERY_LOW", "20"))
DEFAULT_CHARGE_THRESHOLD_CRITICAL = int(os.getenv("BATTERY_CRITICAL_LOW", "15"))
DEFAULT_POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
DEFAULT_ALARM_VOLUME = float(os.getenv("DEFAULT_ALARM_VOLUME", "0.8"))
DEFAULT_QUIET_HOURS_START = os.getenv("DEFAULT_QUIET_HOURS_START", "22:00")
DEFAULT_QUIET_HOURS_END = os.getenv("DEFAULT_QUIET_HOURS_END", "07:00")

# ============================================================================
# Logging
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "voltsentry.log"
AUDIT_LOG_FILE = LOGS_DIR / "audit.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# Battery Report
# ============================================================================
BATTERY_REPORT_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours
BATTERY_REPORT_PATH = DATA_DIR / "battery_report.xml"

# ============================================================================
# Alarm System - MP3 Support
# ============================================================================
FULL_CHARGE_SOUND = RESOURCES_DIR / "sounds" / "alarm_full_charge.mp3"
LOW_BATTERY_SOUND = RESOURCES_DIR / "sounds" / "alarm_low_battery.mp3"
MAX_CUSTOM_SOUND_SIZE = 5 * 1024 * 1024  # 5 MB
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg"}
SNOOZE_DURATION_MINUTES = int(os.getenv("SNOOZE_DURATION_MINUTES", "15"))
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))

# ============================================================================
# Watchdog
# ============================================================================
WATCHDOG_HEARTBEAT_TIMEOUT = int(os.getenv("WATCHDOG_HEARTBEAT_TIMEOUT", "30"))
WATCHDOG_CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "15"))
WATCHDOG_MAX_RESTARTS = 3

# ============================================================================
# Hysteresis
# ============================================================================
HYSTERESIS_MARGIN = 3  # percent

# ============================================================================
# Circuit Breaker & Retries
# ============================================================================
CIRCUIT_BREAKER_FAILURE_LIMIT = 5
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_MAX_WAIT = 5  # seconds
DEFAULT_RETRY_MULTIPLIER = 0.5

# ============================================================================
# Platform Details
# ============================================================================
IS_64_BIT = sys.maxsize > 2**32
PLATFORM_NAME = platform.system()
PLATFORM_RELEASE = platform.release()
PLATFORM_VERSION = platform.version()

# ============================================================================
# UI Constants
# ============================================================================
TRAY_ICON_COLORS = {
    "green": (60, 100),   # Healthy
    "yellow": (20, 59),   # Moderate
    "red": (0, 19),       # Critical
}
TRAY_ICON_SIZE = 32  # pixels

# ============================================================================
# Health Score Ranges
# ============================================================================
HEALTH_EXCELLENT = 90
HEALTH_GOOD = 80
HEALTH_FAIR = 60
HEALTH_POOR = 40

# ============================================================================
# Calibration
# ============================================================================
CALIBRATION_MAX_DURATION = 24 * 60 * 60  # 24 hours

# ============================================================================
# Export / Backup
# ============================================================================
EXPORT_FILE_EXTENSION = ".vsbak"  # VoltSentry backup
EXPORT_SALT_LENGTH = 32  # bytes
EXPORT_KEY_LENGTH = 32  # bytes (256-bit AES)

# ============================================================================
# Fleet View (Enterprise)
# ============================================================================
FLEET_REPORT_INTERVAL = 60 * 60  # 1 hour
FLEET_STALE_THRESHOLD = 24 * 60 * 60  # 24 hours
DEFAULT_AGGREGATOR_PORT = int(os.getenv("DEFAULT_AGGREGATOR_PORT", "8080"))