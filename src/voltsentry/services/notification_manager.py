"""
FILE: src/voltsentry/services/notification_manager.py
PATH: voltsentry/src/voltsentry/services/notification_manager.py
DESCRIPTION: Native Windows toast notifications with fallback
PHASE: 3.3 - Notification Manager

DISCIPLINES:
- 0.1 Logging Standard: WARNING on failure, DEBUG on success
- 0.2 Error Handling: Catch platform-specific exceptions
- 0.3 Retry Standard: 1 attempt (transient failures don't apply)
- 0.4 Fallback Standard: In-app banner + tray tooltip
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional

from ..core.constants import APP_ID, APP_NAME, IS_WINDOWS
from ..core.decorators import log_entry_exit
from ..core.exceptions import NotificationError
from ..core.logging_config import get_logger, log_audit

logger = get_logger(__name__)


@dataclass
class Notification:
    """Notification data structure."""

    title: str
    message: str
    icon: Optional[str] = None  # Path to icon
    duration: int = 5  # Seconds to display


class NotificationManager:
    """
    Native OS notification manager with fallback to in-app banner.

    On Windows: Uses Windows Toast Notifications (Action Center)
    On macOS: Uses Notification Center (future)
    Fallback: In-app banner + tray tooltip
    """

    def __init__(self):
        self._on_fallback: Optional[Callable[[Notification], None]] = None
        self._last_notification: Optional[Notification] = None
        self._native_available = self._check_native_available()

        logger.info(
            "NotificationManager initialized: native=%s", self._native_available
        )

    def _check_native_available(self) -> bool:
        """Check if native notifications are available."""
        if IS_WINDOWS:
            return self._check_windows_toast_available()
        # macOS/Linux: not yet implemented
        return False

    def _check_windows_toast_available(self) -> bool:
        """Check if Windows Toast Notifications are available."""
        try:
            from windows_toasts import WindowsToaster

            return True
        except ImportError:
            logger.debug("windows_toasts module not installed")
            return False
        except Exception as e:
            logger.debug("Windows Toast check failed: %s", e)
            return False

    def set_fallback_callback(
        self, callback: Callable[[Notification], None]
    ) -> None:
        """
        Set callback for fallback notifications (in-app banner).

        Args:
            callback: Function called with Notification when native fails
        """
        self._on_fallback = callback
        logger.debug("Fallback callback registered")

    @log_entry_exit()
    def notify(self, notification: Notification) -> bool:
        """
        Send a notification.

        Args:
            notification: Notification data

        Returns:
            True if notification was sent, False if failed
        """
        self._last_notification = notification

        if self._native_available:
            try:
                return self._send_native(notification)
            except Exception as e:
                logger.warning(
                    "Error occurred during native notification attempt: %s. Invoking fallback.",
                    e,
                )
                return self._fallback(notification)
        else:
            return self._fallback(notification)

    def _send_native(self, notification: Notification) -> bool:
        """Send native OS notification with catch-all fallback."""
        try:
            if IS_WINDOWS:
                return self._send_windows_toast(notification)
            else:
                # macOS/Linux: fallback
                return self._fallback(notification)
        except Exception as e:
            logger.warning(
                "_send_native encountered exception: %s. Switching to fallback.", e
            )
            return self._fallback(notification)

    def _send_windows_toast(self, notification: Notification) -> bool:
        """Send Windows Toast Notification."""
        try:
            from windows_toasts import Toast, ToastDisplayImage, WindowsToaster

            toaster = WindowsToaster(APP_NAME)
            toast = Toast()

            # Set text fields
            toast.text_fields = [notification.title, notification.message]

            # Set icon image if path provided
            if notification.icon:
                try:
                    toast.AddImage(
                        ToastDisplayImage.fromPath(notification.icon)
                    )
                except Exception as img_err:
                    logger.debug(
                        "Failed to attach icon to toast: %s", img_err
                    )

            # Display toast
            toaster.show_toast(toast)

            logger.debug("Windows Toast sent: %s", notification.title)
            return True

        except ImportError:
            logger.warning("windows_toasts module unavailable during delivery")
            return self._fallback(notification)
        except Exception as e:
            logger.warning(
                "Windows Toast delivery failed: %s. Switching to fallback.", e
            )
            return self._fallback(notification)

    def _fallback(self, notification: Notification) -> bool:
        """
        Fallback notification method.

        Calls the registered fallback callback (in-app banner).
        """
        logger.warning(
            "Using fallback notification: %s - %s",
            notification.title,
            notification.message,
        )

        if self._on_fallback:
            try:
                self._on_fallback(notification)
                return True
            except Exception as e:
                logger.error("Fallback callback failed: %s", e)
                return False

        log_audit("WARNING", f"Notification fallback: {notification.title}")
        return False

    def get_status(self) -> dict:
        """Get notification manager status."""
        return {
            "native_available": self._native_available,
            "last_notification": (
                self._last_notification.title
                if self._last_notification
                else None
            ),
            "has_fallback": self._on_fallback is not None,
        }

    def __repr__(self) -> str:
        return f"<NotificationManager native={self._native_available}>"