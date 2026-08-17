# """
# FILE: src/voltsentry/ui/dashboard.py
# PATH: voltsentry/src/voltsentry/ui/dashboard.py
# DESCRIPTION: Main dashboard window with all panels
# PHASE: 4.2 - Dashboard Main Window

# DISCIPLINES:
# - 0.1 Logging: ERROR with panel name on failure
# - 0.2 Error Handling: Each panel has its own try/except
# - 0.4 Fallback: Panel shows placeholder on error
# """

# from datetime import datetime
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal
# from PyQt6.QtGui import QCloseEvent, QIcon
# from PyQt6.QtWidgets import (
#     QApplication,
#     QFrame,
#     QHBoxLayout,
#     QLabel,
#     QMainWindow,
#     QPushButton,
#     QTabWidget,
#     QVBoxLayout,
#     QWidget,
# )

# from ..core.config import get_config
# from ..core.constants import APP_ID, APP_NAME, APP_VERSION
# from ..core.decorators import log_entry_exit
# from ..core.logging_config import get_logger
# from ..core.types import BatteryReading
# from ..services.alarm_service import AlarmService
# from ..services.battery_poller import BatteryPoller
# from .health_graph import HealthGraph
# from .history_log import HistoryLogView
# from .settings_panel import SettingsPanel
# from .styles import COLORS, FONTS, MAIN_STYLESHEET, RADIUS, SPACING
# from .widgets.alert_banner import AlertBanner
# from .widgets.status_card import StatusCard

# logger = get_logger(__name__)


# class DashboardWindow(QMainWindow):
#     """
#     Main dashboard window.

#     Features:
#     - Status cards (battery %, health score, cycles)
#     - Alert banner
#     - Settings panel
#     - Health graph
#     - History log
#     - Each panel isolated with error handling
#     """

#     closed = pyqtSignal()

#     def __init__(
#         self,
#         poller: Optional[BatteryPoller] = None,
#         alarm_service: Optional[AlarmService] = None,
#     ):
#         super().__init__()

#         self._poller = poller
#         self._alarm_service = alarm_service
#         self._config = get_config()

#         self._setup_window()
#         self._setup_ui()
#         self._setup_signals()
#         self._update_ui()

#         logger.info("DashboardWindow initialized")

#     def _setup_window(self) -> None:
#         """Set up the main window properties."""
#         self.setWindowTitle(f"{APP_NAME} - Dashboard")
#         self.setWindowIcon(QIcon())
#         self.setMinimumSize(800, 600)
#         self.resize(900, 700)
#         self.setStyleSheet(MAIN_STYLESHEET)

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         central = QWidget()
#         self.setCentralWidget(central)

#         main_layout = QVBoxLayout(central)
#         main_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         main_layout.setSpacing(SPACING["md"])

#         # Header
#         self._setup_header(main_layout)

#         # Alert banner
#         self._alert_banner = AlertBanner(auto_dismiss_seconds=10, parent=self)
#         main_layout.addWidget(self._alert_banner)

#         # Status cards
#         self._setup_status_cards(main_layout)

#         # Tab widget
#         self._tab_widget = QTabWidget()

#         self._settings_panel = SettingsPanel(self._config, parent=self)
#         self._tab_widget.addTab(self._settings_panel, "⚙️ Settings")

#         self._health_graph = HealthGraph(parent=self)
#         self._tab_widget.addTab(self._health_graph, "📈 Health")

#         self._history_log = HistoryLogView(parent=self)
#         self._tab_widget.addTab(self._history_log, "📜 History")

#         main_layout.addWidget(self._tab_widget)

#         # Status bar
#         self._setup_status_bar()

#     def _setup_header(self, layout: QVBoxLayout) -> None:
#         """Set up the header section."""
#         header = QFrame()
#         header_layout = QHBoxLayout(header)
#         header_layout.setContentsMargins(0, 0, 0, SPACING["md"])

#         title = QLabel(f"🔋 {APP_NAME}")
#         title.setStyleSheet(f"""
#             font-size: {FONTS['size_large']};
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['gray_900']};
#         """)
#         header_layout.addWidget(title)
#         header_layout.addStretch()

#         version = QLabel(f"v{APP_VERSION}")
#         version.setStyleSheet(f"color: {COLORS['gray_500']};")
#         header_layout.addWidget(version)

#         layout.addWidget(header)

#     def _setup_status_cards(self, layout: QVBoxLayout) -> None:
#         """Set up the status cards row."""
#         cards_layout = QHBoxLayout()
#         cards_layout.setSpacing(SPACING["md"])

#         self._battery_card = StatusCard(
#             title="Battery Level",
#             value="--%",
#             subtitle="Status: Unknown",
#             icon="🔋",
#             status="info",
#             parent=self,
#         )
#         self._battery_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._battery_card)

#         self._health_card = StatusCard(
#             title="Battery Health",
#             value="--%",
#             subtitle="Cycles: --",
#             icon="❤️",
#             status="info",
#             parent=self,
#         )
#         self._health_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._health_card)

#         self._status_card = StatusCard(
#             title="Status",
#             value="--",
#             subtitle="Last updated: --",
#             icon="📊",
#             status="info",
#             parent=self,
#         )
#         cards_layout.addWidget(self._status_card)

#         # Actions card
#         self._actions_card = QFrame()
#         actions_layout = QVBoxLayout(self._actions_card)
#         actions_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         actions_layout.setSpacing(SPACING["sm"])

#         actions_title = QLabel("⚡ Actions")
#         actions_title.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             font-weight: {FONTS['weight_medium']};
#             color: {COLORS['gray_600']};
#         """)
#         actions_layout.addWidget(actions_title)

#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["sm"])

#         self._stop_alarm_btn = QPushButton("🔕 Stop Alarm")
#         self._stop_alarm_btn.setObjectName("dangerButton")
#         self._stop_alarm_btn.setEnabled(False)
#         self._stop_alarm_btn.clicked.connect(self._stop_alarm)
#         btn_layout.addWidget(self._stop_alarm_btn)

#         self._snooze_btn = QPushButton("😴 Snooze")
#         self._snooze_btn.setObjectName("primaryButton")
#         self._snooze_btn.setEnabled(False)
#         self._snooze_btn.clicked.connect(self._snooze_alarm)
#         btn_layout.addWidget(self._snooze_btn)

#         self._refresh_btn = QPushButton("🔄 Refresh")
#         self._refresh_btn.clicked.connect(self._refresh)
#         btn_layout.addWidget(self._refresh_btn)

#         actions_layout.addLayout(btn_layout)

#         self._actions_card.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {COLORS['gray_100']};
#                 border-radius: {RADIUS['lg']}px;
#             }}
#         """)

#         cards_layout.addWidget(self._actions_card)
#         layout.addLayout(cards_layout)

