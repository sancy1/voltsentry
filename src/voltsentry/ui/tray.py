# """
# FILE: src/voltsentry/ui/tray.py
# PATH: voltsentry/src/voltsentry/ui/tray.py
# DESCRIPTION: Native Windows 11 system tray icon with tooltip, menu, and pop-up notifications
# PHASE: 4.1 - Tray Icon & Menu

# DISCIPLINES:
# - 0.1 Logging: WARNING if tray unavailable
# - 0.2 Error Handling: QSystemTrayIcon availability check
# - 0.4 Fallback: Minimized window if tray unavailable
# """

# from pathlib import Path
# from typing import Optional

# from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
# from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
# from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QMessageBox, QApplication

# from ..core.constants import APP_NAME, APP_ID, TRAY_ICON_SIZE, IS_WINDOWS
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from .styles import get_status_color, COLORS

# logger = get_logger(__name__)


# class TrayIcon(QSystemTrayIcon):
#     """
#     Native Windows 11 system tray icon.
    
#     Features:
#     - Dynamic modern battery icon based on battery level
#     - Tooltip with battery details
#     - Right-click context menu
#     - Left-click opens dashboard
#     - Pop-up notifications
#     - Flashing icon during alarms
#     - Fallback mode if tray is unavailable
#     """
    
#     # Signals
#     dashboard_requested = pyqtSignal()
#     settings_requested = pyqtSignal()
#     pause_toggled = pyqtSignal(bool)
#     exit_requested = pyqtSignal()
#     alarm_triggered = pyqtSignal(str)  # alarm type
    
#     def __init__(self, parent: Optional[QWidget] = None):
#         """
#         Initialize the tray icon.
        
#         Args:
#             parent: Parent widget
#         """
#         super().__init__(parent)
        
#         self._parent = parent
#         self._current_percent = 0
#         self._is_charging = False
#         self._is_paused = False
#         self._alarm_active = False
#         self._alarm_type: Optional[str] = None
#         self._flash_state = False
#         self._flash_timer: Optional[QTimer] = None
#         self._current_icon = QIcon()
        
#         # Notification repeating timer
#         self._notification_timer: Optional[QTimer] = None
#         self._notification_count = 0
#         self._max_notifications = 12
#         self._pending_notification_title = ""
#         self._pending_notification_message = ""
#         self._notification_is_active = False
        
#         # Check tray availability
#         if not QSystemTrayIcon.isSystemTrayAvailable():
#             logger.warning("System tray not available - falling back to window mode")
#             self._use_window_fallback = True
#         else:
#             self._use_window_fallback = False
        
#         # Create icon
#         self._create_icon()
        
#         # Create menu
#         self._create_menu()
        
#         # Set tooltip
#         self._update_tooltip()
        
#         # Connect signals
#         self.activated.connect(self._on_activated)
        
#         # Enable message signals for balloon notifications
#         self.messageClicked.connect(self._on_message_clicked)
        
#         logger.info("TrayIcon initialized (fallback=%s)", self._use_window_fallback)
    
#     def _create_icon(self) -> None:
#         """Create the tray icon."""
#         if self._use_window_fallback:
#             pixmap = QPixmap(TRAY_ICON_SIZE, TRAY_ICON_SIZE)
#             pixmap.fill(Qt.GlobalColor.transparent)
#             self.setIcon(QIcon(pixmap))
#             return
        
#         self._update_icon()
#         self.setIcon(self._current_icon)
    
#     def _create_battery_pixmap(self, percent: int, is_charging: bool) -> QPixmap:
#         """
#         Create a modern horizontal battery icon pixmap adhering to Windows 11 UI guidelines.
        
#         Args:
#             percent: Battery percentage (0-100)
#             is_charging: True if charging
        
#         Returns:
#             QPixmap with sleek battery icon
#         """
#         size = TRAY_ICON_SIZE
#         pixmap = QPixmap(size, size)
#         pixmap.fill(Qt.GlobalColor.transparent)
        
#         painter = QPainter(pixmap)
#         painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
#         status_color = QColor(get_status_color(percent, is_charging))
        
#         # Layout metrics for horizontal battery
#         body_x = 2.0
#         body_y = 9.0
#         body_w = 23.0
#         body_h = 14.0
#         radius = 3.0
        
#         # Outer shell border
#         body_rect = QRectF(body_x, body_y, body_w, body_h)
#         shell_pen = QPen(status_color, 2.0)
#         painter.setPen(shell_pen)
#         painter.setBrush(Qt.BrushStyle.NoBrush)
#         painter.drawRoundedRect(body_rect, radius, radius)
        
