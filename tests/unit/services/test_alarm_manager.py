"""
FILE: tests/unit/services/test_alarm_manager.py
PATH: voltsentry/tests/unit/services/test_alarm_manager.py
DESCRIPTION: Unit tests for Dual Alarm Sound System (AlarmManager)
PHASE: 3.2 - Dual Alarm Sound System
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voltsentry.services.alarm_manager import (
    ALARM_PROFILES,
    AlarmManager,
    AlarmProfile,
    AlarmType,
)


class TestAlarmProfileAndTypes:
    """Tests for AlarmType enum and AlarmProfile dataclasses."""

    def test_alarm_profiles_mapping(self):
        """Verify pre-defined alarm profiles are correctly configured."""
        assert AlarmType.FULL_CHARGE in ALARM_PROFILES
        assert AlarmType.LOW_BATTERY in ALARM_PROFILES
        assert AlarmType.CRITICAL_LOW in ALARM_PROFILES

        full_profile = ALARM_PROFILES[AlarmType.FULL_CHARGE]
        assert full_profile.name == "full_charge"
        assert full_profile.priority == 1

        low_profile = ALARM_PROFILES[AlarmType.LOW_BATTERY]
        assert low_profile.name == "low_battery"
        assert low_profile.priority == 2

        critical_profile = ALARM_PROFILES[AlarmType.CRITICAL_LOW]
        assert critical_profile.priority == 2


class TestAlarmManager:
    """Unit tests for AlarmManager service."""

    @pytest.fixture
    def mock_pygame_mixer(self):
        """Mock pygame.mixer module to prevent actual audio hardware access."""
        with patch("voltsentry.services.alarm_manager.pygame.mixer") as mock_mixer:
            mock_mixer.init.return_value = None
            mock_mixer.music = MagicMock()
            yield mock_mixer

    @pytest.fixture
    def alarm_manager(self, mock_pygame_mixer):
        """Fixture for an AlarmManager instance with mocked pygame."""
        return AlarmManager(volume=0.7)

    def test_initialization_success(self, alarm_manager, mock_pygame_mixer):
        """Test successful initialization of pygame mixer."""
        mock_pygame_mixer.init.assert_called_once_with(
            frequency=44100, size=-16, channels=2, buffer=512
        )
        assert alarm_manager.is_audio_available() is True
        assert alarm_manager.is_playing is False
        assert alarm_manager.active_alarm is None
        assert alarm_manager.volume == 0.7

    @patch("voltsentry.services.alarm_manager.pygame.mixer.init")
    def test_initialization_pygame_failure(self, mock_init):
        """Test initialization fallback when pygame init raises pygame.error."""
        import pygame

        mock_init.side_effect = pygame.error("No audio device")
        manager = AlarmManager(volume=0.5)

        assert manager.is_audio_available() is False
        assert manager.is_playing is False

    def test_set_volume(self, alarm_manager, mock_pygame_mixer):
        """Test volume setting and clamping."""
        alarm_manager.set_volume(0.5)
        assert alarm_manager.volume == 0.5

        # Clamping test
        alarm_manager.set_volume(1.5)
        assert alarm_manager.volume == 1.0

        alarm_manager.set_volume(-0.5)
        assert alarm_manager.volume == 0.0

    @patch("voltsentry.services.alarm_manager.Path.exists", return_value=True)
    def test_play_success(self, mock_exists, alarm_manager, mock_pygame_mixer):
        """Test playing a valid alarm via pygame."""
        result = alarm_manager.play(AlarmType.FULL_CHARGE)

        assert result is True
        assert alarm_manager.is_playing is True
        assert alarm_manager.active_alarm == AlarmType.FULL_CHARGE
        mock_pygame_mixer.music.load.assert_called_once()
        mock_pygame_mixer.music.set_volume.assert_called_once_with(0.7)
        mock_pygame_mixer.music.play.assert_called_once_with(loops=-1)

    def test_play_none_stops_alarm(self, alarm_manager):
        """Test that playing AlarmType.NONE stops any active alarm."""
        alarm_manager._is_playing = True
        alarm_manager._active_alarm = AlarmType.FULL_CHARGE

        result = alarm_manager.play(AlarmType.NONE)

        assert result is False
        assert alarm_manager.is_playing is False
        assert alarm_manager.active_alarm is None

    @patch("voltsentry.services.alarm_manager.Path.exists", return_value=True)
    def test_alarm_priority_override(self, mock_exists, alarm_manager):
        """Test priority hierarchy: lower priority alarms cannot override higher priority ones."""
        # Start FULL_CHARGE (Priority 1)
        alarm_manager.play(AlarmType.FULL_CHARGE)
        assert alarm_manager.active_alarm == AlarmType.FULL_CHARGE

        # Attempt to trigger LOW_BATTERY (Priority 2) -> Should override Priority 1
        result = alarm_manager.play(AlarmType.LOW_BATTERY)
        assert result is True
        assert alarm_manager.active_alarm == AlarmType.LOW_BATTERY

        # Attempt to trigger FULL_CHARGE (Priority 1) -> Should be ignored
        result_lower = alarm_manager.play(AlarmType.FULL_CHARGE)
        assert result_lower is False
        assert alarm_manager.active_alarm == AlarmType.LOW_BATTERY

    @patch("voltsentry.services.alarm_manager.Path.exists", return_value=True)
    def test_critical_low_always_overrides(self, mock_exists, alarm_manager):
        """Test that CRITICAL_LOW always overrides active alarms."""
        alarm_manager.play(AlarmType.LOW_BATTERY)
        assert alarm_manager.active_alarm == AlarmType.LOW_BATTERY

        result = alarm_manager.play(AlarmType.CRITICAL_LOW)
        assert result is True
        assert alarm_manager.active_alarm == AlarmType.CRITICAL_LOW

    def test_fallback_to_winsound(self, mock_pygame_mixer):
        """Test fallback to OS winsound when pygame fails/is unavailable."""
        manager = AlarmManager()
        manager._audio_ok = False  # Simulate pygame failure

        mock_winsound = MagicMock()

        with patch("sys.platform", "win32"), patch.dict("sys.modules", {"winsound": mock_winsound}):
            result = manager.play(AlarmType.LOW_BATTERY)

            assert result is True
            mock_winsound.MessageBeep.assert_called_once_with(0x00000030)
            assert manager.is_playing is True

    def test_fallback_to_visual_only(self, mock_pygame_mixer):
        """Test final fallback to visual-only callback when audio and OS beeps are unavailable."""
        manager = AlarmManager()
        manager._audio_ok = False

        visual_callback = MagicMock()
        manager.set_visual_only_callback(visual_callback)

        with patch("sys.platform", "linux"), patch.dict("sys.modules", {"winsound": None}):
            result = manager.play(AlarmType.LOW_BATTERY)

            assert result is True
            visual_callback.assert_called_once_with(AlarmType.LOW_BATTERY)
            assert manager.is_playing is True

    @patch("voltsentry.services.alarm_manager.Path.exists", return_value=True)
    def test_stop_alarm(self, mock_exists, alarm_manager, mock_pygame_mixer):
        """Test stopping active playback."""
        alarm_manager.play(AlarmType.FULL_CHARGE)
        assert alarm_manager.is_playing is True

        alarm_manager.stop()

        assert alarm_manager.is_playing is False
        assert alarm_manager.active_alarm is None
        mock_pygame_mixer.music.stop.assert_called_once()

    def test_get_status(self, alarm_manager):
        """Test status dictionary output."""
        status = alarm_manager.get_status()

        assert status["is_playing"] is False
        assert status["active_alarm"] is None
        assert status["audio_ok"] is True
        assert status["pygame_initialized"] is True
        assert status["volume"] == 0.7