#     def _setup_status_bar(self) -> None:
#         """Set up the status bar."""
#         self.statusBar().showMessage(f"Ready | {APP_ID}")
#         self.statusBar().setStyleSheet(f"""
#             QStatusBar {{
#                 color: {COLORS['gray_500']};
#                 font-size: {FONTS['size_small']};
#             }}
#         """)

#     def _setup_signals(self) -> None:
#         """Connect signals from services."""
#         if self._poller:
#             self._poller.reading_updated.connect(self._on_reading_updated)
#             self._poller.state_changed.connect(self._on_state_changed)
#             self._poller.error_occurred.connect(self._on_poller_error)

#         self._settings_panel.settings_saved.connect(self._on_settings_saved)
#         self._alert_banner.dismissed.connect(lambda: logger.debug("Alert dismissed"))
#         self._alert_banner.snoozed.connect(self._snooze_alarm)

#     @log_entry_exit()
#     def _on_reading_updated(self, reading: BatteryReading) -> None:
#         """Handle new battery reading."""
#         try:
#             percent = reading.percent
#             is_charging = reading.is_charging

#             self._battery_card.set_value(f"{percent}%")
#             self._battery_card.set_subtitle(
#                 "⚡ Charging" if is_charging else "🔋 Discharging"
#             )

#             if percent >= 60:
#                 status = "success"
#             elif percent >= 20:
#                 status = "warning"
#             else:
#                 status = "danger"
#             self._battery_card.set_status(status)

#             status_text = "Charging" if is_charging else "Discharging"
#             self._status_card.set_value(status_text)
#             self._status_card.set_subtitle(
#                 f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
#             )

#             self.statusBar().showMessage(f"Battery: {percent}% | {status_text}")

#             if (
#                 self._alarm_service
#                 and self._alarm_service.state_machine.is_alarm_active
#             ):
#                 self._show_alarm_banner()

#         except Exception as e:
#             logger.error("Error updating UI from reading in panel status_cards: %s", e)
#             self._battery_card.set_value("ERROR")

#     def _on_state_changed(self, old_state: str, new_state: str) -> None:
#         """Handle state change."""
#         try:
#             self._status_card.set_subtitle(f"State: {new_state}")
#         except Exception as e:
#             logger.error("Error updating state UI in panel status_cards: %s", e)

#     def _on_poller_error(self, error_msg: str) -> None:
#         """Handle poller error."""
#         try:
#             self._alert_banner.show_alert(
#                 message=f"⚠️ {error_msg}",
#                 alert_type="warning",
#                 show_snooze=False,
#             )
#             self.statusBar().showMessage(f"Error: {error_msg}")
#         except Exception as e:
#             logger.error("Error showing poller error in panel alert_banner: %s", e)

#     def _on_settings_saved(self) -> None:
#         """Handle settings saved."""
#         try:
#             self.statusBar().showMessage("✅ Settings saved successfully", 3000)
#             self._refresh()
#         except Exception as e:
#             logger.error("Error after settings saved in panel settings: %s", e)

#     def _show_alarm_banner(self) -> None:
#         """Show alarm banner."""
#         try:
#             if self._alarm_service:
#                 alarm_type = self._alarm_service.alarm_manager.active_alarm
#                 if alarm_type:
#                     messages = {
#                         "full_charge": (
#                             "🔔 Battery fully charged! Unplug to extend battery life."
#                         ),
#                         "low_battery": "⚠️ Battery low! Plug in to charge.",
#                         "critical_low": "🔴 Battery critical! Plug in immediately!",
#                     }
#                     message = messages.get(alarm_type.value, "🔔 Alarm active!")
#                     alert_type = (
#                         "danger" if alarm_type.value == "critical_low" else "warning"
#                     )

#                     self._alert_banner.show_alert(
#                         message=message,
#                         alert_type=alert_type,
#                         show_snooze=True,
#                     )

#                     self._stop_alarm_btn.setEnabled(True)
#                     self._snooze_btn.setEnabled(True)
#         except Exception as e:
#             logger.error("Error showing alarm banner in panel alert_banner: %s", e)

#     def _stop_alarm(self) -> None:
#         """Stop the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.stop_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("🔕 Alarm stopped", 2000)
#         except Exception as e:
#             logger.error("Error stopping alarm in panel actions: %s", e)

#     def _snooze_alarm(self) -> None:
#         """Snooze the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.snooze_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("😴 Alarm snoozed for 15 minutes", 2000)
#         except Exception as e:
#             logger.error("Error snoozing alarm in panel actions: %s", e)

#     def _refresh(self) -> None:
#         """Refresh all data."""
#         try:
#             self._health_graph.refresh()
#             self._history_log.refresh()
#             self.statusBar().showMessage("🔄 Refreshed", 1000)
#         except Exception as e:
#             logger.error("Error refreshing in dashboard panels: %s", e)

#     def _update_ui(self) -> None:
#         """Initial UI update."""
#         self._settings_panel.load_settings()
#         self._health_graph.refresh()
#         self._history_log.refresh()

#     def show_event(self) -> None:
#         """Show and activate the window."""
#         self.show()
#         self.raise_()
#         self.activateWindow()

#     def closeEvent(self, event: QCloseEvent) -> None:
#         """Handle close event - just hide the window."""
#         event.ignore()
#         self.hide()
#         logger.debug("Dashboard hidden (not closed)")

#     def close_dashboard(self) -> None:
#         """Fully close the dashboard."""
#         self.close()

#     def __repr__(self) -> str:
#         return f"<DashboardWindow visible={self.isVisible()}>"


















































# """
# FILE: src/voltsentry/ui/dashboard.py
# PATH: voltsentry/src/voltsentry/ui/dashboard.py
# DESCRIPTION: Main dashboard window with all panels
# PHASE: 4.2 - Dashboard Main Window

# DISCIPLINES:
# - 0.1 Logging: ERROR with panel name on failure
# - 0.2 Error Handling: Each panel has its own try/except
# - 0.4 Fallback: Panel shows placeholder on error
# """

# from datetime import datetime
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QSize
# from PyQt6.QtGui import QCloseEvent, QIcon
# from PyQt6.QtWidgets import (
#     QApplication,
#     QFrame,
#     QHBoxLayout,
#     QLabel,
#     QMainWindow,
#     QPushButton,
#     QTabWidget,
#     QVBoxLayout,
#     QWidget,
#     QSizePolicy,
# )

