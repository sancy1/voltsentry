"""
FILE: src/voltsentry/services/alarm_manager.py
PATH: voltsentry/src/voltsentry/services/alarm_manager.py
DESCRIPTION: Simple MP3 alarm sound system with fallback
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from ..core.constants import FULL_CHARGE_SOUND, LOW_BATTERY_SOUND
from ..core.logging_config import get_logger, log_audit

logger = get_logger(__name__)


class AlarmType(Enum):
    """Types of alarms."""
    NONE = "none"
    FULL_CHARGE = "full_charge"
    LOW_BATTERY = "low_battery"
    CRITICAL_LOW = "critical_low"


@dataclass
class AlarmProfile:
    """Configuration for an alarm sound."""
    name: str
    sound_path: Path
    loop: bool = True
    priority: int = 0
    description: str = ""


FULL_CHARGE_PROFILE = AlarmProfile(
    name="full_charge",
    sound_path=FULL_CHARGE_SOUND,
    loop=True,
    priority=1,
    description="Calm alarm sound",
)

LOW_BATTERY_PROFILE = AlarmProfile(
    name="low_battery",
    sound_path=LOW_BATTERY_SOUND,
    loop=True,
    priority=2,
    description="Urgent alarm sound",
)

ALARM_PROFILES = {
    AlarmType.FULL_CHARGE: FULL_CHARGE_PROFILE,
    AlarmType.LOW_BATTERY: LOW_BATTERY_PROFILE,
    AlarmType.CRITICAL_LOW: LOW_BATTERY_PROFILE,
}


class AlarmManager:
    """Simple MP3 alarm sound system."""

    def __init__(self, volume: float = 0.8):
        self.volume = max(0.0, min(1.0, volume))
        self._active_alarm: Optional[AlarmType] = None
        self._active_profile: Optional[AlarmProfile] = None
        self._lock = threading.Lock()
        self._visual_only_callback: Optional[Callable[[AlarmType], None]] = None
        self._is_playing = False
        self._pygame_available = False

        # Initialize pygame
        self._init_pygame()

        logger.info("AlarmManager initialized: volume=%.2f, pygame=%s", 
                   self.volume, self._pygame_available)

    def _init_pygame(self) -> None:
        """Initialize pygame mixer."""
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._pygame_available = True
            logger.info("✅ Pygame initialized - MP3 playback ready")
        except ImportError:
            logger.warning("⚠️ Pygame not installed! Install: pip install pygame")
            self._pygame_available = False
        except Exception as e:
            logger.warning("⚠️ Pygame init failed: %s", e)
            self._pygame_available = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def active_alarm(self) -> Optional[AlarmType]:
        return self._active_alarm

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        logger.info("Alarm volume set to %.2f", self.volume)

    def set_visual_only_callback(self, callback: Callable[[AlarmType], None]) -> None:
        self._visual_only_callback = callback

    def play(self, alarm_type: AlarmType, custom_sound_path: Optional[Path] = None) -> bool:
        if alarm_type == AlarmType.NONE:
            self.stop()
            return False

        with self._lock:
            # Priority check
            if self._active_alarm is not None:
                current_priority = ALARM_PROFILES.get(self._active_alarm, AlarmProfile("", Path(), priority=0)).priority
                new_priority = ALARM_PROFILES.get(alarm_type, AlarmProfile("", Path(), priority=0)).priority
                if alarm_type == AlarmType.CRITICAL_LOW:
                    logger.info("CRITICAL_LOW overriding current")
                elif new_priority < current_priority:
                    return False

            profile = ALARM_PROFILES.get(alarm_type)
            if profile is None:
                logger.error("Unknown alarm type: %s", alarm_type)
                return False

            sound_path = custom_sound_path if custom_sound_path and custom_sound_path.exists() else profile.sound_path
            self._active_alarm = alarm_type
            self._active_profile = profile

            logger.info("🔊 Playing alarm: %s", alarm_type.value)
            logger.info("   Sound file: %s (exists: %s)", sound_path, sound_path.exists())

            # ===== PLAY MP3 DIRECTLY =====
            success = False

            # Try pygame (supports MP3 directly!)
            if self._pygame_available:
                success = self._play_mp3(sound_path)

            # Fallback to Windows beep
            if not success:
                success = self._fallback_beep()

            # Visual-only fallback
            if not success:
                success = self._visual_only_fallback()

            if success:
                self._is_playing = True
                logger.info("✅ Alarm playing: %s", alarm_type.value)
                log_audit("INFO", f"Alarm triggered: {alarm_type.value}")
            else:
                logger.error("❌ All alarm playback failed for: %s", alarm_type.value)

            return success

    def _play_mp3(self, sound_path: Path) -> bool:
        """Play MP3 (or any audio) using pygame."""
        try:
            import pygame

            if not sound_path.exists():
                logger.error("❌ Sound file not found: %s", sound_path)
                return False

            # pygame.mixer.music supports MP3, WAV, OGG, etc.
            pygame.mixer.music.load(str(sound_path))
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(loops=-1)  # Loop indefinitely

            # Verify it's playing
            if pygame.mixer.music.get_busy():
                logger.debug("✅ Pygame playing: %s", sound_path.name)
                return True
            else:
                logger.warning("⚠️ Pygame loaded but not playing")
                return False

        except pygame.error as e:
            error_msg = str(e).lower()
            if "unknown wave format" in error_msg:
                logger.error("❌ Unsupported audio format. MP3/WAV recommended.")
                logger.info("💡 Convert your file to MP3 or WAV format.")
            else:
                logger.error("❌ Pygame error: %s", e)
            return False
        except Exception as e:
            logger.error("❌ Playback failed: %s", e)
            return False

    def _fallback_beep(self) -> bool:
        """Fallback to Windows beep."""
        try:
            import winsound
            winsound.Beep(800, 400)
            time.sleep(0.1)
            winsound.Beep(1000, 400)
            logger.debug("✅ Windows beep played")
            return True
        except Exception as e:
            logger.debug("Beep failed: %s", e)
            return False

    def _visual_only_fallback(self) -> bool:
        """Visual-only fallback."""
        if self._visual_only_callback and self._active_alarm:
            try:
                self._visual_only_callback(self._active_alarm)
                return True
            except Exception as e:
                logger.error("Visual callback failed: %s", e)
        return False

    def stop(self) -> None:
        """Stop the currently playing alarm."""
        with self._lock:
            if not self._is_playing:
                return

            self._is_playing = False

            try:
                import pygame
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                logger.debug("Alarm stopped")
            except:
                pass

            self._active_alarm = None
            self._active_profile = None
            logger.info("🔕 Alarm stopped")

    def is_audio_available(self) -> bool:
        return self._pygame_available

    def get_status(self) -> dict:
        return {
            "is_playing": self._is_playing,
            "active_alarm": self._active_alarm.value if self._active_alarm else None,
            "pygame_available": self._pygame_available,
            "volume": self.volume,
        }