# """
# FILE: src/voltsentry/app.py
# PATH: voltsentry/src/voltsentry/app.py
# DESCRIPTION: Main application entry point - connects all components
# PHASE: 5 - Integration & Testing

# DISCIPLINES:
# - 0.1 Logging: INFO on startup/shutdown, ERROR on failures
# - 0.2 Error Handling: Graceful shutdown on errors
# - 0.4 Fallback: Tray fallback if unavailable
# - BATTERY OPTIMIZATION: Smart polling, event-driven UI updates
# """

# from pathlib import Path
# import signal
# import sys
# from typing import Optional

# from PyQt6.QtCore import Qt, QTimer
# from PyQt6.QtWidgets import QApplication, QMessageBox

# from .core.config import get_config
# from .core.constants import APP_ID, APP_NAME, APP_VERSION, DEBUG
# from .core.decorators import singleton
# from .core.logging_config import get_logger, log_audit, setup_logging
# from .services.alarm_service import AlarmService
# from .services.automation_hooks import AutomationHookManager
# from .services.backup_restore import BackupRestoreService
# from .services.battery_poller import BatteryPoller
# from .services.battery_report import BatteryReportService
# from .services.calibration import CalibrationService
# from .services.heartbeat import get_heartbeat_service
# from .services.power_draw import get_power_draw_monitor
# from .services.watchdog import WatchdogService
# from .services.weekly_report import WeeklyReportService
# from .ui.dashboard import DashboardWindow
# from .ui.tray import TrayIcon

# logger = get_logger(__name__)


# @singleton
# class VoltSentryApplication:
#     """
#     Main application class that orchestrates all components.

#     Connects:
#     - Battery Poller → Dashboard
#     - Battery Poller → Tray
#     - Alarm Service → Dashboard & Tray
#     - Heartbeat → Watchdog
#     """

#     def __init__(self):
#         self._app: Optional[QApplication] = None
#         self._poller: Optional[BatteryPoller] = None
#         self._alarm_service: Optional[AlarmService] = None
#         self._dashboard: Optional[DashboardWindow] = None
#         self._tray: Optional[TrayIcon] = None
#         self._watchdog: Optional[WatchdogService] = None
#         self._heartbeat_timer: Optional[QTimer] = None
#         self._report_service: Optional[BatteryReportService] = None
#         self._weekly_report: Optional[WeeklyReportService] = None

#         self._initialized = False
#         self._running = False

#         logger.info("VoltSentryApplication instance created")

#     def initialize(self) -> bool:
#         """
#         Initialize the application.

#         Returns:
#             True if initialization was successful
#         """
#         if self._initialized:
#             logger.warning("Application already initialized")
#             return True

#         try:
#             # Setup logging
#             setup_logging(verbose=DEBUG, is_production=not DEBUG)
#             logger.info("=" * 60)
#             logger.info("%s v%s starting up", APP_NAME, APP_VERSION)
#             logger.info("App ID: %s", APP_ID)
#             logger.info("Debug mode: %s", DEBUG)
#             logger.info("=" * 60)
#             log_audit("INFO", f"{APP_NAME} v{APP_VERSION} started")

#             # Load config
#             config = get_config()
#             settings = config.settings
#             logger.info(
#                 "Config loaded: thresholds %d%%/%d%%, poll %ds",
#                 settings.charge_threshold_high,
#                 settings.charge_threshold_low,
#                 settings.poll_interval_seconds,
#             )

#             # Create QApplication
#             self._app = QApplication(sys.argv)
#             self._app.setApplicationName(APP_NAME)
#             self._app.setApplicationVersion(APP_VERSION)
#             self._app.setQuitOnLastWindowClosed(
#                 False
#             )  # Keep running when dashboard closed

#             # Setup signal handlers for graceful shutdown
#             signal.signal(signal.SIGINT, self._signal_handler)
#             signal.signal(signal.SIGTERM, self._signal_handler)

#             # Create services
#             self._create_services()

#             # Create UI
#             self._create_ui()

#             # Connect signals
#             self._connect_signals()

#             # Start services
#             self._start_services()

#             self._initialized = True
#             logger.info("Application initialized successfully")
#             return True

#         except Exception as e:
#             logger.critical(
#                 "Failed to initialize application: %s", e, exc_info=True
#             )
#             log_audit("CRITICAL", f"Application initialization failed: {e}")

#             if self._app:
#                 QMessageBox.critical(
#                     None,
#                     f"{APP_NAME} - Startup Error",
#                     f"Failed to start {APP_NAME}:\n\n{e}\n\nPlease check the logs for details.",
#                 )
#             return False

#     def _create_services(self) -> None:
#         """Create all services."""
#         logger.info("Creating services...")

#         # Heartbeat (for watchdog)
#         self._heartbeat = get_heartbeat_service()

#         # Battery Report Service
#         self._report_service = BatteryReportService()

#         # Power Draw Monitor
#         self._power_draw = get_power_draw_monitor()

#         # Battery Poller
#         self._poller = BatteryPoller(
#             poll_interval=get_config().settings.poll_interval_seconds
#         )

#         # Alarm Service
#         self._alarm_service = AlarmService()

#         # Weekly Report
#         self._weekly_report = WeeklyReportService()

#         # Watchdog
#         self._watchdog = WatchdogService()