# from ..core.config import get_config
# from ..core.constants import APP_ID, APP_NAME, APP_VERSION
# from ..core.decorators import log_entry_exit
# from ..core.logging_config import get_logger
# from ..core.types import BatteryReading
# from ..services.alarm_service import AlarmService
# from ..services.battery_poller import BatteryPoller
# from .health_graph import HealthGraph
# from .history_log import HistoryLogView
# from .settings_panel import SettingsPanel
# from .styles import COLORS, FONTS, MAIN_STYLESHEET, RADIUS, SPACING
# from .widgets.alert_banner import AlertBanner
# from .widgets.status_card import StatusCard

# logger = get_logger(__name__)


# class DashboardWindow(QMainWindow):
#     """
#     Main dashboard window.

#     Features:
#     - Status cards (battery %, health score, cycles)
#     - Alert banner
#     - Settings panel
#     - Health graph
#     - History log
#     - Each panel isolated with error handling
#     """

#     closed = pyqtSignal()

#     def __init__(
#         self,
#         poller: Optional[BatteryPoller] = None,
#         alarm_service: Optional[AlarmService] = None,
#     ):
#         super().__init__()

#         self._poller = poller
#         self._alarm_service = alarm_service
#         self._config = get_config()

#         self._setup_window()
#         self._setup_ui()
#         self._setup_signals()
#         self._update_ui()

#         logger.info("DashboardWindow initialized")

#     def _setup_window(self) -> None:
#         """Set up the main window properties."""
#         self.setWindowTitle(f"{APP_NAME} - Dashboard")
#         self.setWindowIcon(QIcon())
#         self.setMinimumSize(800, 600)
#         self.resize(900, 700)
#         self.setStyleSheet(MAIN_STYLESHEET)

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         central = QWidget()
#         self.setCentralWidget(central)

#         main_layout = QVBoxLayout(central)
#         main_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         main_layout.setSpacing(SPACING["md"])

#         # Header
#         self._setup_header(main_layout)

#         # Alert banner - EXPANDS LAYOUT (doesn't overlap)
#         self._alert_banner = AlertBanner(auto_dismiss_seconds=0, parent=self)
#         self._alert_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         self._alert_banner.setVisible(False)  # Hidden by default
#         main_layout.addWidget(self._alert_banner)

#         # Status cards
#         self._setup_status_cards(main_layout)

#         # Tab widget
#         self._tab_widget = QTabWidget()

#         self._settings_panel = SettingsPanel(self._config, parent=self)
#         self._tab_widget.addTab(self._settings_panel, "⚙️ Settings")

#         self._health_graph = HealthGraph(parent=self)
#         self._tab_widget.addTab(self._health_graph, "📈 Health")

#         self._history_log = HistoryLogView(parent=self)
#         self._tab_widget.addTab(self._history_log, "📜 History")

#         main_layout.addWidget(self._tab_widget)

#         # Status bar
#         self._setup_status_bar()

#     def _setup_header(self, layout: QVBoxLayout) -> None:
#         """Set up the header section."""
#         header = QFrame()
#         header_layout = QHBoxLayout(header)
#         header_layout.setContentsMargins(0, 0, 0, SPACING["md"])

#         title = QLabel(f"🔋 {APP_NAME}")
#         title.setStyleSheet(f"""
#             font-size: {FONTS['size_large']};
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['gray_900']};
#         """)
#         header_layout.addWidget(title)
#         header_layout.addStretch()

#         version = QLabel(f"v{APP_VERSION}")
#         version.setStyleSheet(f"color: {COLORS['gray_500']};")
#         header_layout.addWidget(version)

#         layout.addWidget(header)

#     def _setup_status_cards(self, layout: QVBoxLayout) -> None:
#         """Set up the status cards row."""
#         cards_layout = QHBoxLayout()
#         cards_layout.setSpacing(SPACING["md"])

#         self._battery_card = StatusCard(
#             title="Battery Level",
#             value="--%",
#             subtitle="Status: Unknown",
#             icon="🔋",
#             status="info",
#             parent=self,
#         )
#         self._battery_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._battery_card)

#         self._health_card = StatusCard(
#             title="Battery Health",
#             value="--%",
#             subtitle="Cycles: --",
#             icon="❤️",
#             status="info",
#             parent=self,
#         )
#         self._health_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._health_card)

#         self._status_card = StatusCard(
#             title="Status",
#             value="--",
#             subtitle="Last updated: --",
#             icon="📊",
#             status="info",
#             parent=self,
#         )
#         cards_layout.addWidget(self._status_card)

#         # Actions card
#         self._actions_card = QFrame()
#         actions_layout = QVBoxLayout(self._actions_card)
#         actions_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         actions_layout.setSpacing(SPACING["sm"])

#         actions_title = QLabel("⚡ Actions")
#         actions_title.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             font-weight: {FONTS['weight_medium']};
#             color: {COLORS['gray_600']};
#         """)
#         actions_layout.addWidget(actions_title)

#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["sm"])

#         self._stop_alarm_btn = QPushButton("🔕 Stop Alarm")
#         self._stop_alarm_btn.setObjectName("dangerButton")
#         self._stop_alarm_btn.setEnabled(False)
#         self._stop_alarm_btn.clicked.connect(self._stop_alarm)
#         btn_layout.addWidget(self._stop_alarm_btn)

#         self._snooze_btn = QPushButton("😴 Snooze")
#         self._snooze_btn.setObjectName("primaryButton")
#         self._snooze_btn.setEnabled(False)
#         self._snooze_btn.clicked.connect(self._snooze_alarm)
#         btn_layout.addWidget(self._snooze_btn)

#         self._refresh_btn = QPushButton("🔄 Refresh")
#         self._refresh_btn.clicked.connect(self._refresh)
#         btn_layout.addWidget(self._refresh_btn)

#         actions_layout.addLayout(btn_layout)

#         self._actions_card.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {COLORS['gray_100']};
#                 border-radius: {RADIUS['lg']}px;
#             }}
#         """)

#         cards_layout.addWidget(self._actions_card)
#         layout.addLayout(cards_layout)

#     def _setup_status_bar(self) -> None:
#         """Set up the status bar."""
#         self.statusBar().showMessage(f"Ready | {APP_ID}")
#         self.statusBar().setStyleSheet(f"""
#             QStatusBar {{
#                 color: {COLORS['gray_500']};
#                 font-size: {FONTS['size_small']};
#             }}
#         """)

#     def _setup_signals(self) -> None:
#         """Connect signals from services."""
#         if self._poller:
#             self._poller.reading_updated.connect(self._on_reading_updated)
#             self._poller.state_changed.connect(self._on_state_changed)
#             self._poller.error_occurred.connect(self._on_poller_error)

#         self._settings_panel.settings_saved.connect(self._on_settings_saved)
#         self._alert_banner.dismissed.connect(lambda: logger.debug("Alert dismissed"))
#         self._alert_banner.snoozed.connect(self._snooze_alarm)

