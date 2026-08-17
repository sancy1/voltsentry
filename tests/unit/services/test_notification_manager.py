"""
FILE: tests/unit/services/test_notification_manager.py
PATH: voltsentry/tests/unit/services/test_notification_manager.py
DESCRIPTION: Unit tests for Native Windows Toast Notifications and Fallback System
PHASE: 3.3 - Notification Manager
"""

from unittest.mock import MagicMock, patch

import pytest

from voltsentry.services.notification_manager import (
    Notification,
    NotificationManager,
)


class TestNotificationManager:
    """Unit tests for NotificationManager service."""

    @pytest.fixture
    def sample_notification(self):
        """Fixture providing a standard test notification."""
        return Notification(
            title="Battery Low",
            message="Battery level reached 15%. Plug in charger.",
            duration=5,
        )

    def test_notification_dataclass(self, sample_notification):
        """Test Notification dataclass instantiation and fields."""
        assert sample_notification.title == "Battery Low"
        assert sample_notification.message == "Battery level reached 15%. Plug in charger."
        assert sample_notification.duration == 5
        assert sample_notification.icon is None

    @patch("voltsentry.services.notification_manager.IS_WINDOWS", False)
    def test_check_native_available_non_windows(self):
        """Test native availability returns False on non-Windows platforms."""
        manager = NotificationManager()
        assert manager._native_available is False

    @patch("voltsentry.services.notification_manager.IS_WINDOWS", True)
    @patch("voltsentry.services.notification_manager.NotificationManager._check_windows_toast_available", return_value=True)
    def test_check_native_available_windows_success(self, mock_toast_check):
        """Test native availability returns True on Windows when windows_toasts is available."""
        manager = NotificationManager()
        assert manager._native_available is True
        mock_toast_check.assert_called_once()

    def test_set_fallback_callback(self):
        """Test registering a fallback callback."""
        manager = NotificationManager()
        callback = MagicMock()

        manager.set_fallback_callback(callback)
        assert manager._on_fallback == callback

    @patch("voltsentry.services.notification_manager.IS_WINDOWS", True)
    def test_notify_windows_toast_success(self, sample_notification):
        """Test successful notification dispatch via Windows Toast."""
        manager = NotificationManager()
        manager._native_available = True

        with patch.object(manager, "_send_windows_toast", return_value=True):
            result = manager.notify(sample_notification)
            assert result is True
            assert manager._last_notification == sample_notification

    @patch("voltsentry.services.notification_manager.IS_WINDOWS", True)
    def test_notify_windows_toast_failure_triggers_fallback(self, sample_notification):
        """Test fallback callback trigger when Windows Toast throws an exception during send."""
        manager = NotificationManager()
        manager._native_available = True

        fallback_callback = MagicMock()
        manager.set_fallback_callback(fallback_callback)

        with patch.object(manager, "_send_windows_toast", side_effect=Exception("Toast display failed")):
            result = manager.notify(sample_notification)

            assert result is True
            fallback_callback.assert_called_once_with(sample_notification)

    def test_notify_fallback_when_native_unavailable(self, sample_notification):
        """Test automatic routing to fallback callback when native notifications are unavailable."""
        manager = NotificationManager()
        manager._native_available = False

        callback = MagicMock()
        manager.set_fallback_callback(callback)

        result = manager.notify(sample_notification)

        assert result is True
        callback.assert_called_once_with(sample_notification)

    def test_fallback_without_callback(self, sample_notification):
        """Test fallback behavior when no fallback callback is registered."""
        manager = NotificationManager()
        manager._native_available = False

        result = manager.notify(sample_notification)

        assert result is False

    def test_fallback_callback_exception_handling(self, sample_notification):
        """Test error handling when fallback callback itself raises an exception."""
        manager = NotificationManager()
        manager._native_available = False

        failing_callback = MagicMock(side_effect=RuntimeError("Banner rendering failed"))
        manager.set_fallback_callback(failing_callback)

        result = manager.notify(sample_notification)

        assert result is False

    def test_get_status(self, sample_notification):
        """Test status dictionary output."""
        manager = NotificationManager()
        manager._last_notification = sample_notification

        status = manager.get_status()

        assert status["native_available"] == manager._native_available
        assert status["last_notification"] == "Battery Low"
        assert status["has_fallback"] is False

        manager.set_fallback_callback(lambda x: None)
        assert manager.get_status()["has_fallback"] is True