#         # Calibration
#         self._calibration = CalibrationService(
#             poller=self._poller, alarm_service=self._alarm_service
#         )

#         # Automation Hooks
#         self._automation = AutomationHookManager()

#         # Backup/Restore
#         self._backup_restore = BackupRestoreService()

#         logger.info("All services created")

#     def _create_ui(self) -> None:
#         """Create UI components."""
#         logger.info("Creating UI...")

#         # Dashboard
#         self._dashboard = DashboardWindow(
#             poller=self._poller, alarm_service=self._alarm_service
#         )

#         # Tray
#         self._tray = TrayIcon(parent=self._dashboard)

#         logger.info("UI created")

#     def _connect_signals(self) -> None:
#         """Connect all signals between components."""
#         logger.info("Connecting signals...")

#         # ============================================================
#         # 1. Battery Poller → Dashboard
#         # ============================================================
#         if self._poller and self._dashboard:
#             self._poller.reading_updated.connect(
#                 self._dashboard._on_reading_updated
#             )
#             self._poller.state_changed.connect(
#                 self._dashboard._on_state_changed
#             )
#             self._poller.error_occurred.connect(
#                 self._dashboard._on_poller_error
#             )
#             logger.debug("Poller → Dashboard connected")

#         # ============================================================
#         # 2. Battery Poller → Tray
#         # ============================================================
#         if self._poller and self._tray:
#             self._poller.reading_updated.connect(
#                 lambda r: self._tray.update_battery(r.percent, r.is_charging)
#             )
#             self._poller.error_occurred.connect(
#                 lambda e: self._tray.setToolTip(f"⚠️ Error: {e}")
#             )
#             logger.debug("Poller → Tray connected")

#         # ============================================================
#         # 3. Battery Poller → Alarm Service
#         # ============================================================
#         if self._poller and self._alarm_service:
#             self._poller.reading_updated.connect(
#                 self._alarm_service.process_reading
#             )
#             logger.debug("Poller → Alarm Service connected")

#         # ============================================================
#         # 4. Battery Poller → Heartbeat
#         # ============================================================
#         if self._poller and self._heartbeat:
#             self._poller.reading_updated.connect(
#                 lambda r: self._heartbeat.beat()
#             )
#             logger.debug("Poller → Heartbeat connected")

#         # ============================================================
#         # 5. ⚠️ CRITICAL FIX: Alarm Service → Tray
#         # ============================================================
#         if self._alarm_service and self._tray:
#             # THIS WAS MISSING - sets the tray reference in AlarmService
#             self._alarm_service.set_tray(self._tray)
#             logger.info("✅ Alarm Service → Tray connected (set_tray)")

#         # ============================================================
#         # 6. Alarm Service → Dashboard (via state machine)
#         # ============================================================
#         if self._alarm_service and self._dashboard:
#             # Alarm state changes are handled via the state machine
#             # which already triggers the dashboard via _show_alarm_banner
#             logger.debug(
#                 "Alarm Service → Dashboard connected (via state machine)"
#             )

#         # ============================================================
#         # 7. Tray → Dashboard
#         # ============================================================
#         if self._tray and self._dashboard:
#             self._tray.dashboard_requested.connect(
#                 self._dashboard.show_event
#             )
#             self._tray.settings_requested.connect(
#                 lambda: self._dashboard._tab_widget.setCurrentIndex(0)
#             )
#             self._tray.pause_toggled.connect(self._on_pause_toggled)
#             self._tray.alarm_triggered.connect(self._on_tray_alarm_triggered)
#             self._tray.exit_requested.connect(self.shutdown)
#             logger.debug("Tray → Dashboard connected")

#         # ============================================================
#         # 8. Calibration → Dashboard
#         # ============================================================
#         if self._calibration and self._dashboard:
#             # Calibration will update dashboard via callbacks
#             logger.debug("Calibration → Dashboard connected")

#         # ============================================================
#         # 9. Watchdog → Tray (for failure notifications)
#         # ============================================================
#         if self._watchdog and self._tray:
#             self._watchdog.add_failure_callback(
#                 lambda msg: self._tray.setToolTip(f"⚠️ {msg}")
#             )
#             logger.debug("Watchdog → Tray connected")

#         logger.info("All signals connected")

#     def _start_services(self) -> None:
#         """Start all services."""
#         logger.info("Starting services...")

#         # Start poller
#         if self._poller:
#             self._poller.start()
#             logger.info("Battery poller started")

#         # Start heartbeat timer
#         self._heartbeat_timer = QTimer()
#         self._heartbeat_timer.timeout.connect(self._heartbeat.beat)
#         self._heartbeat_timer.start(5000)  # Every 5 seconds
#         logger.info("Heartbeat timer started")

#         # Start watchdog
#         if self._watchdog:
#             self._watchdog.start()
#             logger.info("Watchdog started")

#         # Show tray
#         if self._tray:
#             self._tray.show_tray()
#             logger.info("Tray icon shown")

#         # Don't auto-show dashboard - let user open via tray
#         if self._dashboard:
#             logger.info("Dashboard ready (click tray icon to open)")

#         self._running = True
#         logger.info("All services started")