#     @log_entry_exit()
#     def _on_reading_updated(self, reading: BatteryReading) -> None:
#         """Handle new battery reading."""
#         try:
#             percent = reading.percent
#             is_charging = reading.is_charging

#             self._battery_card.set_value(f"{percent}%")
#             self._battery_card.set_subtitle(
#                 "⚡ Charging" if is_charging else "🔋 Discharging"
#             )

#             if percent >= 60:
#                 status = "success"
#             elif percent >= 20:
#                 status = "warning"
#             else:
#                 status = "danger"
#             self._battery_card.set_status(status)

#             status_text = "Charging" if is_charging else "Discharging"
#             self._status_card.set_value(status_text)
#             self._status_card.set_subtitle(
#                 f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
#             )

#             self.statusBar().showMessage(f"Battery: {percent}% | {status_text}")

#             if (
#                 self._alarm_service
#                 and self._alarm_service.state_machine.is_alarm_active
#             ):
#                 self._show_alarm_banner()

#         except Exception as e:
#             logger.error("Error updating UI from reading in panel status_cards: %s", e)
#             self._battery_card.set_value("ERROR")

#     def _on_state_changed(self, old_state: str, new_state: str) -> None:
#         """Handle state change."""
#         try:
#             self._status_card.set_subtitle(f"State: {new_state}")
#         except Exception as e:
#             logger.error("Error updating state UI in panel status_cards: %s", e)

#     def _on_poller_error(self, error_msg: str) -> None:
#         """Handle poller error."""
#         try:
#             self._alert_banner.show_alert(
#                 message=f"⚠️ {error_msg}",
#                 alert_type="warning",
#                 show_snooze=False,
#             )
#             self.statusBar().showMessage(f"Error: {error_msg}")
#         except Exception as e:
#             logger.error("Error showing poller error in panel alert_banner: %s", e)

#     def _on_settings_saved(self) -> None:
#         """Handle settings saved - UPDATE ALARM SERVICE THRESHOLDS."""
#         try:
#             # Reload config to get latest values
#             self._config.load()
#             settings = self._config.settings

#             logger.info(
#                 "📊 Dashboard: Settings saved - high=%d%%, low=%d%%",
#                 settings.charge_threshold_high,
#                 settings.charge_threshold_low,
#             )

#             # ✅ Update AlarmService with new thresholds
#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(
#                     settings.charge_threshold_high,
#                     settings.charge_threshold_low,
#                 )
#                 logger.info("✅ AlarmService thresholds updated from Dashboard")

#             self.statusBar().showMessage("✅ Settings saved successfully", 3000)
#             self._refresh()
#         except Exception as e:
#             logger.error("Error after settings saved in panel settings: %s", e)

#     def _show_alarm_banner(self) -> None:
#         """Show alarm banner - PUSHES CONTENT DOWN."""
#         try:
#             if self._alarm_service:
#                 alarm_type = self._alarm_service.alarm_manager.active_alarm
#                 if alarm_type:
#                     messages = {
#                         "full_charge": (
#                             "🔔 Battery fully charged! Unplug to extend battery life."
#                         ),
#                         "low_battery": "⚠️ Battery low! Plug in to charge.",
#                         "critical_low": "🔴 Battery critical! Plug in immediately!",
#                     }
#                     message = messages.get(alarm_type.value, "🔔 Alarm active!")
#                     alert_type = (
#                         "danger" if alarm_type.value == "critical_low" else "warning"
#                     )

#                     # Show alert - THIS WILL PUSH CONTENT DOWN
#                     self._alert_banner.show_alert(
#                         message=message,
#                         alert_type=alert_type,
#                         show_snooze=True,
#                     )

#                     self._stop_alarm_btn.setEnabled(True)
#                     self._snooze_btn.setEnabled(True)
#         except Exception as e:
#             logger.error("Error showing alarm banner in panel alert_banner: %s", e)

#     def _stop_alarm(self) -> None:
#         """Stop the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.stop_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("🔕 Alarm stopped", 2000)
#         except Exception as e:
#             logger.error("Error stopping alarm in panel actions: %s", e)

#     def _snooze_alarm(self) -> None:
#         """Snooze the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.snooze_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("😴 Alarm snoozed for 15 minutes", 2000)
#         except Exception as e:
#             logger.error("Error snoozing alarm in panel actions: %s", e)

#     def _refresh(self) -> None:
#         """Refresh all data."""
#         try:
#             self._health_graph.refresh()
#             self._history_log.refresh()
#             self.statusBar().showMessage("🔄 Refreshed", 1000)
#         except Exception as e:
#             logger.error("Error refreshing in dashboard panels: %s", e)

#     def _update_ui(self) -> None:
#         """Initial UI update."""
#         self._settings_panel.load_settings()
#         self._health_graph.refresh()
#         self._history_log.refresh()

#     def show_event(self) -> None:
#         """Show and activate the window."""
#         self.show()
#         self.raise_()
#         self.activateWindow()

#     def closeEvent(self, event: QCloseEvent) -> None:
#         """Handle close event - just hide the window."""
#         event.ignore()
#         self.hide()
#         logger.debug("Dashboard hidden (not closed)")

#     def close_dashboard(self) -> None:
#         """Fully close the dashboard."""
#         self.close()

#     def __repr__(self) -> str:
#         return f"<DashboardWindow visible={self.isVisible()}>"











































































# """
# FILE: src/voltsentry/ui/dashboard.py
# PATH: voltsentry/src/voltsentry/ui/dashboard.py
# DESCRIPTION: Main dashboard window with all panels
# PHASE: 4.2 - Dashboard Main Window

# DISCIPLINES:
# - 0.1 Logging: ERROR with panel name on failure
# - 0.2 Error Handling: Each panel has its own try/except
# - 0.4 Fallback: Panel shows placeholder on error
# """

# from datetime import datetime
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QSize
# from PyQt6.QtGui import QCloseEvent, QIcon
# from PyQt6.QtWidgets import (
#     QApplication,
#     QFrame,
#     QHBoxLayout,
#     QLabel,
#     QMainWindow,
#     QPushButton,
#     QTabWidget,
#     QVBoxLayout,
#     QWidget,
#     QSizePolicy,
# )

# from ..core.config import get_config
# from ..core.constants import APP_ID, APP_NAME, APP_VERSION
# from ..core.decorators import log_entry_exit
# from ..core.logging_config import get_logger
# from ..core.types import BatteryReading
# from ..services.alarm_service import AlarmService
# from ..services.battery_poller import BatteryPoller
# from .health_graph import HealthGraph
# from .history_log import HistoryLogView
# from .settings_panel import SettingsPanel
# from .styles import COLORS, FONTS, MAIN_STYLESHEET, RADIUS, SPACING
# from .widgets.alert_banner import AlertBanner
# from .widgets.status_card import StatusCard