#         # Terminal cap (Right side)
#         cap_x = body_x + body_w + 1.0
#         cap_y = body_y + 4.0
#         cap_w = 2.0
#         cap_h = 6.0
#         cap_rect = QRectF(cap_x, cap_y, cap_w, cap_h)
#         cap_path = QPainterPath()
#         cap_path.addRoundedRect(cap_rect, 1.0, 1.0)
#         painter.fillPath(cap_path, QBrush(status_color))
        
#         # Inner Fill
#         fill_margin = 3.0
#         max_fill_w = body_w - (fill_margin * 2)
#         fill_h = body_h - (fill_margin * 2)
        
#         clamped_pct = max(0, min(100, percent))
#         fill_w = (max_fill_w * clamped_pct) / 100.0
        
#         if fill_w > 0:
#             fill_x = body_x + fill_margin
#             fill_y = body_y + fill_margin
#             fill_rect = QRectF(fill_x, fill_y, fill_w, fill_h)
            
#             fill_path = QPainterPath()
#             fill_path.addRoundedRect(fill_rect, 1.5, 1.5)
#             painter.fillPath(fill_path, QBrush(status_color))
        
#         # Minimalist Charging Indicator Bolt (Center aligned)
#         if is_charging:
#             cx = body_x + (body_w / 2.0)
#             cy = body_y + (body_h / 2.0)
            
#             bolt_path = QPainterPath()
#             bolt_path.moveTo(cx + 0.5, cy - 5.0)
#             bolt_path.lineTo(cx - 3.5, cy + 0.5)
#             bolt_path.lineTo(cx - 0.5, cy + 0.5)
#             bolt_path.lineTo(cx - 1.5, cy + 5.0)
#             bolt_path.lineTo(cx + 2.5, cy - 0.5)
#             bolt_path.lineTo(cx - 0.5, cy - 0.5)
#             bolt_path.closeSubpath()
            
#             painter.setPen(QPen(QColor(20, 20, 20), 1.0))
#             painter.setBrush(QBrush(QColor(255, 255, 255)))
#             painter.drawPath(bolt_path)
        
#         painter.end()
#         return pixmap
    
#     def _update_icon(self) -> None:
#         """Update the tray icon based on current battery state."""
#         if self._use_window_fallback:
#             return
        
#         self._current_icon = QIcon(
#             self._create_battery_pixmap(
#                 self._current_percent,
#                 self._is_charging
#             )
#         )
#         self.setIcon(self._current_icon)
    
#     def _create_menu(self) -> None:
#         """Create clean context menu."""
#         self._menu = QMenu()
        
#         # Dashboard action
#         self._dashboard_action = QAction("Dashboard", self._menu)
#         self._dashboard_action.triggered.connect(self.dashboard_requested.emit)
#         self._menu.addAction(self._dashboard_action)
        
#         self._menu.addSeparator()
        
#         # Pause/Resume action
#         self._pause_action = QAction("Pause Monitoring", self._menu)
#         self._pause_action.triggered.connect(self._toggle_pause)
#         self._menu.addAction(self._pause_action)
        
#         # Snooze action
#         self._snooze_action = QAction("Snooze Alarm", self._menu)
#         self._snooze_action.triggered.connect(self._snooze_alarm)
#         self._snooze_action.setEnabled(False)
#         self._menu.addAction(self._snooze_action)
        
#         self._menu.addSeparator()
        
#         # Settings action
#         self._settings_action = QAction("Settings", self._menu)
#         self._settings_action.triggered.connect(self.settings_requested.emit)
#         self._menu.addAction(self._settings_action)
        
#         self._menu.addSeparator()
        
#         # About action
#         self._about_action = QAction("About", self._menu)
#         self._about_action.triggered.connect(self._show_about)
#         self._menu.addAction(self._about_action)
        
#         # Exit action
#         self._exit_action = QAction("Exit", self._menu)
#         self._exit_action.triggered.connect(self.exit_requested.emit)
#         self._menu.addAction(self._exit_action)
        
#         self.setContextMenu(self._menu)
    
#     def _update_tooltip(self) -> None:
#         """Update tooltip with current battery info."""
#         if self._use_window_fallback:
#             self.setToolTip(f"{APP_NAME} - Tray Unavailable")
#             return
        
#         percent = self._current_percent
#         status = "Charging" if self._is_charging else "Discharging"
        