#     def _on_pause_toggled(self, paused: bool) -> None:
#         """Handle pause toggle from tray."""
#         if paused:
#             if self._poller:
#                 self._poller.stop()
#             logger.info("Monitoring paused")
#         else:
#             if self._poller:
#                 self._poller.start()
#             logger.info("Monitoring resumed")

#         # Update dashboard status
#         if self._dashboard:
#             status = "⏸️ Paused" if paused else "▶️ Running"
#             self._dashboard.statusBar().showMessage(f"Monitoring: {status}")

#     def _on_tray_alarm_triggered(self, action: str) -> None:
#         """Handle alarm action from tray."""
#         if action == "snooze" and self._alarm_service:
#             self._alarm_service.snooze_alarm()
#             logger.info("Alarm snoozed from tray")

#     def run(self) -> int:
#         """
#         Run the application main loop.

#         Returns:
#             Exit code
#         """
#         if not self._initialized:
#             logger.error("Cannot run: application not initialized")
#             return 1

#         logger.info("Application entering main loop")
#         try:
#             return self._app.exec()
#         except Exception as e:
#             logger.critical("Application crashed: %s", e, exc_info=True)
#             return 1

#     def shutdown(self) -> None:
#         """Gracefully shutdown the application."""
#         logger.info("Shutting down...")
#         log_audit("INFO", "Application shutting down")

#         self._running = False

#         # Stop timer
#         if self._heartbeat_timer:
#             self._heartbeat_timer.stop()

#         # Stop services
#         if self._watchdog:
#             self._watchdog.stop()

#         if self._poller:
#             self._poller.stop()

#         # Hide tray
#         if self._tray:
#             self._tray.hide_tray()

#         # Close dashboard
#         if self._dashboard:
#             self._dashboard.close()

#         # Quit app
#         if self._app:
#             self._app.quit()

#         logger.info("Shutdown complete")

#     def _signal_handler(self, signum: int, frame) -> None:
#         """Handle SIGINT/SIGTERM for graceful shutdown."""
#         logger.info("Received signal %d, shutting down...", signum)
#         self.shutdown()

#     def get_status(self) -> dict:
#         """Get application status."""
#         return {
#             "initialized": self._initialized,
#             "running": self._running,
#             "poller": self._poller.get_state_info() if self._poller else None,
#             "alarm": (
#                 self._alarm_service.get_status()
#                 if self._alarm_service
#                 else None
#             ),
#             "heartbeat": (
#                 self._heartbeat.get_status() if self._heartbeat else None
#             ),
#             "watchdog": (
#                 self._watchdog.get_status() if self._watchdog else None
#             ),
#             "tray_visible": self._tray.isVisible() if self._tray else False,
#             "dashboard_visible": (
#                 self._dashboard.isVisible() if self._dashboard else False
#             ),
#         }


# # ============================================================================
# # Convenience function
# # ============================================================================
# def create_app() -> Optional[VoltSentryApplication]:
#     """Create and initialize the application."""
#     app = VoltSentryApplication()
#     if app.initialize():
#         return app
#     return None


# # ============================================================================
# # Main entry point
# # ============================================================================
# def main() -> int:
#     """Main entry point for the application."""
#     app = create_app()
#     if app is None:
#         return 1
#     return app.run()


# if __name__ == "__main__":
#     sys.exit(main())










































































# """
# FILE: src/voltsentry/app.py
# PATH: voltsentry/src/voltsentry/app.py
# DESCRIPTION: Main application entry point - connects all components
# PHASE: 5 - Integration & Testing

# DISCIPLINES:
# - 0.1 Logging: INFO on startup/shutdown, ERROR on failures
# - 0.2 Error Handling: Graceful shutdown on errors
# - 0.4 Fallback: Tray fallback if unavailable
# - BATTERY OPTIMIZATION: Smart polling, event-driven UI updates
# """

# from pathlib import Path
# import signal
# import sys
# import ctypes
# from typing import Optional

# from PyQt6.QtCore import Qt, QTimer
# from PyQt6.QtWidgets import QApplication, QMessageBox
# from PyQt6.QtGui import QIcon

# from .core.config import get_config
# from .core.constants import APP_ID, APP_NAME, APP_VERSION, DEBUG
# from .core.decorators import singleton
# from .core.logging_config import get_logger, log_audit, setup_logging
# from .services.alarm_service import AlarmService
# from .services.automation_hooks import AutomationHookManager
# from .services.backup_restore import BackupRestoreService
# from .services.battery_poller import BatteryPoller
# from .services.battery_report import BatteryReportService
# from .services.calibration import CalibrationService
# from .services.heartbeat import get_heartbeat_service
# from .services.power_draw import get_power_draw_monitor
# from .services.watchdog import WatchdogService
# from .services.weekly_report import WeeklyReportService
# from .ui.dashboard import DashboardWindow
# from .ui.tray import TrayIcon

# # ✅ Import from utils to avoid circular import
# from .utils import get_resource_path

# logger = get_logger(__name__)


# def load_app_icon(app: QApplication) -> bool:
#     """
#     Load the application icon dynamically.
    
#     Args:
#         app: QApplication instance
    
#     Returns:
#         True if icon was loaded, False otherwise
#     """
#     # Try PNG first (better quality for window header)
#     icon_path = get_resource_path("assets/icon.png")
    