# logger = get_logger(__name__)


# class DashboardWindow(QMainWindow):
#     """
#     Main dashboard window.

#     Features:
#     - Status cards (battery %, health score, cycles)
#     - Alert banner
#     - Settings panel
#     - Health graph
#     - History log
#     - Each panel isolated with error handling
#     """

#     closed = pyqtSignal()

#     def __init__(
#         self,
#         poller: Optional[BatteryPoller] = None,
#         alarm_service: Optional[AlarmService] = None,
#     ):
#         super().__init__()

#         self._poller = poller
#         self._alarm_service = alarm_service
#         self._config = get_config()

#         self._setup_window()
#         self._setup_ui()
#         self._setup_signals()
#         self._update_ui()

#         logger.info("DashboardWindow initialized")

#     def _setup_window(self) -> None:
#         """Set up the main window properties."""
#         self.setWindowTitle(f"{APP_NAME} - Dashboard")
#         self.setMinimumSize(800, 600)
#         self.resize(900, 700)
#         self.setStyleSheet(MAIN_STYLESHEET)

#         # ✅ Load icon for the window
#         try:
#             from ..utils import get_resource_path
            
#             # Try PNG first (better quality)
#             icon_path = get_resource_path("assets/icon.png")
#             if icon_path.exists():
#                 self.setWindowIcon(QIcon(str(icon_path)))
#                 logger.info("✅ Dashboard window icon loaded from: %s", icon_path)
#             else:
#                 # Try ICO as fallback
#                 icon_path = get_resource_path("assets/icon.ico")
#                 if icon_path.exists():
#                     self.setWindowIcon(QIcon(str(icon_path)))
#                     logger.info("✅ Dashboard window icon loaded from: %s", icon_path)
#         except Exception as e:
#             logger.debug("Could not load window icon: %s", e)

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         central = QWidget()
#         self.setCentralWidget(central)

#         main_layout = QVBoxLayout(central)
#         main_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         main_layout.setSpacing(SPACING["md"])

#         # Header
#         self._setup_header(main_layout)

#         # Alert banner - EXPANDS LAYOUT (doesn't overlap)
#         self._alert_banner = AlertBanner(auto_dismiss_seconds=0, parent=self)
#         self._alert_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         self._alert_banner.setVisible(False)  # Hidden by default
#         main_layout.addWidget(self._alert_banner)

#         # Status cards
#         self._setup_status_cards(main_layout)

#         # Tab widget
#         self._tab_widget = QTabWidget()

#         self._settings_panel = SettingsPanel(self._config, parent=self)
#         self._tab_widget.addTab(self._settings_panel, "⚙️ Settings")

#         self._health_graph = HealthGraph(parent=self)
#         self._tab_widget.addTab(self._health_graph, "📈 Health")

#         self._history_log = HistoryLogView(parent=self)
#         self._tab_widget.addTab(self._history_log, "📜 History")

#         main_layout.addWidget(self._tab_widget)

#         # Status bar
#         self._setup_status_bar()

#     def _setup_header(self, layout: QVBoxLayout) -> None:
#         """Set up the header section."""
#         header = QFrame()
#         header_layout = QHBoxLayout(header)
#         header_layout.setContentsMargins(0, 0, 0, SPACING["md"])

#         title = QLabel(f"🔋 {APP_NAME}")
#         title.setStyleSheet(f"""
#             font-size: {FONTS['size_large']};
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['gray_900']};
#         """)
#         header_layout.addWidget(title)
#         header_layout.addStretch()

#         version = QLabel(f"v{APP_VERSION}")
#         version.setStyleSheet(f"color: {COLORS['gray_500']};")
#         header_layout.addWidget(version)

#         layout.addWidget(header)

#     def _setup_status_cards(self, layout: QVBoxLayout) -> None:
#         """Set up the status cards row."""
#         cards_layout = QHBoxLayout()
#         cards_layout.setSpacing(SPACING["md"])

#         self._battery_card = StatusCard(
#             title="Battery Level",
#             value="--%",
#             subtitle="Status: Unknown",
#             icon="🔋",
#             status="info",
#             parent=self,
#         )
#         self._battery_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._battery_card)

#         self._health_card = StatusCard(
#             title="Battery Health",
#             value="--%",
#             subtitle="Cycles: --",
#             icon="❤️",
#             status="info",
#             parent=self,
#         )
#         self._health_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
#         cards_layout.addWidget(self._health_card)

#         self._status_card = StatusCard(
#             title="Status",
#             value="--",
#             subtitle="Last updated: --",
#             icon="📊",
#             status="info",
#             parent=self,
#         )
#         cards_layout.addWidget(self._status_card)

#         # Actions card
#         self._actions_card = QFrame()
#         actions_layout = QVBoxLayout(self._actions_card)
#         actions_layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         actions_layout.setSpacing(SPACING["sm"])

#         actions_title = QLabel("⚡ Actions")
#         actions_title.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             font-weight: {FONTS['weight_medium']};
#             color: {COLORS['gray_600']};
#         """)
#         actions_layout.addWidget(actions_title)

#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["sm"])

#         self._stop_alarm_btn = QPushButton("🔕 Stop Alarm")
#         self._stop_alarm_btn.setObjectName("dangerButton")
#         self._stop_alarm_btn.setEnabled(False)
#         self._stop_alarm_btn.clicked.connect(self._stop_alarm)
#         btn_layout.addWidget(self._stop_alarm_btn)

#         self._snooze_btn = QPushButton("😴 Snooze")
#         self._snooze_btn.setObjectName("primaryButton")
#         self._snooze_btn.setEnabled(False)
#         self._snooze_btn.clicked.connect(self._snooze_alarm)
#         btn_layout.addWidget(self._snooze_btn)

#         self._refresh_btn = QPushButton("🔄 Refresh")
#         self._refresh_btn.clicked.connect(self._refresh)
#         btn_layout.addWidget(self._refresh_btn)

#         actions_layout.addLayout(btn_layout)

#         self._actions_card.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {COLORS['gray_100']};
#                 border-radius: {RADIUS['lg']}px;
#             }}
#         """)

#         cards_layout.addWidget(self._actions_card)
#         layout.addLayout(cards_layout)

#     def _setup_status_bar(self) -> None:
#         """Set up the status bar."""
#         self.statusBar().showMessage(f"Ready | {APP_ID}")
#         self.statusBar().setStyleSheet(f"""
#             QStatusBar {{
#                 color: {COLORS['gray_500']};
#                 font-size: {FONTS['size_small']};
#             }}
#         """)

#     def _setup_signals(self) -> None:
#         """Connect signals from services."""
#         if self._poller:
#             self._poller.reading_updated.connect(self._on_reading_updated)
#             self._poller.state_changed.connect(self._on_state_changed)
#             self._poller.error_occurred.connect(self._on_poller_error)