#         alarm_text = f"\nALARM: {self._alarm_type.upper()}" if (self._alarm_active and self._alarm_type) else ""
        
#         tooltip = (
#             f"{APP_NAME}\n"
#             f"─────────────────\n"
#             f"Battery: {percent}%\n"
#             f"Status: {status}"
#             f"{alarm_text}\n"
#             f"─────────────────\n"
#             f"Click to open Dashboard"
#         )
        
#         self.setToolTip(tooltip)
    
#     # ============================================================================
#     # POP-UP NOTIFICATION METHODS - Windows Toast
#     # ============================================================================
    
#     def show_notification(self, title: str, message: str, urgency: str = "normal") -> None:
#         """
#         Show a pop-up notification near the battery icon.
        
#         Uses Windows Toast Notifications for Windows 11 style popups.
        
#         Args:
#             title: Notification title
#             message: Notification message
#             urgency: 'normal' or 'critical'
#         """
#         try:
#             logger.info("Showing Windows notification: %s", title)
            
#             self._notification_is_active = True
#             self._pending_notification_title = title
#             self._pending_notification_message = message
            
#             if IS_WINDOWS:
#                 success = self._show_windows_toast(title, message, urgency)
#                 if success:
#                     logger.debug("Windows Toast shown successfully")
#                     if self._alarm_active:
#                         self._start_repeating_notification(title, message)
#                     return
            
#             self._show_qt_balloon(title, message, urgency)
#             self._start_flash()
            
#             if self._alarm_active:
#                 self._start_repeating_notification(title, message)
            
#         except Exception as e:
#             logger.error("Failed to show notification: %s", e)
#             self._show_qt_balloon(title, message, urgency)
    
#     def _show_windows_toast(self, title: str, message: str, urgency: str = "normal") -> bool:
#         """Show Windows 11 native toast notification."""
#         try:
#             from winrt.windows.ui.notifications import (
#                 ToastNotificationManager, ToastNotification,
#                 ToastTemplateType, ToastDuration
#             )
            
#             template = ToastNotificationManager.get_template_content(ToastTemplateType.TOAST_TEXT02)
            
#             text_elements = template.get_text_elements()
#             if len(text_elements) >= 2:
#                 text_elements[0].text = title
#                 text_elements[1].text = message
            
#             notifier = ToastNotificationManager.create_toast_notifier(APP_NAME)
#             toast = ToastNotification(template)
            
#             toast.duration = ToastDuration.LONG if urgency == "critical" else ToastDuration.SHORT
            
#             notifier.show(toast)
#             logger.debug("Windows Toast notification shown via winrt")
#             return True
            
#         except ImportError:
#             logger.debug("winrt not available, using Qt fallback")
#             return False
#         except Exception as e:
#             logger.error("Windows Toast failed: %s", e)
#             return False
    
#     def _show_qt_balloon(self, title: str, message: str, urgency: str = "normal") -> None:
#         """Show Qt balloon notification fallback."""
#         try:
#             icon = (
#                 QSystemTrayIcon.MessageIcon.Critical
#                 if urgency == "critical"
#                 else QSystemTrayIcon.MessageIcon.Information
#             )
            
#             self.showMessage(title, message, icon, 15000)
#             self._notification_is_active = True
#             logger.debug("Qt balloon notification shown")
            
#         except Exception as e:
#             logger.error("Qt balloon failed: %s", e)
    
#     def _start_repeating_notification(self, title: str, message: str) -> None:
#         """Start repeating notifications (max 12 times)."""
#         self._notification_count = 0
#         self._pending_notification_title = title
#         self._pending_notification_message = message
        
#         if self._notification_timer is None:
#             self._notification_timer = QTimer()
#             self._notification_timer.timeout.connect(self._repeat_notification)
        
#         self._notification_timer.start(30000)
#         self._notification_count = 0
#         logger.debug("Repeating notification timer started")
    
#     def _repeat_notification(self) -> None:
#         """Repeat notification if alarm is still active."""
#         self._notification_count += 1
        
#         if self._notification_count >= self._max_notifications:
#             self._notification_timer.stop()
#             self._notification_is_active = False
#             logger.debug("Repeating notifications stopped (max reached)")
#             return
        
#         if self._alarm_active:
#             repeat_msg = f"{self._pending_notification_message} (Reminder {self._notification_count + 1}/{self._max_notifications})"
#             self._show_qt_balloon(
#                 f"{self._pending_notification_title}",
#                 repeat_msg,
#                 "critical"
#             )
#             logger.debug("Repeating notification #%d", self._notification_count + 1)
    