#     if icon_path.exists():
#         app.setWindowIcon(QIcon(str(icon_path)))
#         logger.info("✅ Application icon loaded from: %s", icon_path)
#         return True
    
#     # Try ICO as fallback (better for .exe)
#     icon_path = get_resource_path("assets/icon.ico")
#     if icon_path.exists():
#         app.setWindowIcon(QIcon(str(icon_path)))
#         logger.info("✅ Application icon loaded from: %s", icon_path)
#         return True
    
#     logger.warning("⚠️ No icon found in assets folder")
#     return False


# @singleton
# class VoltSentryApplication:
#     """
#     Main application class that orchestrates all components.

#     Connects:
#     - Battery Poller → Dashboard
#     - Battery Poller → Tray
#     - Alarm Service → Dashboard & Tray
#     - Heartbeat → Watchdog
#     """

#     def __init__(self):
#         self._app: Optional[QApplication] = None
#         self._poller: Optional[BatteryPoller] = None
#         self._alarm_service: Optional[AlarmService] = None
#         self._dashboard: Optional[DashboardWindow] = None
#         self._tray: Optional[TrayIcon] = None
#         self._watchdog: Optional[WatchdogService] = None
#         self._heartbeat_timer: Optional[QTimer] = None
#         self._report_service: Optional[BatteryReportService] = None
#         self._weekly_report: Optional[WeeklyReportService] = None

#         self._initialized = False
#         self._running = False

#         logger.info("VoltSentryApplication instance created")

#     def initialize(self) -> bool:
#         """
#         Initialize the application.

#         Returns:
#             True if initialization was successful
#         """
#         if self._initialized:
#             logger.warning("Application already initialized")
#             return True

#         try:
#             # Setup logging
#             setup_logging(verbose=DEBUG, is_production=not DEBUG)
#             logger.info("=" * 60)
#             logger.info("%s v%s starting up", APP_NAME, APP_VERSION)
#             logger.info("App ID: %s", APP_ID)
#             logger.info("Debug mode: %s", DEBUG)
#             logger.info("=" * 60)
#             log_audit("INFO", f"{APP_NAME} v{APP_VERSION} started")

#             # Load config
#             config = get_config()
#             settings = config.settings
#             logger.info(
#                 "Config loaded: thresholds %d%%/%d%%, poll %ds",
#                 settings.charge_threshold_high,
#                 settings.charge_threshold_low,
#                 settings.poll_interval_seconds,
#             )

#             # ============================================================
#             # CREATE QApplication WITH ICON SUPPORT
#             # ============================================================
#             self._app = QApplication(sys.argv)
#             self._app.setApplicationName(APP_NAME)
#             self._app.setApplicationVersion(APP_VERSION)
#             self._app.setQuitOnLastWindowClosed(False)

#             # ✅ Set AppUserModelID for Windows taskbar icon
#             app_id = "voltsentry.battery.monitor.1.0"
#             try:
#                 ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
#                 logger.info("✅ AppUserModelID set: %s", app_id)
#             except Exception as e:
#                 logger.debug("AppUserModelID not set (non-Windows or error): %s", e)

#             # ✅ Load application icon dynamically
#             load_app_icon(self._app)

#             # Setup signal handlers for graceful shutdown
#             signal.signal(signal.SIGINT, self._signal_handler)
#             signal.signal(signal.SIGTERM, self._signal_handler)

#             # Create services
#             self._create_services()

#             # Create UI
#             self._create_ui()

#             # Connect signals
#             self._connect_signals()

#             # Start services
#             self._start_services()

#             self._initialized = True
#             logger.info("Application initialized successfully")
#             return True

#         except Exception as e:
#             logger.critical(
#                 "Failed to initialize application: %s", e, exc_info=True
#             )
#             log_audit("CRITICAL", f"Application initialization failed: {e}")

#             if self._app:
#                 QMessageBox.critical(
#                     None,
#                     f"{APP_NAME} - Startup Error",
#                     f"Failed to start {APP_NAME}:\n\n{e}\n\nPlease check the logs for details.",
#                 )
#             return False

#     def _create_services(self) -> None:
#         """Create all services."""
#         logger.info("Creating services...")

#         # Heartbeat (for watchdog)
#         self._heartbeat = get_heartbeat_service()

#         # Battery Report Service
#         self._report_service = BatteryReportService()

#         # Power Draw Monitor
#         self._power_draw = get_power_draw_monitor()

#         # Battery Poller
#         self._poller = BatteryPoller(
#             poll_interval=get_config().settings.poll_interval_seconds
#         )

#         # Alarm Service
#         self._alarm_service = AlarmService()

#         # Weekly Report
#         self._weekly_report = WeeklyReportService()

#         # Watchdog
#         self._watchdog = WatchdogService()

#         # Calibration
#         self._calibration = CalibrationService(
#             poller=self._poller, alarm_service=self._alarm_service
#         )

#         # Automation Hooks
#         self._automation = AutomationHookManager()

#         # Backup/Restore
#         self._backup_restore = BackupRestoreService()

#         logger.info("All services created")

#     def _create_ui(self) -> None:
#         """Create UI components."""
#         logger.info("Creating UI...")

#         # Dashboard - icon is set globally via QApplication
#         self._dashboard = DashboardWindow(
#             poller=self._poller, alarm_service=self._alarm_service
#         )

