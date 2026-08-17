# File: validators.py
# Path: voltsentry/src/voltsentry/core/validators.py
# Description: Reusable, DRY validation functions for inputs, thresholds, files, and configurations.

import os
import re
from pathlib import Path
from typing import Any, Optional, Union

from voltsentry.core.constants import MAX_CUSTOM_SOUND_SIZE, SUPPORTED_AUDIO_EXTENSIONS
from voltsentry.core.exceptions import ValidationError

# ============================================================================
# Battery Validators
# ============================================================================
def validate_percent(value: int) -> int:
    """Validate a battery percentage (0-100)."""
    if type(value) is bool or not isinstance(value, int):
        raise ValidationError(f"Percent must be integer, got {type(value).__name__}")
    if not 0 <= value <= 100:
        raise ValidationError(f"Percent must be 0-100, got {value}")
    return value


def validate_threshold_pair(high: int, low: int, min_gap: int = 10) -> tuple[int, int]:
    """Validate charge threshold pair.

    Args:
        high: Charge threshold (stop charging)
        low: Discharge threshold (start charging)
        min_gap: Minimum gap between thresholds

    Returns:
        Validated (high, low) tuple

    Raises:
        ValidationError: If thresholds invalid
    """
    high = validate_percent(high)
    low = validate_percent(low)

    if high <= low:
        raise ValidationError(
            f"High threshold ({high}%) must be greater than low threshold ({low}%)"
        )

    if high - low < min_gap:
        raise ValidationError(
            f"Threshold gap must be at least {min_gap}% (currently {high - low}%)"
        )

    return high, low


# ============================================================================
# Time Validators
# ============================================================================
def validate_time_format(
    time_str: str,
    pattern: str = r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
) -> str:
    """Validate HH:MM time format.

    Args:
        time_str: Time string to validate
        pattern: Regex pattern for validation

    Returns:
        Validated time string

    Raises:
        ValidationError: If format invalid
    """
    if not isinstance(time_str, str):
        raise ValidationError(f"Time must be string, got {type(time_str).__name__}")

    if not re.match(pattern, time_str):
        raise ValidationError(f"Invalid time format: '{time_str}' (expected HH:MM)")

    return time_str


def validate_quiet_hours(start: str, end: str) -> tuple[str, str]:
    """Validate quiet hours start/end times."""
    start = validate_time_format(start)
    end = validate_time_format(end)

    if start == end:
        raise ValidationError("Quiet hours start and end times cannot be identical")

    return start, end


# ============================================================================
# File Validators
# ============================================================================
def validate_file_exists(path: Union[str, Path]) -> Path:
    """Validate that a file exists and is a file."""
    path_obj = Path(path)

    if not path_obj.exists():
        raise ValidationError(f"File does not exist: {path_obj}")

    if not path_obj.is_file():
        raise ValidationError(f"Path is not a regular file: {path_obj}")

    return path_obj


def validate_audio_file(path: Union[str, Path]) -> Path:
    """Validate an audio file for alarm use.

    Checks:
    - File exists
    - File extension is supported
    - File size <= MAX_CUSTOM_SOUND_SIZE
    - File has valid audio header
    """
    path_obj = validate_file_exists(path)

    # Check extension
    if path_obj.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValidationError(
            f"Unsupported audio format: {path_obj.suffix}. "
            f"Supported: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}"
        )

    # Check size
    size = os.path.getsize(path_obj)
    if size > MAX_CUSTOM_SOUND_SIZE:
        max_mb = MAX_CUSTOM_SOUND_SIZE / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise ValidationError(
            f"File too large: {actual_mb:.1f} MB (max {max_mb:.0f} MB)"
        )

    # Basic audio header check (first 4 bytes)
    with open(path_obj, "rb") as f:
        header = f.read(4)

    if len(header) < 2:
        raise ValidationError("Audio file is empty or corrupted")

    # Magic numbers for audio formats
    valid_headers = (
        b"RIFF",  # WAV
        b"RIFX",  # Big-endian WAV
        b"ID3",   # MP3 with ID3 tag
        b"OggS",  # OGG container
    )

    if any(header.startswith(h) for h in valid_headers):
        return path_obj

    # Check raw MP3 frame sync bytes (11 bits set: 0xFF, 0xE0 mask)
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return path_obj

    raise ValidationError("Invalid or corrupted audio file signature")


def validate_config_json(data: dict[str, Any]) -> dict[str, Any]:
    """Validate configuration JSON structure."""
    from voltsentry.core.config import VoltSentrySettings

    try:
        settings = VoltSentrySettings(**data)
        return settings.to_dict()
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid configuration data: {e}") from e


# ============================================================================
# String & Primitive Validators
# ============================================================================
def validate_not_empty(value: str, field_name: str = "Value") -> str:
    """Validate that a string is not empty or whitespace only."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be string, got {type(value).__name__}")

    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty")

    return stripped


def validate_positive_int(value: int, field_name: str = "Value") -> int:
    """Validate a positive integer (> 0)."""
    if type(value) is bool or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be integer, got {type(value).__name__}")

    if value <= 0:
        raise ValidationError(f"{field_name} must be positive (> 0), got {value}")

    return value


# ============================================================================
# Data Class & Entity Validators
# ============================================================================
def validate_entity(entity: Any, required_fields: list[str]) -> None:
    """Validate that an entity has all required fields set and non-None."""
    for field in required_fields:
        if not hasattr(entity, field):
            raise ValidationError(f"Entity missing required attribute: {field}")

        value = getattr(entity, field)
        if value is None:
            raise ValidationError(f"Entity field cannot be None: {field}")