#     def _stop_repeating_notification(self) -> None:
#         """Stop repeating notifications."""
#         if self._notification_timer is not None:
#             self._notification_timer.stop()
#             self._notification_timer = None
#             self._notification_count = 0
#             self._notification_is_active = False
#             logger.debug("Repeating notifications stopped")
    
#     def _on_message_clicked(self) -> None:
#         """Handle click on notification balloon."""
#         logger.debug("Notification clicked - opening dashboard")
#         self._notification_is_active = False
#         self.dashboard_requested.emit()
    
#     def _toggle_pause(self) -> None:
#         """Toggle monitoring pause state."""
#         self._is_paused = not self._is_paused
#         self._pause_action.setText(
#             "Resume Monitoring" if self._is_paused else "Pause Monitoring"
#         )
#         self.pause_toggled.emit(self._is_paused)
#         logger.info("Monitoring %s", "paused" if self._is_paused else "resumed")
    
#     def _snooze_alarm(self) -> None:
#         """Snooze current alarm."""
#         if self._alarm_active:
#             self.alarm_triggered.emit("snooze")
#             self._alarm_active = False
#             self._snooze_action.setEnabled(False)
#             self._stop_flash()
#             self._stop_repeating_notification()
#             self._update_tooltip()
#             logger.info("Alarm snoozed from tray")
    
#     def _show_about(self) -> None:
#         """Show about dialog."""
#         QMessageBox.about(
#             self._parent,
#             f"About {APP_NAME}",
#             f"<h2>{APP_NAME}</h2>"
#             f"<p>Version: 1.0.0</p>"
#             f"<p>Intelligent Battery Health Management System</p>"
#             f"<p>Protect your battery, extend its life.</p>"
#             f"<p style='color: #666; font-size: 11px;'>"
#             f"{APP_ID}</p>"
#         )
    
#     def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
#         """Handle tray icon click activation."""
#         if reason in (
#             QSystemTrayIcon.ActivationReason.DoubleClick,
#             QSystemTrayIcon.ActivationReason.Trigger
#         ):
#             self.dashboard_requested.emit()
    
#     @log_entry_exit()
#     def update_battery(self, percent: int, is_charging: bool) -> None:
#         """Update battery status."""
#         self._current_percent = percent
#         self._is_charging = is_charging
        
#         self._update_icon()
#         self._update_tooltip()
    
#     @log_entry_exit()
#     def update_alarm(self, active: bool, alarm_type: Optional[str] = None) -> None:
#         """Update alarm status."""
#         self._alarm_active = active
#         self._alarm_type = alarm_type
        
#         self._snooze_action.setEnabled(active)
        
#         if active:
#             self._start_flash()
#             if alarm_type:
#                 title = f"{APP_NAME} - {alarm_type.replace('_', ' ').title()}"
#                 if alarm_type == "full_charge":
#                     message = "Battery fully charged! Unplug to extend battery life."
#                 elif alarm_type == "low_battery":
#                     message = "Battery low! Plug in to charge."
#                 elif alarm_type == "critical_low":
#                     message = "Battery critically low! Plug in immediately!"
#                 else:
#                     message = "Battery alarm triggered!"
                
#                 self.show_notification(title, message, urgency="critical")
#         else:
#             self._stop_flash()
#             self._stop_repeating_notification()
#             self._notification_is_active = False
        
#         self._update_tooltip()
    
#     def _start_flash(self) -> None:
#         """Start flashing the tray icon for alarm state."""
#         if self._flash_timer is None:
#             self._flash_timer = QTimer()
#             self._flash_timer.timeout.connect(self._flash_toggle)
#             self._flash_timer.start(500)
#         self._flash_state = False
    
#     def _stop_flash(self) -> None:
#         """Stop flashing the tray icon."""
#         if self._flash_timer is not None:
#             self._flash_timer.stop()
#             self._flash_timer.deleteLater()
#             self._flash_timer = None
#         self._update_icon()
#         self._flash_state = False
    
#     def _flash_toggle(self) -> None:
#         """Toggle flash state using transparent alert overlay."""
#         self._flash_state = not self._flash_state
#         if self._flash_state:
#             pixmap = self._create_battery_pixmap(self._current_percent, self._is_charging)
#             painter = QPainter(pixmap)
#             painter.setBrush(QBrush(QColor(231, 76, 60, 100)))
#             painter.drawRect(painter.viewport())
#             painter.end()
#             self.setIcon(QIcon(pixmap))
#         else:
#             self._update_icon()
    