#         # Tray
#         self._tray = TrayIcon(parent=self._dashboard)

#         logger.info("UI created")

#     def _connect_signals(self) -> None:
#         """Connect all signals between components."""
#         logger.info("Connecting signals...")

#         # ============================================================
#         # 1. Battery Poller → Dashboard
#         # ============================================================
#         if self._poller and self._dashboard:
#             self._poller.reading_updated.connect(
#                 self._dashboard._on_reading_updated
#             )
#             self._poller.state_changed.connect(
#                 self._dashboard._on_state_changed
#             )
#             self._poller.error_occurred.connect(
#                 self._dashboard._on_poller_error
#             )
#             logger.debug("Poller → Dashboard connected")

#         # ============================================================
#         # 2. Battery Poller → Tray
#         # ============================================================
#         if self._poller and self._tray:
#             self._poller.reading_updated.connect(
#                 lambda r: self._tray.update_battery(r.percent, r.is_charging)
#             )
#             self._poller.error_occurred.connect(
#                 lambda e: self._tray.setToolTip(f"⚠️ Error: {e}")
#             )
#             logger.debug("Poller → Tray connected")

#         # ============================================================
#         # 3. Battery Poller → Alarm Service
#         # ============================================================
#         if self._poller and self._alarm_service:
#             self._poller.reading_updated.connect(
#                 self._alarm_service.process_reading
#             )
#             logger.debug("Poller → Alarm Service connected")

#         # ============================================================
#         # 4. Battery Poller → Heartbeat
#         # ============================================================
#         if self._poller and self._heartbeat:
#             self._poller.reading_updated.connect(
#                 lambda r: self._heartbeat.beat()
#             )
#             logger.debug("Poller → Heartbeat connected")

#         # ============================================================
#         # 5. ⚠️ CRITICAL FIX: Alarm Service → Tray
#         # ============================================================
#         if self._alarm_service and self._tray:
#             self._alarm_service.set_tray(self._tray)
#             logger.info("✅ Alarm Service → Tray connected (set_tray)")

#         # ============================================================
#         # 6. Alarm Service → Dashboard (via state machine)
#         # ============================================================
#         if self._alarm_service and self._dashboard:
#             logger.debug(
#                 "Alarm Service → Dashboard connected (via state machine)"
#             )

#         # ============================================================
#         # 7. Tray → Dashboard
#         # ============================================================
#         if self._tray and self._dashboard:
#             self._tray.dashboard_requested.connect(
#                 self._dashboard.show_event
#             )
#             self._tray.settings_requested.connect(
#                 lambda: self._dashboard._tab_widget.setCurrentIndex(0)
#             )
#             self._tray.pause_toggled.connect(self._on_pause_toggled)
#             self._tray.alarm_triggered.connect(self._on_tray_alarm_triggered)
#             self._tray.exit_requested.connect(self.shutdown)
#             logger.debug("Tray → Dashboard connected")

#         # ============================================================
#         # 8. Calibration → Dashboard
#         # ============================================================
#         if self._calibration and self._dashboard:
#             logger.debug("Calibration → Dashboard connected")

#         # ============================================================
#         # 9. Watchdog → Tray (for failure notifications)
#         # ============================================================
#         if self._watchdog and self._tray:
#             self._watchdog.add_failure_callback(
#                 lambda msg: self._tray.setToolTip(f"⚠️ {msg}")
#             )
#             logger.debug("Watchdog → Tray connected")

#         logger.info("All signals connected")

#     def _start_services(self) -> None:
#         """Start all services."""
#         logger.info("Starting services...")

#         # Start poller
#         if self._poller:
#             self._poller.start()
#             logger.info("Battery poller started")

#         # Start heartbeat timer
#         self._heartbeat_timer = QTimer()
#         self._heartbeat_timer.timeout.connect(self._heartbeat.beat)
#         self._heartbeat_timer.start(5000)  # Every 5 seconds
#         logger.info("Heartbeat timer started")

#         # Start watchdog
#         if self._watchdog:
#             self._watchdog.start()
#             logger.info("Watchdog started")

#         # Show tray
#         if self._tray:
#             self._tray.show_tray()
#             logger.info("Tray icon shown")

#         # Don't auto-show dashboard - let user open via tray
#         if self._dashboard:
#             logger.info("Dashboard ready (click tray icon to open)")

#         self._running = True
#         logger.info("All services started")

#     def _on_pause_toggled(self, paused: bool) -> None:
#         """Handle pause toggle from tray."""
#         if paused:
#             if self._poller:
#                 self._poller.stop()
#             logger.info("Monitoring paused")
#         else:
#             if self._poller:
#                 self._poller.start()
#             logger.info("Monitoring resumed")

#         # Update dashboard status
#         if self._dashboard:
#             status = "⏸️ Paused" if paused else "▶️ Running"
#             self._dashboard.statusBar().showMessage(f"Monitoring: {status}")

#     def _on_tray_alarm_triggered(self, action: str) -> None:
#         """Handle alarm action from tray."""
#         if action == "snooze" and self._alarm_service:
#             self._alarm_service.snooze_alarm()
#             logger.info("Alarm snoozed from tray")

#     def run(self) -> int:
#         """
#         Run the application main loop.