#         self._settings_panel.settings_saved.connect(self._on_settings_saved)
#         self._alert_banner.dismissed.connect(lambda: logger.debug("Alert dismissed"))
#         self._alert_banner.snoozed.connect(self._snooze_alarm)

#     @log_entry_exit()
#     def _on_reading_updated(self, reading: BatteryReading) -> None:
#         """Handle new battery reading."""
#         try:
#             percent = reading.percent
#             is_charging = reading.is_charging

#             self._battery_card.set_value(f"{percent}%")
#             self._battery_card.set_subtitle(
#                 "⚡ Charging" if is_charging else "🔋 Discharging"
#             )

#             if percent >= 60:
#                 status = "success"
#             elif percent >= 20:
#                 status = "warning"
#             else:
#                 status = "danger"
#             self._battery_card.set_status(status)

#             status_text = "Charging" if is_charging else "Discharging"
#             self._status_card.set_value(status_text)
#             self._status_card.set_subtitle(
#                 f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
#             )

#             self.statusBar().showMessage(f"Battery: {percent}% | {status_text}")

#             if (
#                 self._alarm_service
#                 and self._alarm_service.state_machine.is_alarm_active
#             ):
#                 self._show_alarm_banner()

#         except Exception as e:
#             logger.error("Error updating UI from reading in panel status_cards: %s", e)
#             self._battery_card.set_value("ERROR")

#     def _on_state_changed(self, old_state: str, new_state: str) -> None:
#         """Handle state change."""
#         try:
#             self._status_card.set_subtitle(f"State: {new_state}")
#         except Exception as e:
#             logger.error("Error updating state UI in panel status_cards: %s", e)

#     def _on_poller_error(self, error_msg: str) -> None:
#         """Handle poller error."""
#         try:
#             self._alert_banner.show_alert(
#                 message=f"⚠️ {error_msg}",
#                 alert_type="warning",
#                 show_snooze=False,
#             )
#             self.statusBar().showMessage(f"Error: {error_msg}")
#         except Exception as e:
#             logger.error("Error showing poller error in panel alert_banner: %s", e)

#     def _on_settings_saved(self) -> None:
#         """Handle settings saved - UPDATE ALARM SERVICE THRESHOLDS."""
#         try:
#             # Reload config to get latest values
#             self._config.load()
#             settings = self._config.settings

#             logger.info(
#                 "📊 Dashboard: Settings saved - high=%d%%, low=%d%%",
#                 settings.charge_threshold_high,
#                 settings.charge_threshold_low,
#             )

#             # ✅ Update AlarmService with new thresholds
#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(
#                     settings.charge_threshold_high,
#                     settings.charge_threshold_low,
#                 )
#                 logger.info("✅ AlarmService thresholds updated from Dashboard")

#             self.statusBar().showMessage("✅ Settings saved successfully", 3000)
#             self._refresh()
#         except Exception as e:
#             logger.error("Error after settings saved in panel settings: %s", e)

#     def _show_alarm_banner(self) -> None:
#         """Show alarm banner - PUSHES CONTENT DOWN."""
#         try:
#             if self._alarm_service:
#                 alarm_type = self._alarm_service.alarm_manager.active_alarm
#                 if alarm_type:
#                     messages = {
#                         "full_charge": (
#                             "🔔 Battery fully charged! Unplug to extend battery life."
#                         ),
#                         "low_battery": "⚠️ Battery low! Plug in to charge.",
#                         "critical_low": "🔴 Battery critical! Plug in immediately!",
#                     }
#                     message = messages.get(alarm_type.value, "🔔 Alarm active!")
#                     alert_type = (
#                         "danger" if alarm_type.value == "critical_low" else "warning"
#                     )

#                     # Show alert - THIS WILL PUSH CONTENT DOWN
#                     self._alert_banner.show_alert(
#                         message=message,
#                         alert_type=alert_type,
#                         show_snooze=True,
#                     )

#                     self._stop_alarm_btn.setEnabled(True)
#                     self._snooze_btn.setEnabled(True)
#         except Exception as e:
#             logger.error("Error showing alarm banner in panel alert_banner: %s", e)

#     def _stop_alarm(self) -> None:
#         """Stop the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.stop_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("🔕 Alarm stopped", 2000)
#         except Exception as e:
#             logger.error("Error stopping alarm in panel actions: %s", e)

#     def _snooze_alarm(self) -> None:
#         """Snooze the current alarm."""
#         try:
#             if self._alarm_service:
#                 self._alarm_service.snooze_alarm()
#                 self._alert_banner.dismiss()
#                 self._stop_alarm_btn.setEnabled(False)
#                 self._snooze_btn.setEnabled(False)
#                 self.statusBar().showMessage("😴 Alarm snoozed for 15 minutes", 2000)
#         except Exception as e:
#             logger.error("Error snoozing alarm in panel actions: %s", e)

#     def _refresh(self) -> None:
#         """Refresh all data."""
#         try:
#             self._health_graph.refresh()
#             self._history_log.refresh()
#             self.statusBar().showMessage("🔄 Refreshed", 1000)
#         except Exception as e:
#             logger.error("Error refreshing in dashboard panels: %s", e)

#     def _update_ui(self) -> None:
#         """Initial UI update."""
#         self._settings_panel.load_settings()
#         self._health_graph.refresh()
#         self._history_log.refresh()

#     def show_event(self) -> None:
#         """Show and activate the window."""
#         self.show()
#         self.raise_()
#         self.activateWindow()

#     def closeEvent(self, event: QCloseEvent) -> None:
#         """Handle close event - just hide the window."""
#         event.ignore()
#         self.hide()
#         logger.debug("Dashboard hidden (not closed)")

#     def close_dashboard(self) -> None:
#         """Fully close the dashboard."""
#         self.close()

#     def __repr__(self) -> str:
#         return f"<DashboardWindow visible={self.isVisible()}>"









































