#     def show_tray(self) -> None:
#         """Show tray icon."""
#         if not self._use_window_fallback:
#             self.show()
#             logger.info("Tray icon shown")
    
#     def hide_tray(self) -> None:
#         """Hide tray icon."""
#         if not self._use_window_fallback:
#             self.hide()
#             logger.info("Tray icon hidden")
    
#     def get_is_paused(self) -> bool:
#         """Check if monitoring is paused."""
#         return self._is_paused
    
#     def get_is_fallback(self) -> bool:
#         """Check if using window fallback mode."""
#         return self._use_window_fallback
    
#     def __repr__(self) -> str:
#         return f"<TrayIcon percent={self._current_percent}, charging={self._is_charging}, paused={self._is_paused}>"






































































"""
FILE: src/voltsentry/ui/tray.py
PATH: voltsentry/src/voltsentry/ui/tray.py
DESCRIPTION: Native Windows 11 system tray icon with tooltip, menu, and pop-up notifications
PHASE: 4.1 - Tray Icon & Menu

DISCIPLINES:
- 0.1 Logging: WARNING if tray unavailable
- 0.2 Error Handling: QSystemTrayIcon availability check
- 0.4 Fallback: Minimized window if tray unavailable
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QMessageBox, QApplication

from ..core.constants import APP_NAME, APP_ID, TRAY_ICON_SIZE, IS_WINDOWS
from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit
from .styles import get_status_color, COLORS

# ✅ Import dynamic resource helper
from ..utils import get_resource_path

logger = get_logger(__name__)


class TrayIcon(QSystemTrayIcon):
    """
    Native Windows 11 system tray icon.
    
    Features:
    - Dynamic modern battery icon based on battery level
    - Tooltip with battery details
    - Right-click context menu
    - Left-click opens dashboard
    - Pop-up notifications
    - Flashing icon during alarms
    - Fallback mode if tray is unavailable
    - Custom app icon from assets folder
    """
    
    # Signals
    dashboard_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)
    exit_requested = pyqtSignal()
    alarm_triggered = pyqtSignal(str)  # alarm type
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the tray icon.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._parent = parent
        self._current_percent = 0
        self._is_charging = False
        self._is_paused = False
        self._alarm_active = False
        self._alarm_type: Optional[str] = None
        self._flash_state = False
        self._flash_timer: Optional[QTimer] = None
        self._current_icon = QIcon()
        
        # Notification repeating timer
        self._notification_timer: Optional[QTimer] = None
        self._notification_count = 0
        self._max_notifications = 12
        self._pending_notification_title = ""
        self._pending_notification_message = ""
        self._notification_is_active = False
        
        # Check tray availability
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available - falling back to window mode")
            self._use_window_fallback = True
        else:
            self._use_window_fallback = False
        
        # Create icon
        self._create_icon()
        
        # Create menu
        self._create_menu()
        
        # Set tooltip
        self._update_tooltip()
        
        # Connect signals
        self.activated.connect(self._on_activated)
        
        # Enable message signals for balloon notifications
        self.messageClicked.connect(self._on_message_clicked)
        
        logger.info("TrayIcon initialized (fallback=%s)", self._use_window_fallback)
    
    def _create_icon(self) -> None:
        """Create the tray icon with dynamic asset loading."""
        if self._use_window_fallback:
            pixmap = QPixmap(TRAY_ICON_SIZE, TRAY_ICON_SIZE)
            pixmap.fill(Qt.GlobalColor.transparent)
            self.setIcon(QIcon(pixmap))
            return
        
        # ✅ Try to load custom icon from assets first
        icon_loaded = self._load_custom_icon()
        
        if not icon_loaded:
            # Fallback to generated battery icon
            self._update_icon()
            self.setIcon(self._current_icon)
    
    def _load_custom_icon(self) -> bool:
        """
        Load custom icon from assets folder.
        
        Returns:
            True if icon was loaded, False otherwise
        """
        # Try PNG first (better quality)
        icon_path = get_resource_path("assets/icon.png")
        
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
            logger.debug("Tray custom icon loaded from: %s", icon_path)
            return True
        
        # Try ICO as fallback
        icon_path = get_resource_path("assets/icon.ico")
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
            logger.debug("Tray custom icon loaded from: %s", icon_path)
            return True
        
        logger.debug("No custom icon found, using generated battery icon")
        return False
    
    def _create_battery_pixmap(self, percent: int, is_charging: bool) -> QPixmap:
        """
        Create a modern horizontal battery icon pixmap adhering to Windows 11 UI guidelines.
        
        Args:
            percent: Battery percentage (0-100)
            is_charging: True if charging
        
        Returns:
            QPixmap with sleek battery icon
        """
        size = TRAY_ICON_SIZE
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        status_color = QColor(get_status_color(percent, is_charging))
        
        # Layout metrics for horizontal battery
        body_x = 2.0
        body_y = 9.0
        body_w = 23.0
        body_h = 14.0
        radius = 3.0
        
        # Outer shell border
        body_rect = QRectF(body_x, body_y, body_w, body_h)
        shell_pen = QPen(status_color, 2.0)
        painter.setPen(shell_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(body_rect, radius, radius)
        
        # Terminal cap (Right side)
        cap_x = body_x + body_w + 1.0
        cap_y = body_y + 4.0
        cap_w = 2.0
        cap_h = 6.0
        cap_rect = QRectF(cap_x, cap_y, cap_w, cap_h)
        cap_path = QPainterPath()
        cap_path.addRoundedRect(cap_rect, 1.0, 1.0)
        painter.fillPath(cap_path, QBrush(status_color))
        
        # Inner Fill
        fill_margin = 3.0
        max_fill_w = body_w - (fill_margin * 2)
        fill_h = body_h - (fill_margin * 2)
        
        clamped_pct = max(0, min(100, percent))
        fill_w = (max_fill_w * clamped_pct) / 100.0
        
        if fill_w > 0:
            fill_x = body_x + fill_margin
            fill_y = body_y + fill_margin
            fill_rect = QRectF(fill_x, fill_y, fill_w, fill_h)
            
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, 1.5, 1.5)
            painter.fillPath(fill_path, QBrush(status_color))
        
        # Minimalist Charging Indicator Bolt (Center aligned)
        if is_charging:
            cx = body_x + (body_w / 2.0)
            cy = body_y + (body_h / 2.0)
            
            bolt_path = QPainterPath()
            bolt_path.moveTo(cx + 0.5, cy - 5.0)
            bolt_path.lineTo(cx - 3.5, cy + 0.5)
            bolt_path.lineTo(cx - 0.5, cy + 0.5)
            bolt_path.lineTo(cx - 1.5, cy + 5.0)
            bolt_path.lineTo(cx + 2.5, cy - 0.5)
            bolt_path.lineTo(cx - 0.5, cy - 0.5)
            bolt_path.closeSubpath()
            
            painter.setPen(QPen(QColor(20, 20, 20), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawPath(bolt_path)
        
        painter.end()
        return pixmap
    
    def _update_icon(self) -> None:
        """Update the tray icon based on current battery state."""
        if self._use_window_fallback:
            return
        
        self._current_icon = QIcon(
            self._create_battery_pixmap(
                self._current_percent,
                self._is_charging
            )
        )
        self.setIcon(self._current_icon)
    
    def _create_menu(self) -> None:
        """Create clean context menu."""
        self._menu = QMenu()
        
        # Dashboard action
        self._dashboard_action = QAction("Dashboard", self._menu)
        self._dashboard_action.triggered.connect(self.dashboard_requested.emit)
        self._menu.addAction(self._dashboard_action)
        
        self._menu.addSeparator()
        
        # Pause/Resume action
        self._pause_action = QAction("Pause Monitoring", self._menu)
        self._pause_action.triggered.connect(self._toggle_pause)
        self._menu.addAction(self._pause_action)
        
        # Snooze action
        self._snooze_action = QAction("Snooze Alarm", self._menu)
        self._snooze_action.triggered.connect(self._snooze_alarm)
        self._snooze_action.setEnabled(False)
        self._menu.addAction(self._snooze_action)
        
        self._menu.addSeparator()
        
        # Settings action
        self._settings_action = QAction("Settings", self._menu)
        self._settings_action.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(self._settings_action)
        
        self._menu.addSeparator()
        
        # About action
        self._about_action = QAction("About", self._menu)
        self._about_action.triggered.connect(self._show_about)
        self._menu.addAction(self._about_action)
        
        # Exit action
        self._exit_action = QAction("Exit", self._menu)
        self._exit_action.triggered.connect(self.exit_requested.emit)
        self._menu.addAction(self._exit_action)
        
        self.setContextMenu(self._menu)
    
    def _update_tooltip(self) -> None:
        """Update tooltip with current battery info."""
        if self._use_window_fallback:
            self.setToolTip(f"{APP_NAME} - Tray Unavailable")
            return
        
        percent = self._current_percent
        status = "Charging" if self._is_charging else "Discharging"
        
        alarm_text = f"\nALARM: {self._alarm_type.upper()}" if (self._alarm_active and self._alarm_type) else ""
        
        tooltip = (
            f"{APP_NAME}\n"
            f"─────────────────\n"
            f"Battery: {percent}%\n"
            f"Status: {status}"
            f"{alarm_text}\n"
            f"─────────────────\n"
            f"Click to open Dashboard"
        )
        
        self.setToolTip(tooltip)
    
    # ============================================================================
    # POP-UP NOTIFICATION METHODS - Windows Toast
    # ============================================================================
    
    def show_notification(self, title: str, message: str, urgency: str = "normal") -> None:
        """
        Show a pop-up notification near the battery icon.
        
        Uses Windows Toast Notifications for Windows 11 style popups.
        
        Args:
            title: Notification title
            message: Notification message
            urgency: 'normal' or 'critical'
        """
        try:
            logger.info("Showing Windows notification: %s", title)
            
            self._notification_is_active = True
            self._pending_notification_title = title
            self._pending_notification_message = message
            
            if IS_WINDOWS:
                success = self._show_windows_toast(title, message, urgency)
                if success:
                    logger.debug("Windows Toast shown successfully")
                    if self._alarm_active:
                        self._start_repeating_notification(title, message)
                    return
            
            self._show_qt_balloon(title, message, urgency)
            self._start_flash()
            
            if self._alarm_active:
                self._start_repeating_notification(title, message)
            
        except Exception as e:
            logger.error("Failed to show notification: %s", e)
            self._show_qt_balloon(title, message, urgency)
    
    def _show_windows_toast(self, title: str, message: str, urgency: str = "normal") -> bool:
        """Show Windows 11 native toast notification."""
        try:
            from winrt.windows.ui.notifications import (
                ToastNotificationManager, ToastNotification,
                ToastTemplateType, ToastDuration
            )
            
            template = ToastNotificationManager.get_template_content(ToastTemplateType.TOAST_TEXT02)
            
            text_elements = template.get_text_elements()
            if len(text_elements) >= 2:
                text_elements[0].text = title
                text_elements[1].text = message
            
            notifier = ToastNotificationManager.create_toast_notifier(APP_NAME)
            toast = ToastNotification(template)
            
            toast.duration = ToastDuration.LONG if urgency == "critical" else ToastDuration.SHORT
            
            notifier.show(toast)
            logger.debug("Windows Toast notification shown via winrt")
            return True
            
        except ImportError:
            logger.debug("winrt not available, using Qt fallback")
            return False
        except Exception as e:
            logger.error("Windows Toast failed: %s", e)
            return False
    
    def _show_qt_balloon(self, title: str, message: str, urgency: str = "normal") -> None:
        """Show Qt balloon notification fallback."""
        try:
            icon = (
                QSystemTrayIcon.MessageIcon.Critical
                if urgency == "critical"
                else QSystemTrayIcon.MessageIcon.Information
            )
            
            self.showMessage(title, message, icon, 15000)
            self._notification_is_active = True
            logger.debug("Qt balloon notification shown")
            
        except Exception as e:
            logger.error("Qt balloon failed: %s", e)
    
    def _start_repeating_notification(self, title: str, message: str) -> None:
        """Start repeating notifications (max 12 times)."""
        self._notification_count = 0
        self._pending_notification_title = title
        self._pending_notification_message = message
        
        if self._notification_timer is None:
            self._notification_timer = QTimer()
            self._notification_timer.timeout.connect(self._repeat_notification)
        
        self._notification_timer.start(30000)
        self._notification_count = 0
        logger.debug("Repeating notification timer started")
    
    def _repeat_notification(self) -> None:
        """Repeat notification if alarm is still active."""
        self._notification_count += 1
        
        if self._notification_count >= self._max_notifications:
            self._notification_timer.stop()
            self._notification_is_active = False
            logger.debug("Repeating notifications stopped (max reached)")
            return
        
        if self._alarm_active:
            repeat_msg = f"{self._pending_notification_message} (Reminder {self._notification_count + 1}/{self._max_notifications})"
            self._show_qt_balloon(
                f"{self._pending_notification_title}",
                repeat_msg,
                "critical"
            )
            logger.debug("Repeating notification #%d", self._notification_count + 1)
    
    def _stop_repeating_notification(self) -> None:
        """Stop repeating notifications."""
        if self._notification_timer is not None:
            self._notification_timer.stop()
            self._notification_timer = None
            self._notification_count = 0
            self._notification_is_active = False
            logger.debug("Repeating notifications stopped")
    
    def _on_message_clicked(self) -> None:
        """Handle click on notification balloon."""
        logger.debug("Notification clicked - opening dashboard")
        self._notification_is_active = False
        self.dashboard_requested.emit()
    
    def _toggle_pause(self) -> None:
        """Toggle monitoring pause state."""
        self._is_paused = not self._is_paused
        self._pause_action.setText(
            "Resume Monitoring" if self._is_paused else "Pause Monitoring"
        )
        self.pause_toggled.emit(self._is_paused)
        logger.info("Monitoring %s", "paused" if self._is_paused else "resumed")
    
    def _snooze_alarm(self) -> None:
        """Snooze current alarm."""
        if self._alarm_active:
            self.alarm_triggered.emit("snooze")
            self._alarm_active = False
            self._snooze_action.setEnabled(False)
            self._stop_flash()
            self._stop_repeating_notification()
            self._update_tooltip()
            logger.info("Alarm snoozed from tray")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self._parent,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version: 1.0.0</p>"
            f"<p>Intelligent Battery Health Management System</p>"
            f"<p>Protect your battery, extend its life.</p>"
            f"<p style='color: #666; font-size: 11px;'>"
            f"{APP_ID}</p>"
        )
    
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click activation."""
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger
        ):
            self.dashboard_requested.emit()
    
    @log_entry_exit()
    def update_battery(self, percent: int, is_charging: bool) -> None:
        """Update battery status."""
        self._current_percent = percent
        self._is_charging = is_charging
        
        self._update_icon()
        self._update_tooltip()
    
    @log_entry_exit()
    def update_alarm(self, active: bool, alarm_type: Optional[str] = None) -> None:
        """Update alarm status."""
        self._alarm_active = active
        self._alarm_type = alarm_type
        
        self._snooze_action.setEnabled(active)
        
        if active:
            self._start_flash()
            if alarm_type:
                title = f"{APP_NAME} - {alarm_type.replace('_', ' ').title()}"
                if alarm_type == "full_charge":
                    message = "Battery fully charged! Unplug to extend battery life."
                elif alarm_type == "low_battery":
                    message = "Battery low! Plug in to charge."
                elif alarm_type == "critical_low":
                    message = "Battery critically low! Plug in immediately!"
                else:
                    message = "Battery alarm triggered!"
                
                self.show_notification(title, message, urgency="critical")
        else:
            self._stop_flash()
            self._stop_repeating_notification()
            self._notification_is_active = False
        
        self._update_tooltip()
    
    def _start_flash(self) -> None:
        """Start flashing the tray icon for alarm state."""
        if self._flash_timer is None:
            self._flash_timer = QTimer()
            self._flash_timer.timeout.connect(self._flash_toggle)
            self._flash_timer.start(500)
        self._flash_state = False
    
    def _stop_flash(self) -> None:
        """Stop flashing the tray icon."""
        if self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer.deleteLater()
            self._flash_timer = None
        self._update_icon()
        self._flash_state = False
    
    def _flash_toggle(self) -> None:
        """Toggle flash state using transparent alert overlay."""
        self._flash_state = not self._flash_state
        if self._flash_state:
            pixmap = self._create_battery_pixmap(self._current_percent, self._is_charging)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(QColor(231, 76, 60, 100)))
            painter.drawRect(painter.viewport())
            painter.end()
            self.setIcon(QIcon(pixmap))
        else:
            self._update_icon()
    
    def show_tray(self) -> None:
        """Show tray icon."""
        if not self._use_window_fallback:
            self.show()
            logger.info("Tray icon shown")
    
    def hide_tray(self) -> None:
        """Hide tray icon."""
        if not self._use_window_fallback:
            self.hide()
            logger.info("Tray icon hidden")
    
    def get_is_paused(self) -> bool:
        """Check if monitoring is paused."""
        return self._is_paused
    
    def get_is_fallback(self) -> bool:
        """Check if using window fallback mode."""
        return self._use_window_fallback
    
    def __repr__(self) -> str:
        return f"<TrayIcon percent={self._current_percent}, charging={self._is_charging}, paused={self._is_paused}>"
    