#         Returns:
#             Exit code
#         """
#         if not self._initialized:
#             logger.error("Cannot run: application not initialized")
#             return 1

#         logger.info("Application entering main loop")
#         try:
#             return self._app.exec()
#         except Exception as e:
#             logger.critical("Application crashed: %s", e, exc_info=True)
#             return 1

#     def shutdown(self) -> None:
#         """Gracefully shutdown the application."""
#         logger.info("Shutting down...")
#         log_audit("INFO", "Application shutting down")

#         self._running = False

#         # Stop timer
#         if self._heartbeat_timer:
#             self._heartbeat_timer.stop()

#         # Stop services
#         if self._watchdog:
#             self._watchdog.stop()

#         if self._poller:
#             self._poller.stop()

#         # Hide tray
#         if self._tray:
#             self._tray.hide_tray()

#         # Close dashboard
#         if self._dashboard:
#             self._dashboard.close()

#         # Quit app
#         if self._app:
#             self._app.quit()

#         logger.info("Shutdown complete")

#     def _signal_handler(self, signum: int, frame) -> None:
#         """Handle SIGINT/SIGTERM for graceful shutdown."""
#         logger.info("Received signal %d, shutting down...", signum)
#         self.shutdown()

#     def get_status(self) -> dict:
#         """Get application status."""
#         return {
#             "initialized": self._initialized,
#             "running": self._running,
#             "poller": self._poller.get_state_info() if self._poller else None,
#             "alarm": (
#                 self._alarm_service.get_status()
#                 if self._alarm_service
#                 else None
#             ),
#             "heartbeat": (
#                 self._heartbeat.get_status() if self._heartbeat else None
#             ),
#             "watchdog": (
#                 self._watchdog.get_status() if self._watchdog else None
#             ),
#             "tray_visible": self._tray.isVisible() if self._tray else False,
#             "dashboard_visible": (
#                 self._dashboard.isVisible() if self._dashboard else False
#             ),
#         }


# # ============================================================================
# # Convenience function
# # ============================================================================
# def create_app() -> Optional[VoltSentryApplication]:
#     """Create and initialize the application."""
#     app = VoltSentryApplication()
#     if app.initialize():
#         return app
#     return None


# # ============================================================================
# # Main entry point
# # ============================================================================
# def main() -> int:
#     """Main entry point for the application."""
#     app = create_app()
#     if app is None:
#         return 1
#     return app.run()


# if __name__ == "__main__":
#     sys.exit(main())




















































































"""
FILE: src/voltsentry/app.py
PATH: voltsentry/src/voltsentry/app.py
DESCRIPTION: Main application entry point - connects all components
PHASE: 5 - Integration & Testing

DISCIPLINES:
- 0.1 Logging: INFO on startup/shutdown, ERROR on failures
- 0.2 Error Handling: Graceful shutdown on errors
- 0.4 Fallback: Tray fallback if unavailable
- BATTERY OPTIMIZATION: Smart polling, event-driven UI updates
"""

from pathlib import Path
import signal
import sys
import ctypes
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from .core.config import get_config
from .core.constants import APP_ID, APP_NAME, APP_VERSION, DEBUG
from .core.decorators import singleton
from .core.logging_config import get_logger, log_audit, setup_logging
from .services.alarm_service import AlarmService
from .services.automation_hooks import AutomationHookManager
from .services.backup_restore import BackupRestoreService
from .services.battery_poller import BatteryPoller
from .services.battery_report import BatteryReportService
from .services.calibration import CalibrationService
from .services.heartbeat import get_heartbeat_service
from .services.power_draw import get_power_draw_monitor
from .services.watchdog import WatchdogService
from .services.weekly_report import WeeklyReportService
from .ui.dashboard import DashboardWindow
from .ui.tray import TrayIcon

# ✅ Import from utils
from .utils import get_resource_path, set_auto_start, is_auto_start_enabled

logger = get_logger(__name__)