"""
FILE: src/voltsentry/ui/dashboard.py
PATH: voltsentry/src/voltsentry/ui/dashboard.py
DESCRIPTION: Main dashboard window with all panels
PHASE: 4.2 - Dashboard Main Window

DISCIPLINES:
- 0.1 Logging: ERROR with panel name on failure
- 0.2 Error Handling: Each panel has its own try/except
- 0.4 Fallback: Panel shows placeholder on error
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from ..core.config import get_config
from ..core.constants import APP_ID, APP_NAME, APP_VERSION
from ..core.decorators import log_entry_exit
from ..core.logging_config import get_logger
from ..core.types import BatteryReading
from ..services.alarm_service import AlarmService
from ..services.battery_poller import BatteryPoller
from .health_graph import HealthGraph
from .history_log import HistoryLogView
from .settings_panel import SettingsPanel
from .styles import COLORS, FONTS, MAIN_STYLESHEET, RADIUS, SPACING
from .widgets.alert_banner import AlertBanner
from .widgets.status_card import StatusCard

logger = get_logger(__name__)


class DashboardWindow(QMainWindow):
    """
    Main dashboard window.

    Features:
    - Status cards (battery %, health score, cycles)
    - Alert banner
    - Settings panel
    - Health graph
    - History log
    - Each panel isolated with error handling
    - Reset State button for manual alarm reset
    """

    closed = pyqtSignal()

    def __init__(
        self,
        poller: Optional[BatteryPoller] = None,
        alarm_service: Optional[AlarmService] = None,
    ):
        super().__init__()

        self._poller = poller
        self._alarm_service = alarm_service
        self._config = get_config()

        self._setup_window()
        self._setup_ui()
        self._setup_signals()
        self._update_ui()

        logger.info("DashboardWindow initialized")

    def _setup_window(self) -> None:
        """Set up the main window properties."""
        self.setWindowTitle(f"{APP_NAME} - Dashboard")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self.setStyleSheet(MAIN_STYLESHEET)

        # ✅ Load icon for the window
        try:
            from ..utils import get_resource_path
            
            # Try PNG first (better quality)
            icon_path = get_resource_path("assets/icon.png")
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                logger.info("✅ Dashboard window icon loaded from: %s", icon_path)
            else:
                # Try ICO as fallback
                icon_path = get_resource_path("assets/icon.ico")
                if icon_path.exists():
                    self.setWindowIcon(QIcon(str(icon_path)))
                    logger.info("✅ Dashboard window icon loaded from: %s", icon_path)
        except Exception as e:
            logger.debug("Could not load window icon: %s", e)

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(
            SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
        )
        main_layout.setSpacing(SPACING["md"])

        # Header
        self._setup_header(main_layout)

        # Alert banner - EXPANDS LAYOUT (doesn't overlap)
        self._alert_banner = AlertBanner(auto_dismiss_seconds=0, parent=self)
        self._alert_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._alert_banner.setVisible(False)  # Hidden by default
        main_layout.addWidget(self._alert_banner)

        # Status cards
        self._setup_status_cards(main_layout)

        # Tab widget
        self._tab_widget = QTabWidget()

        self._settings_panel = SettingsPanel(self._config, parent=self)
        self._tab_widget.addTab(self._settings_panel, "⚙️ Settings")

        self._health_graph = HealthGraph(parent=self)
        self._tab_widget.addTab(self._health_graph, "📈 Health")

        self._history_log = HistoryLogView(parent=self)
        self._tab_widget.addTab(self._history_log, "📜 History")

        main_layout.addWidget(self._tab_widget)

        # Status bar
        self._setup_status_bar()

    def _setup_header(self, layout: QVBoxLayout) -> None:
        """Set up the header section."""
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, SPACING["md"])

        title = QLabel(f"🔋 {APP_NAME}")
        title.setStyleSheet(f"""
            font-size: {FONTS['size_large']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['gray_900']};
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet(f"color: {COLORS['gray_500']};")
        header_layout.addWidget(version)

        layout.addWidget(header)

    def _setup_status_cards(self, layout: QVBoxLayout) -> None:
        """Set up the status cards row with Reset State button."""
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(SPACING["md"])

        self._battery_card = StatusCard(
            title="Battery Level",
            value="--%",
            subtitle="Status: Unknown",
            icon="🔋",
            status="info",
            parent=self,
        )
        self._battery_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
        cards_layout.addWidget(self._battery_card)

        self._health_card = StatusCard(
            title="Battery Health",
            value="--%",
            subtitle="Cycles: --",
            icon="❤️",
            status="info",
            parent=self,
        )
        self._health_card.clicked.connect(lambda: self._tab_widget.setCurrentIndex(1))
        cards_layout.addWidget(self._health_card)

        self._status_card = StatusCard(
            title="Status",
            value="--",
            subtitle="Last updated: --",
            icon="📊",
            status="info",
            parent=self,
        )
        cards_layout.addWidget(self._status_card)

        # Actions card - ADDED RESET STATE BUTTON
        self._actions_card = QFrame()
        actions_layout = QVBoxLayout(self._actions_card)
        actions_layout.setContentsMargins(
            SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
        )
        actions_layout.setSpacing(SPACING["sm"])

        actions_title = QLabel("⚡ Actions")
        actions_title.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            font-weight: {FONTS['weight_medium']};
            color: {COLORS['gray_600']};
        """)
        actions_layout.addWidget(actions_title)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING["sm"])

        self._stop_alarm_btn = QPushButton("🔕 Stop Alarm")
        self._stop_alarm_btn.setObjectName("dangerButton")
        self._stop_alarm_btn.setEnabled(False)
        self._stop_alarm_btn.clicked.connect(self._stop_alarm)
        btn_layout.addWidget(self._stop_alarm_btn)

        self._snooze_btn = QPushButton("😴 Snooze")
        self._snooze_btn.setObjectName("primaryButton")
        self._snooze_btn.setEnabled(False)
        self._snooze_btn.clicked.connect(self._snooze_alarm)
        btn_layout.addWidget(self._snooze_btn)

        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        btn_layout.addWidget(self._refresh_btn)

        # ✅ NEW: Reset State Button
        self._reset_btn = QPushButton("🔄 Reset State")
        self._reset_btn.setObjectName("primaryButton")
        self._reset_btn.setToolTip("Clear active snooze and force immediate battery re-evaluation")
        self._reset_btn.clicked.connect(self._reset_state)
        btn_layout.addWidget(self._reset_btn)

        actions_layout.addLayout(btn_layout)

        self._actions_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['gray_100']};
                border-radius: {RADIUS['lg']}px;
            }}
        """)

        cards_layout.addWidget(self._actions_card)
        layout.addLayout(cards_layout)

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.statusBar().showMessage(f"Ready | {APP_ID}")
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                color: {COLORS['gray_500']};
                font-size: {FONTS['size_small']};
            }}
        """)

    def _setup_signals(self) -> None:
        """Connect signals from services."""
        if self._poller:
            self._poller.reading_updated.connect(self._on_reading_updated)
            self._poller.state_changed.connect(self._on_state_changed)
            self._poller.error_occurred.connect(self._on_poller_error)

        self._settings_panel.settings_saved.connect(self._on_settings_saved)
        self._alert_banner.dismissed.connect(lambda: logger.debug("Alert dismissed"))
        self._alert_banner.snoozed.connect(self._snooze_alarm)

    @log_entry_exit()
    def _on_reading_updated(self, reading: BatteryReading) -> None:
        """Handle new battery reading."""
        try:
            percent = reading.percent
            is_charging = reading.is_charging

            self._battery_card.set_value(f"{percent}%")
            self._battery_card.set_subtitle(
                "⚡ Charging" if is_charging else "🔋 Discharging"
            )

            if percent >= 60:
                status = "success"
            elif percent >= 20:
                status = "warning"
            else:
                status = "danger"
            self._battery_card.set_status(status)

            status_text = "Charging" if is_charging else "Discharging"
            self._status_card.set_value(status_text)
            self._status_card.set_subtitle(
                f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
            )

            self.statusBar().showMessage(f"Battery: {percent}% | {status_text}")

            if (
                self._alarm_service
                and self._alarm_service.state_machine.is_alarm_active
            ):
                self._show_alarm_banner()

        except Exception as e:
            logger.error("Error updating UI from reading in panel status_cards: %s", e)
            self._battery_card.set_value("ERROR")

    def _on_state_changed(self, old_state: str, new_state: str) -> None:
        """Handle state change."""
        try:
            self._status_card.set_subtitle(f"State: {new_state}")
        except Exception as e:
            logger.error("Error updating state UI in panel status_cards: %s", e)

    def _on_poller_error(self, error_msg: str) -> None:
        """Handle poller error."""
        try:
            self._alert_banner.show_alert(
                message=f"⚠️ {error_msg}",
                alert_type="warning",
                show_snooze=False,
            )
            self.statusBar().showMessage(f"Error: {error_msg}")
        except Exception as e:
            logger.error("Error showing poller error in panel alert_banner: %s", e)

    def _on_settings_saved(self) -> None:
        """Handle settings saved - UPDATE ALARM SERVICE THRESHOLDS."""
        try:
            # Reload config to get latest values
            self._config.load()
            settings = self._config.settings

            logger.info(
                "📊 Dashboard: Settings saved - high=%d%%, low=%d%%",
                settings.charge_threshold_high,
                settings.charge_threshold_low,
            )

            # ✅ Update AlarmService with new thresholds
            if self._alarm_service:
                self._alarm_service.update_thresholds(
                    settings.charge_threshold_high,
                    settings.charge_threshold_low,
                )
                logger.info("✅ AlarmService thresholds updated from Dashboard")

            self.statusBar().showMessage("✅ Settings saved successfully", 3000)
            self._refresh()
        except Exception as e:
            logger.error("Error after settings saved in panel settings: %s", e)

    def _show_alarm_banner(self) -> None:
        """Show alarm banner - PUSHES CONTENT DOWN."""
        try:
            if self._alarm_service:
                alarm_type = self._alarm_service.alarm_manager.active_alarm
                if alarm_type:
                    messages = {
                        "full_charge": (
                            "🔔 Battery fully charged! Unplug to extend battery life."
                        ),
                        "low_battery": "⚠️ Battery low! Plug in to charge.",
                        "critical_low": "🔴 Battery critical! Plug in immediately!",
                    }
                    message = messages.get(alarm_type.value, "🔔 Alarm active!")
                    alert_type = (
                        "danger" if alarm_type.value == "critical_low" else "warning"
                    )

                    # Show alert - THIS WILL PUSH CONTENT DOWN
                    self._alert_banner.show_alert(
                        message=message,
                        alert_type=alert_type,
                        show_snooze=True,
                    )

                    self._stop_alarm_btn.setEnabled(True)
                    self._snooze_btn.setEnabled(True)
        except Exception as e:
            logger.error("Error showing alarm banner in panel alert_banner: %s", e)

    def _stop_alarm(self) -> None:
        """Stop the current alarm."""
        try:
            if self._alarm_service:
                self._alarm_service.stop_alarm()
                self._alert_banner.dismiss()
                self._stop_alarm_btn.setEnabled(False)
                self._snooze_btn.setEnabled(False)
                self.statusBar().showMessage("🔕 Alarm stopped", 2000)
        except Exception as e:
            logger.error("Error stopping alarm in panel actions: %s", e)

    def _snooze_alarm(self) -> None:
        """Snooze the current alarm."""
        try:
            if self._alarm_service:
                self._alarm_service.snooze_alarm()
                self._alert_banner.dismiss()
                self._stop_alarm_btn.setEnabled(False)
                self._snooze_btn.setEnabled(False)
                self.statusBar().showMessage("😴 Alarm snoozed for 15 minutes", 2000)
        except Exception as e:
            logger.error("Error snoozing alarm in panel actions: %s", e)

    # ============================================================
    # ✅ UPDATED REFRESH METHOD - Also resets state
    # ============================================================

    def _refresh(self) -> None:
        """Refresh all data AND reset alarm state for fresh evaluation."""
        try:
            # ✅ Reset alarm state first
            if self._alarm_service:
                self._alarm_service.reset_alarm_state(reason="User clicked Refresh button")
            
            # Then refresh UI data
            self._health_graph.refresh()
            self._history_log.refresh()
            
            # Force immediate battery check
            if self._poller and self._poller.current_reading:
                reading = self._poller.current_reading
                if self._alarm_service:
                    self._alarm_service.process_reading(reading)
            
            self.statusBar().showMessage("🔄 Refreshed and state reset", 1000)
        except Exception as e:
            logger.error("Error refreshing in dashboard panels: %s", e)

    # ============================================================
    # ✅ NEW: RESET STATE METHOD
    # ============================================================

    def _reset_state(self) -> None:
        """Reset alarm state to force fresh evaluation without restart."""
        try:
            if self._alarm_service:
                # Reset alarm state
                self._alarm_service.reset_alarm_state(reason="User clicked Reset State button")
                
                # Clear alert banner
                self._alert_banner.dismiss()
                self._stop_alarm_btn.setEnabled(False)
                self._snooze_btn.setEnabled(False)
                
                # Force immediate battery check
                if self._poller and self._poller.current_reading:
                    reading = self._poller.current_reading
                    self._alarm_service.process_reading(reading)
                
                self.statusBar().showMessage("✅ State reset successfully - monitoring active", 3000)
                logger.info("User manually reset alarm state")
        except Exception as e:
            logger.error("Error resetting state: %s", e)
            self.statusBar().showMessage("❌ Failed to reset state", 2000)

    def _update_ui(self) -> None:
        """Initial UI update."""
        self._settings_panel.load_settings()
        self._health_graph.refresh()
        self._history_log.refresh()

    def show_event(self) -> None:
        """Show and activate the window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle close event - just hide the window."""
        event.ignore()
        self.hide()
        logger.debug("Dashboard hidden (not closed)")

    def close_dashboard(self) -> None:
        """Fully close the dashboard."""
        self.close()

    def __repr__(self) -> str:
        return f"<DashboardWindow visible={self.isVisible()}>"
    
    