def load_app_icon(app: QApplication) -> bool:
    """
    Load the application icon dynamically.
    
    Args:
        app: QApplication instance
    
    Returns:
        True if icon was loaded, False otherwise
    """
    # Try PNG first (better quality for window header)
    icon_path = get_resource_path("assets/icon.png")
    
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.info("✅ Application icon loaded from: %s", icon_path)
        return True
    
    # Try ICO as fallback (better for .exe)
    icon_path = get_resource_path("assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.info("✅ Application icon loaded from: %s", icon_path)
        return True
    
    logger.warning("⚠️ No icon found in assets folder")
    return False


@singleton
class VoltSentryApplication:
    """
    Main application class that orchestrates all components.

    Connects:
    - Battery Poller → Dashboard
    - Battery Poller → Tray
    - Alarm Service → Dashboard & Tray
    - Heartbeat → Watchdog
    """

    def __init__(self):
        self._app: Optional[QApplication] = None
        self._poller: Optional[BatteryPoller] = None
        self._alarm_service: Optional[AlarmService] = None
        self._dashboard: Optional[DashboardWindow] = None
        self._tray: Optional[TrayIcon] = None
        self._watchdog: Optional[WatchdogService] = None
        self._heartbeat_timer: Optional[QTimer] = None
        self._report_service: Optional[BatteryReportService] = None
        self._weekly_report: Optional[WeeklyReportService] = None

        self._initialized = False
        self._running = False

        logger.info("VoltSentryApplication instance created")

    def initialize(self) -> bool:
        """
        Initialize the application.

        Returns:
            True if initialization was successful
        """
        if self._initialized:
            logger.warning("Application already initialized")
            return True

        try:
            # Setup logging
            setup_logging(verbose=DEBUG, is_production=not DEBUG)
            logger.info("=" * 60)
            logger.info("%s v%s starting up", APP_NAME, APP_VERSION)
            logger.info("App ID: %s", APP_ID)
            logger.info("Debug mode: %s", DEBUG)
            logger.info("=" * 60)
            log_audit("INFO", f"{APP_NAME} v{APP_VERSION} started")

            # ✅ Enable auto-start on first run (if not already enabled)
            if not is_auto_start_enabled():
                if set_auto_start(True):
                    logger.info("✅ Auto-start enabled for Windows boot")
                    log_audit("INFO", "Auto-start enabled on first run")
                else:
                    logger.warning("⚠️ Could not enable auto-start (permission issue)")

            # Load config
            config = get_config()
            settings = config.settings
            logger.info(
                "Config loaded: thresholds %d%%/%d%%, poll %ds",
                settings.charge_threshold_high,
                settings.charge_threshold_low,
                settings.poll_interval_seconds,
            )

            # ============================================================
            # CREATE QApplication WITH ICON SUPPORT
            # ============================================================
            self._app = QApplication(sys.argv)
            self._app.setApplicationName(APP_NAME)
            self._app.setApplicationVersion(APP_VERSION)
            self._app.setQuitOnLastWindowClosed(False)

            # ✅ Set AppUserModelID for Windows taskbar icon
            app_id = "voltsentry.battery.monitor.1.0"
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                logger.info("✅ AppUserModelID set: %s", app_id)
            except Exception as e:
                logger.debug("AppUserModelID not set (non-Windows or error): %s", e)

            # ✅ Load application icon dynamically
            load_app_icon(self._app)

            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Create services
            self._create_services()

            # Create UI
            self._create_ui()

            # Connect signals
            self._connect_signals()

            # Start services
            self._start_services()

            self._initialized = True
            logger.info("Application initialized successfully")
            return True

        except Exception as e:
            logger.critical(
                "Failed to initialize application: %s", e, exc_info=True
            )
            log_audit("CRITICAL", f"Application initialization failed: {e}")

            if self._app:
                QMessageBox.critical(
                    None,
                    f"{APP_NAME} - Startup Error",
                    f"Failed to start {APP_NAME}:\n\n{e}\n\nPlease check the logs for details.",
                )
            return False

    def _create_services(self) -> None:
        """Create all services."""
        logger.info("Creating services...")

        # Heartbeat (for watchdog)
        self._heartbeat = get_heartbeat_service()

        # Battery Report Service
        self._report_service = BatteryReportService()

        # Power Draw Monitor
        self._power_draw = get_power_draw_monitor()

        # Battery Poller
        self._poller = BatteryPoller(
            poll_interval=get_config().settings.poll_interval_seconds
        )

        # Alarm Service
        self._alarm_service = AlarmService()

        # Weekly Report
        self._weekly_report = WeeklyReportService()

        # Watchdog
        self._watchdog = WatchdogService()

        # Calibration
        self._calibration = CalibrationService(
            poller=self._poller, alarm_service=self._alarm_service
        )

        # Automation Hooks
        self._automation = AutomationHookManager()

        # Backup/Restore
        self._backup_restore = BackupRestoreService()

        logger.info("All services created")

    def _create_ui(self) -> None:
        """Create UI components."""
        logger.info("Creating UI...")

        # Dashboard - icon is set globally via QApplication
        self._dashboard = DashboardWindow(
            poller=self._poller, alarm_service=self._alarm_service
        )

        # Tray
        self._tray = TrayIcon(parent=self._dashboard)

        logger.info("UI created")

    def _connect_signals(self) -> None:
        """Connect all signals between components."""
        logger.info("Connecting signals...")

        # ============================================================
        # 1. Battery Poller → Dashboard
        # ============================================================
        if self._poller and self._dashboard:
            self._poller.reading_updated.connect(
                self._dashboard._on_reading_updated
            )
            self._poller.state_changed.connect(
                self._dashboard._on_state_changed
            )
            self._poller.error_occurred.connect(
                self._dashboard._on_poller_error
            )
            logger.debug("Poller → Dashboard connected")

        # ============================================================
        # 2. Battery Poller → Tray
        # ============================================================
        if self._poller and self._tray:
            self._poller.reading_updated.connect(
                lambda r: self._tray.update_battery(r.percent, r.is_charging)
            )
            self._poller.error_occurred.connect(
                lambda e: self._tray.setToolTip(f"⚠️ Error: {e}")
            )
            logger.debug("Poller → Tray connected")

        # ============================================================
        # 3. Battery Poller → Alarm Service
        # ============================================================
        if self._poller and self._alarm_service:
            self._poller.reading_updated.connect(
                self._alarm_service.process_reading
            )
            logger.debug("Poller → Alarm Service connected")

        # ============================================================
        # 4. Battery Poller → Heartbeat
        # ============================================================
        if self._poller and self._heartbeat:
            self._poller.reading_updated.connect(
                lambda r: self._heartbeat.beat()
            )
            logger.debug("Poller → Heartbeat connected")

        # ============================================================
        # 5. ⚠️ CRITICAL FIX: Alarm Service → Tray
        # ============================================================
        if self._alarm_service and self._tray:
            self._alarm_service.set_tray(self._tray)
            logger.info("✅ Alarm Service → Tray connected (set_tray)")

        # ============================================================
        # 6. Alarm Service → Dashboard (via state machine)
        # ============================================================
        if self._alarm_service and self._dashboard:
            logger.debug(
                "Alarm Service → Dashboard connected (via state machine)"
            )

        # ============================================================
        # 7. Tray → Dashboard
        # ============================================================
        if self._tray and self._dashboard:
            self._tray.dashboard_requested.connect(
                self._dashboard.show_event
            )
            self._tray.settings_requested.connect(
                lambda: self._dashboard._tab_widget.setCurrentIndex(0)
            )
            self._tray.pause_toggled.connect(self._on_pause_toggled)
            self._tray.alarm_triggered.connect(self._on_tray_alarm_triggered)
            self._tray.exit_requested.connect(self.shutdown)
            logger.debug("Tray → Dashboard connected")

        # ============================================================
        # 8. Calibration → Dashboard
        # ============================================================
        if self._calibration and self._dashboard:
            logger.debug("Calibration → Dashboard connected")

        # ============================================================
        # 9. Watchdog → Tray (for failure notifications)
        # ============================================================
        if self._watchdog and self._tray:
            self._watchdog.add_failure_callback(
                lambda msg: self._tray.setToolTip(f"⚠️ {msg}")
            )
            logger.debug("Watchdog → Tray connected")

        logger.info("All signals connected")

    def _start_services(self) -> None:
        """Start all services."""
        logger.info("Starting services...")

        # Start poller
        if self._poller:
            self._poller.start()
            logger.info("Battery poller started")

        # Start heartbeat timer
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._heartbeat.beat)
        self._heartbeat_timer.start(5000)  # Every 5 seconds
        logger.info("Heartbeat timer started")

        # Start watchdog
        if self._watchdog:
            self._watchdog.start()
            logger.info("Watchdog started")

        # Show tray
        if self._tray:
            self._tray.show_tray()
            logger.info("Tray icon shown")

        # Don't auto-show dashboard - let user open via tray
        if self._dashboard:
            logger.info("Dashboard ready (click tray icon to open)")

        self._running = True
        logger.info("All services started")

    def _on_pause_toggled(self, paused: bool) -> None:
        """Handle pause toggle from tray."""
        if paused:
            if self._poller:
                self._poller.stop()
            logger.info("Monitoring paused")
        else:
            if self._poller:
                self._poller.start()
            logger.info("Monitoring resumed")

        # Update dashboard status
        if self._dashboard:
            status = "⏸️ Paused" if paused else "▶️ Running"
            self._dashboard.statusBar().showMessage(f"Monitoring: {status}")

    def _on_tray_alarm_triggered(self, action: str) -> None:
        """Handle alarm action from tray."""
        if action == "snooze" and self._alarm_service:
            self._alarm_service.snooze_alarm()
            logger.info("Alarm snoozed from tray")

    def run(self) -> int:
        """
        Run the application main loop.

        Returns:
            Exit code
        """
        if not self._initialized:
            logger.error("Cannot run: application not initialized")
            return 1

        logger.info("Application entering main loop")
        try:
            return self._app.exec()
        except Exception as e:
            logger.critical("Application crashed: %s", e, exc_info=True)
            return 1

    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        logger.info("Shutting down...")
        log_audit("INFO", "Application shutting down")

        self._running = False

        # Stop timer
        if self._heartbeat_timer:
            self._heartbeat_timer.stop()

        # Stop services
        if self._watchdog:
            self._watchdog.stop()

        if self._poller:
            self._poller.stop()

        # Hide tray
        if self._tray:
            self._tray.hide_tray()

        # Close dashboard
        if self._dashboard:
            self._dashboard.close()

        # Quit app
        if self._app:
            self._app.quit()

        logger.info("Shutdown complete")

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        logger.info("Received signal %d, shutting down...", signum)
        self.shutdown()

    def get_status(self) -> dict:
        """Get application status."""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "poller": self._poller.get_state_info() if self._poller else None,
            "alarm": (
                self._alarm_service.get_status()
                if self._alarm_service
                else None
            ),
            "heartbeat": (
                self._heartbeat.get_status() if self._heartbeat else None
            ),
            "watchdog": (
                self._watchdog.get_status() if self._watchdog else None
            ),
            "tray_visible": self._tray.isVisible() if self._tray else False,
            "dashboard_visible": (
                self._dashboard.isVisible() if self._dashboard else False
            ),
        }


# ============================================================================
# Convenience function
# ============================================================================
def create_app() -> Optional[VoltSentryApplication]:
    """Create and initialize the application."""
    app = VoltSentryApplication()
    if app.initialize():
        return app
    return None


# ============================================================================
# Main entry point
# ============================================================================
def main() -> int:
    """Main entry point for the application."""
    app = create_app()
    if app is None:
        return 1
    return app.run()


if __name__ == "__main__":
    sys.exit(main())