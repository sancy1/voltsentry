# """
# FILE: src/voltsentry/ui/settings_panel.py
# PATH: voltsentry/src/voltsentry/ui/settings_panel.py
# DESCRIPTION: Settings panel with validation
# PHASE: 4.3 - Settings Panel

# DISCIPLINES:
# - 0.1 Logging: INFO on settings saved, ERROR on validation
# - 0.2 Error Handling: Validation before saving
# - 0.4 Fallback: Previous settings remain active on invalid input
# """

# from typing import Optional
# from pathlib import Path
# from PyQt6.QtCore import Qt, pyqtSignal, QTimer
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QSlider,
#     QPushButton,
#     QCheckBox,
#     QComboBox,
#     QLineEdit,
#     QGroupBox,
#     QMessageBox,
#     QFileDialog,
# )
# from PyQt6.QtGui import QFont

# from ..core.config import GlobalConfig, VoltSentrySettings
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from ..core.validators import validate_threshold_pair
# from ..core.constants import SNOOZE_DURATION_MINUTES
# from .styles import COLORS, FONTS, SPACING

# logger = get_logger(__name__)


# class SettingsPanel(QWidget):
#     """
#     Settings panel with validation.

#     Features:
#     - Threshold sliders with validation (high must be 10% above low)
#     - Quiet hours configuration
#     - Alarm volume slider
#     - Custom sound upload
#     - Startup options
#     - Invalid combinations rejected with inline message
#     """

#     settings_saved = pyqtSignal()

#     def __init__(self, config: GlobalConfig, parent: Optional[QWidget] = None):
#         super().__init__(parent)
#         self._config = config
#         self._settings = config.settings

#         self._setup_ui()
#         self.load_settings()

#         logger.info("SettingsPanel initialized")

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         layout = QVBoxLayout(self)
#         layout.setSpacing(SPACING["lg"])
#         layout.setContentsMargins(0, 0, 0, 0)

#         # Battery Thresholds
#         threshold_group = QGroupBox("🔋 Battery Thresholds")
#         threshold_layout = QVBoxLayout(threshold_group)

#         # High threshold
#         high_layout = QHBoxLayout()
#         high_layout.addWidget(QLabel("Stop Charging at:"))
#         self._high_slider = QSlider(Qt.Orientation.Horizontal)
#         self._high_slider.setRange(50, 100)
#         self._high_slider.setTickInterval(5)
#         self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._high_slider.valueChanged.connect(self._on_high_changed)
#         high_layout.addWidget(self._high_slider, 1)

#         self._high_label = QLabel("85%")
#         self._high_label.setFixedWidth(50)
#         self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._high_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['primary']};
#         """)
#         high_layout.addWidget(self._high_label)
#         threshold_layout.addLayout(high_layout)

#         # Low threshold
#         low_layout = QHBoxLayout()
#         low_layout.addWidget(QLabel("Start Charging at:"))
#         self._low_slider = QSlider(Qt.Orientation.Horizontal)
#         self._low_slider.setRange(5, 50)
#         self._low_slider.setTickInterval(5)
#         self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._low_slider.valueChanged.connect(self._on_low_changed)
#         low_layout.addWidget(self._low_slider, 1)

#         self._low_label = QLabel("20%")
#         self._low_label.setFixedWidth(50)
#         self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._low_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['warning']};
#         """)
#         low_layout.addWidget(self._low_label)
#         threshold_layout.addLayout(low_layout)

#         # Validation message
#         self._validation_msg = QLabel("")
#         self._validation_msg.setStyleSheet(f"color: {COLORS['danger']};")
#         self._validation_msg.setVisible(False)
#         threshold_layout.addWidget(self._validation_msg)

#         layout.addWidget(threshold_group)

#         # Quiet Hours
#         quiet_group = QGroupBox("🌙 Quiet Hours")
#         quiet_layout = QVBoxLayout(quiet_group)

#         # Enable checkbox
#         self._quiet_enabled = QCheckBox("Enable Quiet Hours")
#         self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
#         quiet_layout.addWidget(self._quiet_enabled)

#         # Time range
#         time_layout = QHBoxLayout()
#         time_layout.addWidget(QLabel("From:"))
#         self._quiet_start = QComboBox()
#         self._quiet_start.addItems(self._generate_time_options())
#         time_layout.addWidget(self._quiet_start)

#         time_layout.addWidget(QLabel("To:"))
#         self._quiet_end = QComboBox()
#         self._quiet_end.addItems(self._generate_time_options())
#         time_layout.addWidget(self._quiet_end)

#         time_layout.addStretch()
#         quiet_layout.addLayout(time_layout)

#         layout.addWidget(quiet_group)

#         # Audio Settings
#         audio_group = QGroupBox("🔊 Audio")
#         audio_layout = QVBoxLayout(audio_group)

#         # Volume
#         vol_layout = QHBoxLayout()
#         vol_layout.addWidget(QLabel("Volume:"))
#         self._volume_slider = QSlider(Qt.Orientation.Horizontal)
#         self._volume_slider.setRange(0, 100)
#         self._volume_slider.valueChanged.connect(self._on_volume_changed)
#         vol_layout.addWidget(self._volume_slider, 1)
#         self._volume_label = QLabel("80%")
#         self._volume_label.setFixedWidth(40)
#         vol_layout.addWidget(self._volume_label)
#         audio_layout.addLayout(vol_layout)

#         # Custom sound
#         sound_layout = QHBoxLayout()
#         sound_layout.addWidget(QLabel("Custom Alarm Sound:"))
#         self._sound_path = QLineEdit()
#         self._sound_path.setReadOnly(True)
#         self._sound_path.setPlaceholderText("No custom sound selected")
#         sound_layout.addWidget(self._sound_path, 1)

#         self._browse_btn = QPushButton("Browse...")
#         self._browse_btn.clicked.connect(self._browse_sound)
#         sound_layout.addWidget(self._browse_btn)

#         self._clear_sound_btn = QPushButton("Clear")
#         self._clear_sound_btn.clicked.connect(self._clear_sound)
#         sound_layout.addWidget(self._clear_sound_btn)

#         audio_layout.addLayout(sound_layout)

#         layout.addWidget(audio_group)

#         # Startup & Reports
#         misc_group = QGroupBox("⚙️ General")
#         misc_layout = QVBoxLayout(misc_group)

#         self._startup_check = QCheckBox("Start with OS")
#         misc_layout.addWidget(self._startup_check)

#         self._weekly_report_check = QCheckBox("Enable Weekly Reports")
#         misc_layout.addWidget(self._weekly_report_check)

#         layout.addWidget(misc_group)

#         # Save Button
#         btn_layout = QHBoxLayout()
#         btn_layout.addStretch()

#         self._save_btn = QPushButton("💾 Save Settings")
#         self._save_btn.setObjectName("primaryButton")
#         self._save_btn.setFixedHeight(36)
#         self._save_btn.clicked.connect(self.save_settings)
#         btn_layout.addWidget(self._save_btn)

#         self._reset_btn = QPushButton("↩️ Reset to Defaults")
#         self._reset_btn.clicked.connect(self.reset_settings)
#         btn_layout.addWidget(self._reset_btn)

#         layout.addLayout(btn_layout)

#         # Status message
#         self._status_label = QLabel("")
#         self._status_label.setStyleSheet(f"color: {COLORS['gray_500']};")
#         layout.addWidget(self._status_label)

#     def _generate_time_options(self) -> list:
#         """Generate time options for quiet hours."""
#         return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

#     def _on_high_changed(self, value: int) -> None:
#         """Handle high threshold slider change."""
#         self._high_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _on_low_changed(self, value: int) -> None:
#         """Handle low threshold slider change."""
#         self._low_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _validate_thresholds(self) -> bool:
#         """Validate threshold pair and show message if invalid."""
#         high = self._high_slider.value()
#         low = self._low_slider.value()

#         try:
#             validate_threshold_pair(high, low)
#             self._validation_msg.setVisible(False)
#             self._save_btn.setEnabled(True)
#             return True
#         except ValueError as e:
#             self._validation_msg.setText(f"⚠️ {e}")
#             self._validation_msg.setVisible(True)
#             self._save_btn.setEnabled(False)
#             return False

#     def _on_volume_changed(self, value: int) -> None:
#         """Handle volume slider change."""
#         self._volume_label.setText(f"{value}%")

#     def _on_quiet_toggled(self, checked: bool) -> None:
#         """Handle quiet hours toggle."""
#         self._quiet_start.setEnabled(checked)
#         self._quiet_end.setEnabled(checked)

#     def _browse_sound(self) -> None:
#         """Browse for custom sound file."""
#         file_path, _ = QFileDialog.getOpenFileName(
#             self,
#             "Select Alarm Sound",
#             str(Path.home()),
#             "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)",
#         )

#         if file_path:
#             self._sound_path.setText(file_path)
#             logger.info("Custom sound selected: %s", file_path)

#     def _clear_sound(self) -> None:
#         """Clear custom sound selection."""
#         self._sound_path.clear()
#         logger.info("Custom sound cleared")

#     @log_entry_exit()
#     def load_settings(self) -> None:
#         """Load settings from config."""
#         settings = self._settings

#         # Thresholds
#         self._high_slider.setValue(settings.charge_threshold_high)
#         self._low_slider.setValue(settings.charge_threshold_low)

#         # Volume
#         self._volume_slider.setValue(int(settings.alarm_volume * 100))

#         # Quiet hours
#         self._quiet_enabled.setChecked(
#             settings.quiet_hours_start != "00:00"
#             or settings.quiet_hours_end != "00:00"
#         )
#         self._quiet_start.setCurrentText(settings.quiet_hours_start)
#         self._quiet_end.setCurrentText(settings.quiet_hours_end)
#         self._quiet_start.setEnabled(self._quiet_enabled.isChecked())
#         self._quiet_end.setEnabled(self._quiet_enabled.isChecked())

#         # Custom sound
#         if settings.custom_alarm_path:
#             self._sound_path.setText(settings.custom_alarm_path)

#         # Startup
#         self._startup_check.setChecked(settings.start_with_os)

#         # Reports
#         self._weekly_report_check.setChecked(settings.weekly_report_enabled)

#         # Validate
#         self._validate_thresholds()

#         logger.info("Settings loaded")

#     def save_settings(self) -> None:
#         """Save settings with validation."""
#         # Validate first
#         if not self._validate_thresholds():
#             QMessageBox.warning(
#                 self,
#                 "Invalid Settings",
#                 "Please fix the validation errors before saving.",
#             )
#             return

#         try:
#             high = self._high_slider.value()
#             low = self._low_slider.value()
#             volume = self._volume_slider.value() / 100.0

#             # Determine quiet hours
#             if self._quiet_enabled.isChecked():
#                 quiet_start = self._quiet_start.currentText()
#                 quiet_end = self._quiet_end.currentText()
#             else:
#                 quiet_start = "00:00"
#                 quiet_end = "00:00"

#             # Update settings
#             self._settings.update(
#                 charge_threshold_high=high,
#                 charge_threshold_low=low,
#                 alarm_volume=volume,
#                 quiet_hours_start=quiet_start,
#                 quiet_hours_end=quiet_end,
#                 custom_alarm_path=self._sound_path.text() or None,
#                 start_with_os=self._startup_check.isChecked(),
#                 weekly_report_enabled=self._weekly_report_check.isChecked(),
#             )

#             # Save to disk
#             self._config.save()

#             self._status_label.setText("✅ Settings saved successfully!")
#             self._status_label.setStyleSheet(f"color: {COLORS['success']};")

#             # Clear status after 5 seconds
#             QTimer.singleShot(5000, lambda: self._status_label.setText(""))

#             self.settings_saved.emit()
#             logger.info("Settings saved successfully")

#         except Exception as e:
#             logger.error("Failed to save settings: %s", e)
#             QMessageBox.critical(
#                 self, "Error", f"Failed to save settings: {e}"
#             )

#     def reset_settings(self) -> None:
#         """Reset settings to defaults."""
#         reply = QMessageBox.question(
#             self,
#             "Reset Settings",
#             "Are you sure you want to reset all settings to defaults?",
#             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
#         )

#         if reply == QMessageBox.StandardButton.Yes:
#             self._config.reset()
#             self.load_settings()
#             self._status_label.setText("↩️ Settings reset to defaults")
#             self._status_label.setStyleSheet(f"color: {COLORS['warning']};")
#             logger.info("Settings reset to defaults")

































# """
# FILE: src/voltsentry/ui/settings_panel.py
# PATH: voltsentry/src/voltsentry/ui/settings_panel.py
# DESCRIPTION: Settings panel with validation - NO AUDIO SECTION
# PHASE: 4.3 - Settings Panel

# DISCIPLINES:
# - 0.1 Logging: INFO on settings saved, ERROR on validation
# - 0.2 Error Handling: Validation before saving
# - 0.4 Fallback: Previous settings remain active on invalid input
# """

# from pathlib import Path
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QTimer
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QSlider,
#     QPushButton,
#     QCheckBox,
#     QComboBox,
#     QMessageBox,
#     QGroupBox,
#     QSizePolicy,
# )

# from ..core.config import GlobalConfig
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from ..core.validators import validate_threshold_pair
# from .styles import COLORS, FONTS, SPACING, RADIUS

# logger = get_logger(__name__)


# class SettingsPanel(QWidget):
#     """
#     Settings panel with validation.

#     Features:
#     - Threshold sliders with validation (high must be 10% above low)
#     - Quiet hours configuration
#     - Startup options
#     - Invalid combinations rejected with inline message
#     """

#     settings_saved = pyqtSignal()

#     def __init__(self, config: GlobalConfig, parent: Optional[QWidget] = None):
#         super().__init__(parent)
#         self._config = config
#         self._settings = config.settings

#         self._setup_ui()
#         self.load_settings()

#         logger.info("SettingsPanel initialized")

#     def _setup_ui(self) -> None:
#         """Set up the UI layout - NO AUDIO SECTION."""
#         layout = QVBoxLayout(self)
#         layout.setSpacing(SPACING["lg"])
#         layout.setContentsMargins(0, 0, 0, 0)

#         # ============================================================
#         # Battery Thresholds - EXPANDED
#         # ============================================================
#         threshold_group = QGroupBox("🔋 Battery Thresholds")
#         threshold_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         threshold_layout = QVBoxLayout(threshold_group)
#         threshold_layout.setSpacing(SPACING["md"])

#         # High threshold
#         high_layout = QHBoxLayout()
#         high_label = QLabel("Stop Charging at:")
#         high_label.setMinimumWidth(130)
#         high_layout.addWidget(high_label)

#         self._high_slider = QSlider(Qt.Orientation.Horizontal)
#         self._high_slider.setRange(50, 100)
#         self._high_slider.setTickInterval(5)
#         self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._high_slider.valueChanged.connect(self._on_high_changed)
#         high_layout.addWidget(self._high_slider, 1)

#         self._high_label = QLabel("85%")
#         self._high_label.setFixedWidth(50)
#         self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._high_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['primary']};
#             font-size: {FONTS['size_medium']};
#         """)
#         high_layout.addWidget(self._high_label)
#         threshold_layout.addLayout(high_layout)

#         # Low threshold
#         low_layout = QHBoxLayout()
#         low_label = QLabel("Start Charging at:")
#         low_label.setMinimumWidth(130)
#         low_layout.addWidget(low_label)

#         self._low_slider = QSlider(Qt.Orientation.Horizontal)
#         self._low_slider.setRange(5, 50)
#         self._low_slider.setTickInterval(5)
#         self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._low_slider.valueChanged.connect(self._on_low_changed)
#         low_layout.addWidget(self._low_slider, 1)

#         self._low_label = QLabel("20%")
#         self._low_label.setFixedWidth(50)
#         self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._low_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['warning']};
#             font-size: {FONTS['size_medium']};
#         """)
#         low_layout.addWidget(self._low_label)
#         threshold_layout.addLayout(low_layout)

#         # Validation message
#         self._validation_msg = QLabel("")
#         self._validation_msg.setWordWrap(True)
#         self._validation_msg.setStyleSheet(f"color: {COLORS['danger']}; padding: {SPACING['sm']}px;")
#         self._validation_msg.setVisible(False)
#         threshold_layout.addWidget(self._validation_msg)

#         # Threshold info
#         info_label = QLabel("💡 Keep at least 10% gap between thresholds for optimal battery health.")
#         info_label.setWordWrap(True)
#         info_label.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         threshold_layout.addWidget(info_label)

#         layout.addWidget(threshold_group)

#         # ============================================================
#         # Quiet Hours - EXPANDED
#         # ============================================================
#         quiet_group = QGroupBox("🌙 Quiet Hours")
#         quiet_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         quiet_layout = QVBoxLayout(quiet_group)
#         quiet_layout.setSpacing(SPACING["md"])

#         # Enable checkbox
#         self._quiet_enabled = QCheckBox("Enable Quiet Hours")
#         self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
#         self._quiet_enabled.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         quiet_layout.addWidget(self._quiet_enabled)

#         # Time range
#         time_layout = QHBoxLayout()
#         time_layout.setSpacing(SPACING["md"])

#         time_layout.addWidget(QLabel("From:"))
#         self._quiet_start = QComboBox()
#         self._quiet_start.addItems(self._generate_time_options())
#         self._quiet_start.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_start)

#         time_layout.addWidget(QLabel("To:"))
#         self._quiet_end = QComboBox()
#         self._quiet_end.addItems(self._generate_time_options())
#         self._quiet_end.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_end)

#         time_layout.addStretch()
#         quiet_layout.addLayout(time_layout)

#         quiet_info = QLabel("💡 Alarms will be silent during quiet hours. Visual alerts still appear.")
#         quiet_info.setWordWrap(True)
#         quiet_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         quiet_layout.addWidget(quiet_info)

#         layout.addWidget(quiet_group)

#         # ============================================================
#         # General Settings - EXPANDED
#         # ============================================================
#         misc_group = QGroupBox("⚙️ General Settings")
#         misc_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         misc_layout = QVBoxLayout(misc_group)
#         misc_layout.setSpacing(SPACING["md"])

#         self._startup_check = QCheckBox("Start with Windows")
#         self._startup_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._startup_check)

#         self._weekly_report_check = QCheckBox("Enable Weekly Reports")
#         self._weekly_report_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._weekly_report_check)

#         misc_info = QLabel("💡 Weekly reports summarize your battery health and usage patterns.")
#         misc_info.setWordWrap(True)
#         misc_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         misc_layout.addWidget(misc_info)

#         layout.addWidget(misc_group)

#         # ============================================================
#         # Save & Reset Buttons
#         # ============================================================
#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["md"])
#         btn_layout.addStretch()

#         self._save_btn = QPushButton("💾 Save Settings")
#         self._save_btn.setObjectName("primaryButton")
#         self._save_btn.setFixedHeight(40)
#         self._save_btn.setMinimumWidth(140)
#         self._save_btn.clicked.connect(self.save_settings)
#         btn_layout.addWidget(self._save_btn)

#         self._reset_btn = QPushButton("↩️ Reset to Defaults")
#         self._reset_btn.setFixedHeight(40)
#         self._reset_btn.clicked.connect(self.reset_settings)
#         btn_layout.addWidget(self._reset_btn)

#         layout.addLayout(btn_layout)

#         # Status message
#         self._status_label = QLabel("")
#         self._status_label.setWordWrap(True)
#         self._status_label.setStyleSheet(f"""
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             font-size: {FONTS['size_normal']};
#         """)
#         layout.addWidget(self._status_label)

#         # Add stretch to push everything up
#         layout.addStretch()

#     def _generate_time_options(self) -> list:
#         """Generate time options for quiet hours."""
#         return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

#     def _on_high_changed(self, value: int) -> None:
#         """Handle high threshold slider change."""
#         self._high_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _on_low_changed(self, value: int) -> None:
#         """Handle low threshold slider change."""
#         self._low_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _validate_thresholds(self) -> bool:
#         """Validate threshold pair and show message if invalid."""
#         high = self._high_slider.value()
#         low = self._low_slider.value()

#         try:
#             validate_threshold_pair(high, low)
#             self._validation_msg.setVisible(False)
#             self._save_btn.setEnabled(True)
#             return True
#         except ValueError as e:
#             self._validation_msg.setText(f"⚠️ {e}")
#             self._validation_msg.setVisible(True)
#             self._save_btn.setEnabled(False)
#             return False

#     def _on_quiet_toggled(self, checked: bool) -> None:
#         """Handle quiet hours toggle."""
#         self._quiet_start.setEnabled(checked)
#         self._quiet_end.setEnabled(checked)

#     @log_entry_exit()
#     def load_settings(self) -> None:
#         """Load settings from config."""
#         settings = self._settings

#         # Thresholds
#         self._high_slider.setValue(settings.charge_threshold_high)
#         self._low_slider.setValue(settings.charge_threshold_low)

#         # Quiet hours
#         self._quiet_enabled.setChecked(
#             settings.quiet_hours_start != "00:00" or settings.quiet_hours_end != "00:00"
#         )
#         self._quiet_start.setCurrentText(settings.quiet_hours_start)
#         self._quiet_end.setCurrentText(settings.quiet_hours_end)
#         self._quiet_start.setEnabled(self._quiet_enabled.isChecked())
#         self._quiet_end.setEnabled(self._quiet_enabled.isChecked())

#         # Startup
#         self._startup_check.setChecked(settings.start_with_os)

#         # Reports
#         self._weekly_report_check.setChecked(settings.weekly_report_enabled)

#         # Validate
#         self._validate_thresholds()

#         logger.info("Settings loaded")

#     def save_settings(self) -> None:
#         """Save settings with validation."""
#         # Validate first
#         if not self._validate_thresholds():
#             QMessageBox.warning(
#                 self,
#                 "Invalid Settings",
#                 "Please fix the validation errors before saving."
#             )
#             return

#         try:
#             high = self._high_slider.value()
#             low = self._low_slider.value()

#             # Determine quiet hours
#             if self._quiet_enabled.isChecked():
#                 quiet_start = self._quiet_start.currentText()
#                 quiet_end = self._quiet_end.currentText()
#             else:
#                 quiet_start = "00:00"
#                 quiet_end = "00:00"

#             # Update settings (without audio)
#             self._settings.update(
#                 charge_threshold_high=high,
#                 charge_threshold_low=low,
#                 quiet_hours_start=quiet_start,
#                 quiet_hours_end=quiet_end,
#                 start_with_os=self._startup_check.isChecked(),
#                 weekly_report_enabled=self._weekly_report_check.isChecked(),
#             )

#             # Save to disk
#             self._config.save()

#             self._status_label.setText("✅ Settings saved successfully!")
#             self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['sm']}px;")

#             # Clear status after 5 seconds
#             QTimer.singleShot(5000, lambda: self._status_label.setText(""))

#             self.settings_saved.emit()
#             logger.info("Settings saved successfully")

#         except Exception as e:
#             logger.error("Failed to save settings: %s", e)
#             QMessageBox.critical(
#                 self,
#                 "Error",
#                 f"Failed to save settings: {e}"
#             )

#     def reset_settings(self) -> None:
#         """Reset settings to defaults."""
#         reply = QMessageBox.question(
#             self,
#             "Reset Settings",
#             "Are you sure you want to reset all settings to defaults?",
#             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#         )

#         if reply == QMessageBox.StandardButton.Yes:
#             self._config.reset()
#             self.load_settings()
#             self._status_label.setText("↩️ Settings reset to defaults")
#             self._status_label.setStyleSheet(f"color: {COLORS['warning']}; padding: {SPACING['sm']}px;")
#             logger.info("Settings reset to defaults")
















































# """
# FILE: src/voltsentry/ui/settings_panel.py
# PATH: voltsentry/src/voltsentry/ui/settings_panel.py
# DESCRIPTION: Settings panel with validation - NO AUDIO SECTION
# PHASE: 4.3 - Settings Panel

# DISCIPLINES:
# - 0.1 Logging: INFO on settings saved, ERROR on validation
# - 0.2 Error Handling: Validation before saving
# - 0.4 Fallback: Previous settings remain active on invalid input
# """

# from pathlib import Path
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QTimer
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QSlider,
#     QPushButton,
#     QCheckBox,
#     QComboBox,
#     QMessageBox,
#     QGroupBox,
#     QSizePolicy,
# )

# from ..core.config import GlobalConfig
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from ..core.validators import validate_threshold_pair
# from .styles import COLORS, FONTS, SPACING, RADIUS

# logger = get_logger(__name__)


# class SettingsPanel(QWidget):
#     """
#     Settings panel with validation.

#     Features:
#     - Threshold sliders with validation (high must be 10% above low)
#     - Quiet hours configuration
#     - Startup options
#     - Invalid combinations rejected with inline message
#     """

#     settings_saved = pyqtSignal()

#     def __init__(self, config: GlobalConfig, parent: Optional[QWidget] = None):
#         super().__init__(parent)
#         self._config = config
#         self._settings = config.settings

#         self._setup_ui()
#         self.load_settings()

#         logger.info("SettingsPanel initialized")

#     def _setup_ui(self) -> None:
#         """Set up the UI layout - NO AUDIO SECTION."""
#         layout = QVBoxLayout(self)
#         layout.setSpacing(SPACING["lg"])
#         layout.setContentsMargins(0, 0, 0, 0)

#         # ============================================================
#         # Battery Thresholds - EXPANDED
#         # ============================================================
#         threshold_group = QGroupBox("🔋 Battery Thresholds")
#         threshold_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         threshold_layout = QVBoxLayout(threshold_group)
#         threshold_layout.setSpacing(SPACING["md"])

#         # High threshold
#         high_layout = QHBoxLayout()
#         high_label = QLabel("Stop Charging at:")
#         high_label.setMinimumWidth(130)
#         high_layout.addWidget(high_label)

#         self._high_slider = QSlider(Qt.Orientation.Horizontal)
#         self._high_slider.setRange(50, 100)
#         self._high_slider.setTickInterval(5)
#         self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._high_slider.valueChanged.connect(self._on_high_changed)
#         high_layout.addWidget(self._high_slider, 1)

#         self._high_label = QLabel(f"{self._settings.charge_threshold_high}%")
#         self._high_label.setFixedWidth(50)
#         self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._high_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['primary']};
#             font-size: {FONTS['size_medium']};
#         """)
#         high_layout.addWidget(self._high_label)
#         threshold_layout.addLayout(high_layout)

#         # Low threshold
#         low_layout = QHBoxLayout()
#         low_label = QLabel("Start Charging at:")
#         low_label.setMinimumWidth(130)
#         low_layout.addWidget(low_label)

#         self._low_slider = QSlider(Qt.Orientation.Horizontal)
#         self._low_slider.setRange(5, 50)
#         self._low_slider.setTickInterval(5)
#         self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._low_slider.valueChanged.connect(self._on_low_changed)
#         low_layout.addWidget(self._low_slider, 1)

#         self._low_label = QLabel(f"{self._settings.charge_threshold_low}%")
#         self._low_label.setFixedWidth(50)
#         self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._low_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['warning']};
#             font-size: {FONTS['size_medium']};
#         """)
#         low_layout.addWidget(self._low_label)
#         threshold_layout.addLayout(low_layout)

#         # Validation message
#         self._validation_msg = QLabel("")
#         self._validation_msg.setWordWrap(True)
#         self._validation_msg.setStyleSheet(f"color: {COLORS['danger']}; padding: {SPACING['sm']}px;")
#         self._validation_msg.setVisible(False)
#         threshold_layout.addWidget(self._validation_msg)

#         # Threshold info
#         info_label = QLabel("💡 Keep at least 10% gap between thresholds for optimal battery health.")
#         info_label.setWordWrap(True)
#         info_label.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         threshold_layout.addWidget(info_label)

#         layout.addWidget(threshold_group)

#         # ============================================================
#         # Quiet Hours - EXPANDED
#         # ============================================================
#         quiet_group = QGroupBox("🌙 Quiet Hours")
#         quiet_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         quiet_layout = QVBoxLayout(quiet_group)
#         quiet_layout.setSpacing(SPACING["md"])

#         # Enable checkbox
#         self._quiet_enabled = QCheckBox("Enable Quiet Hours")
#         self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
#         self._quiet_enabled.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         quiet_layout.addWidget(self._quiet_enabled)

#         # Time range
#         time_layout = QHBoxLayout()
#         time_layout.setSpacing(SPACING["md"])

#         time_layout.addWidget(QLabel("From:"))
#         self._quiet_start = QComboBox()
#         self._quiet_start.addItems(self._generate_time_options())
#         self._quiet_start.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_start)

#         time_layout.addWidget(QLabel("To:"))
#         self._quiet_end = QComboBox()
#         self._quiet_end.addItems(self._generate_time_options())
#         self._quiet_end.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_end)

#         time_layout.addStretch()
#         quiet_layout.addLayout(time_layout)

#         quiet_info = QLabel("💡 Alarms will be silent during quiet hours. Visual alerts still appear.")
#         quiet_info.setWordWrap(True)
#         quiet_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         quiet_layout.addWidget(quiet_info)

#         layout.addWidget(quiet_group)

#         # ============================================================
#         # General Settings - EXPANDED
#         # ============================================================
#         misc_group = QGroupBox("⚙️ General Settings")
#         misc_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         misc_layout = QVBoxLayout(misc_group)
#         misc_layout.setSpacing(SPACING["md"])

#         self._startup_check = QCheckBox("Start with Windows")
#         self._startup_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._startup_check)

#         self._weekly_report_check = QCheckBox("Enable Weekly Reports")
#         self._weekly_report_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._weekly_report_check)

#         misc_info = QLabel("💡 Weekly reports summarize your battery health and usage patterns.")
#         misc_info.setWordWrap(True)
#         misc_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         misc_layout.addWidget(misc_info)

#         layout.addWidget(misc_group)

#         # ============================================================
#         # Save & Reset Buttons
#         # ============================================================
#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["md"])
#         btn_layout.addStretch()

#         self._save_btn = QPushButton("💾 Save Settings")
#         self._save_btn.setObjectName("primaryButton")
#         self._save_btn.setFixedHeight(40)
#         self._save_btn.setMinimumWidth(140)
#         self._save_btn.clicked.connect(self.save_settings)
#         btn_layout.addWidget(self._save_btn)

#         self._reset_btn = QPushButton("↩️ Reset to Defaults")
#         self._reset_btn.setFixedHeight(40)
#         self._reset_btn.clicked.connect(self.reset_settings)
#         btn_layout.addWidget(self._reset_btn)

#         layout.addLayout(btn_layout)

#         # Status message
#         self._status_label = QLabel("")
#         self._status_label.setWordWrap(True)
#         self._status_label.setStyleSheet(f"""
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             font-size: {FONTS['size_normal']};
#         """)
#         layout.addWidget(self._status_label)

#         # Add stretch to push everything up
#         layout.addStretch()

#     def _generate_time_options(self) -> list:
#         """Generate time options for quiet hours."""
#         return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

#     def _on_high_changed(self, value: int) -> None:
#         """Handle high threshold slider change."""
#         self._high_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _on_low_changed(self, value: int) -> None:
#         """Handle low threshold slider change."""
#         self._low_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _validate_thresholds(self) -> bool:
#         """Validate threshold pair and show message if invalid."""
#         high = self._high_slider.value()
#         low = self._low_slider.value()

#         try:
#             validate_threshold_pair(high, low)
#             self._validation_msg.setVisible(False)
#             self._save_btn.setEnabled(True)
#             return True
#         except ValueError as e:
#             self._validation_msg.setText(f"⚠️ {e}")
#             self._validation_msg.setVisible(True)
#             self._save_btn.setEnabled(False)
#             return False

#     def _on_quiet_toggled(self, checked: bool) -> None:
#         """Handle quiet hours toggle."""
#         self._quiet_start.setEnabled(checked)
#         self._quiet_end.setEnabled(checked)

#     @log_entry_exit()
#     def load_settings(self) -> None:
#         """Load settings from config."""
#         settings = self._settings

#         # Thresholds
#         self._high_slider.setValue(settings.charge_threshold_high)
#         self._high_label.setText(f"{settings.charge_threshold_high}%")
#         self._low_slider.setValue(settings.charge_threshold_low)
#         self._low_label.setText(f"{settings.charge_threshold_low}%")

#         # Quiet hours
#         self._quiet_enabled.setChecked(
#             settings.quiet_hours_start != "00:00" or settings.quiet_hours_end != "00:00"
#         )
#         self._quiet_start.setCurrentText(settings.quiet_hours_start)
#         self._quiet_end.setCurrentText(settings.quiet_hours_end)
#         self._quiet_start.setEnabled(self._quiet_enabled.isChecked())
#         self._quiet_end.setEnabled(self._quiet_enabled.isChecked())

#         # Startup
#         self._startup_check.setChecked(settings.start_with_os)

#         # Reports
#         self._weekly_report_check.setChecked(settings.weekly_report_enabled)

#         # Validate
#         self._validate_thresholds()

#         logger.info("Settings loaded")

#     def save_settings(self) -> None:
#         """Save settings with validation."""
#         # Validate first
#         if not self._validate_thresholds():
#             QMessageBox.warning(
#                 self,
#                 "Invalid Settings",
#                 "Please fix the validation errors before saving."
#             )
#             return

#         try:
#             high = self._high_slider.value()
#             low = self._low_slider.value()

#             # Determine quiet hours
#             if self._quiet_enabled.isChecked():
#                 quiet_start = self._quiet_start.currentText()
#                 quiet_end = self._quiet_end.currentText()
#             else:
#                 quiet_start = "00:00"
#                 quiet_end = "00:00"

#             # Update settings (without audio)
#             self._settings.update(
#                 charge_threshold_high=high,
#                 charge_threshold_low=low,
#                 quiet_hours_start=quiet_start,
#                 quiet_hours_end=quiet_end,
#                 start_with_os=self._startup_check.isChecked(),
#                 weekly_report_enabled=self._weekly_report_check.isChecked(),
#             )

#             # Save to disk
#             self._config.save()

#             self._status_label.setText("✅ Settings saved successfully!")
#             self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['sm']}px;")

#             # Clear status after 5 seconds
#             QTimer.singleShot(5000, lambda: self._status_label.setText(""))

#             self.settings_saved.emit()
#             logger.info("Settings saved successfully")

#         except Exception as e:
#             logger.error("Failed to save settings: %s", e)
#             QMessageBox.critical(
#                 self,
#                 "Error",
#                 f"Failed to save settings: {e}"
#             )

#     def reset_settings(self) -> None:
#         """Reset settings to defaults."""
#         reply = QMessageBox.question(
#             self,
#             "Reset Settings",
#             "Are you sure you want to reset all settings to defaults?",
#             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#         )

#         if reply == QMessageBox.StandardButton.Yes:
#             self._config.reset()
#             self.load_settings()
#             self._status_label.setText("↩️ Settings reset to defaults")
#             self._status_label.setStyleSheet(f"color: {COLORS['warning']}; padding: {SPACING['sm']}px;")
#             logger.info("Settings reset to defaults")

























































# """
# FILE: src/voltsentry/ui/settings_panel.py
# PATH: voltsentry/src/voltsentry/ui/settings_panel.py
# DESCRIPTION: Settings panel with validation - Integrated with AlarmService
# PHASE: 4.3 - Settings Panel

# DISCIPLINES:
# - 0.1 Logging: INFO on settings saved, ERROR on validation
# - 0.2 Error Handling: Validation before saving
# - 0.4 Fallback: Previous settings remain active on invalid input
# """

# from pathlib import Path
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QTimer
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QSlider,
#     QPushButton,
#     QCheckBox,
#     QComboBox,
#     QMessageBox,
#     QGroupBox,
#     QSizePolicy,
# )

# from ..core.config import GlobalConfig
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from ..core.validators import validate_threshold_pair
# from ..core.constants import (
#     DEFAULT_CHARGE_THRESHOLD_HIGH,
#     DEFAULT_CHARGE_THRESHOLD_LOW,
#     DEFAULT_QUIET_HOURS_START,
#     DEFAULT_QUIET_HOURS_END,
# )
# from ..services.alarm_service import AlarmService
# from .styles import COLORS, FONTS, SPACING, RADIUS

# logger = get_logger(__name__)


# class SettingsPanel(QWidget):
#     """
#     Settings panel with validation - Integrated with AlarmService.

#     Features:
#     - Threshold sliders with validation (high must be 10% above low)
#     - READ FROM AlarmService state machine (NOT hardcoded)
#     - WRITE TO AlarmService.update_thresholds()
#     - Quiet hours configuration
#     - Startup options
#     - Invalid combinations rejected with inline message
#     """

#     settings_saved = pyqtSignal()

#     def __init__(
#         self,
#         config: GlobalConfig,
#         alarm_service: Optional[AlarmService] = None,
#         parent: Optional[QWidget] = None,
#     ):
#         super().__init__(parent)
#         self._config = config
#         self._settings = config.settings
#         self._alarm_service = alarm_service

#         self._setup_ui()
#         self.load_settings()

#         logger.info("SettingsPanel initialized with AlarmService integration")

#     def _setup_ui(self) -> None:
#         """Set up the UI layout - NO AUDIO SECTION."""
#         layout = QVBoxLayout(self)
#         layout.setSpacing(SPACING["lg"])
#         layout.setContentsMargins(0, 0, 0, 0)

#         # ============================================================
#         # Battery Thresholds - EXPANDED
#         # ============================================================
#         threshold_group = QGroupBox("🔋 Battery Thresholds")
#         threshold_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         threshold_layout = QVBoxLayout(threshold_group)
#         threshold_layout.setSpacing(SPACING["md"])

#         # High threshold
#         high_layout = QHBoxLayout()
#         high_label = QLabel("Stop Charging at:")
#         high_label.setMinimumWidth(130)
#         high_layout.addWidget(high_label)

#         self._high_slider = QSlider(Qt.Orientation.Horizontal)
#         self._high_slider.setRange(50, 100)
#         self._high_slider.setTickInterval(5)
#         self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._high_slider.valueChanged.connect(self._on_high_changed)
#         high_layout.addWidget(self._high_slider, 1)

#         # ✅ DYNAMIC LABEL - reads from AlarmService state machine
#         current_high = self._get_current_high_threshold()
#         self._high_label = QLabel(f"{current_high}%")
#         self._high_label.setFixedWidth(50)
#         self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._high_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['primary']};
#             font-size: {FONTS['size_medium']};
#         """)
#         high_layout.addWidget(self._high_label)
#         threshold_layout.addLayout(high_layout)

#         # Low threshold
#         low_layout = QHBoxLayout()
#         low_label = QLabel("Start Charging at:")
#         low_label.setMinimumWidth(130)
#         low_layout.addWidget(low_label)

#         self._low_slider = QSlider(Qt.Orientation.Horizontal)
#         self._low_slider.setRange(5, 50)
#         self._low_slider.setTickInterval(5)
#         self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._low_slider.valueChanged.connect(self._on_low_changed)
#         low_layout.addWidget(self._low_slider, 1)

#         # ✅ DYNAMIC LABEL - reads from AlarmService state machine
#         current_low = self._get_current_low_threshold()
#         self._low_label = QLabel(f"{current_low}%")
#         self._low_label.setFixedWidth(50)
#         self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._low_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['warning']};
#             font-size: {FONTS['size_medium']};
#         """)
#         low_layout.addWidget(self._low_label)
#         threshold_layout.addLayout(low_layout)

#         # Validation message
#         self._validation_msg = QLabel("")
#         self._validation_msg.setWordWrap(True)
#         self._validation_msg.setStyleSheet(f"color: {COLORS['danger']}; padding: {SPACING['sm']}px;")
#         self._validation_msg.setVisible(False)
#         threshold_layout.addWidget(self._validation_msg)

#         # Threshold info
#         info_label = QLabel("💡 Keep at least 10% gap between thresholds for optimal battery health.")
#         info_label.setWordWrap(True)
#         info_label.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         threshold_layout.addWidget(info_label)

#         layout.addWidget(threshold_group)

#         # ============================================================
#         # Quiet Hours - EXPANDED
#         # ============================================================
#         quiet_group = QGroupBox("🌙 Quiet Hours")
#         quiet_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         quiet_layout = QVBoxLayout(quiet_group)
#         quiet_layout.setSpacing(SPACING["md"])

#         # Enable checkbox
#         self._quiet_enabled = QCheckBox("Enable Quiet Hours")
#         self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
#         self._quiet_enabled.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         quiet_layout.addWidget(self._quiet_enabled)

#         # Time range
#         time_layout = QHBoxLayout()
#         time_layout.setSpacing(SPACING["md"])

#         time_layout.addWidget(QLabel("From:"))
#         self._quiet_start = QComboBox()
#         self._quiet_start.addItems(self._generate_time_options())
#         self._quiet_start.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_start)

#         time_layout.addWidget(QLabel("To:"))
#         self._quiet_end = QComboBox()
#         self._quiet_end.addItems(self._generate_time_options())
#         self._quiet_end.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_end)

#         time_layout.addStretch()
#         quiet_layout.addLayout(time_layout)

#         quiet_info = QLabel("💡 Alarms will be silent during quiet hours. Visual alerts still appear.")
#         quiet_info.setWordWrap(True)
#         quiet_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         quiet_layout.addWidget(quiet_info)

#         layout.addWidget(quiet_group)

#         # ============================================================
#         # General Settings - EXPANDED
#         # ============================================================
#         misc_group = QGroupBox("⚙️ General Settings")
#         misc_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         misc_layout = QVBoxLayout(misc_group)
#         misc_layout.setSpacing(SPACING["md"])

#         self._startup_check = QCheckBox("Start with Windows")
#         self._startup_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._startup_check)

#         self._weekly_report_check = QCheckBox("Enable Weekly Reports")
#         self._weekly_report_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._weekly_report_check)

#         misc_info = QLabel("💡 Weekly reports summarize your battery health and usage patterns.")
#         misc_info.setWordWrap(True)
#         misc_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         misc_layout.addWidget(misc_info)

#         layout.addWidget(misc_group)

#         # ============================================================
#         # Save & Reset Buttons
#         # ============================================================
#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["md"])
#         btn_layout.addStretch()

#         self._save_btn = QPushButton("💾 Save Settings")
#         self._save_btn.setObjectName("primaryButton")
#         self._save_btn.setFixedHeight(40)
#         self._save_btn.setMinimumWidth(140)
#         self._save_btn.clicked.connect(self.save_settings)
#         btn_layout.addWidget(self._save_btn)

#         self._reset_btn = QPushButton("↩️ Reset to Defaults")
#         self._reset_btn.setFixedHeight(40)
#         self._reset_btn.clicked.connect(self.reset_settings)
#         btn_layout.addWidget(self._reset_btn)

#         layout.addLayout(btn_layout)

#         # Status message
#         self._status_label = QLabel("")
#         self._status_label.setWordWrap(True)
#         self._status_label.setStyleSheet(f"""
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             font-size: {FONTS['size_normal']};
#         """)
#         layout.addWidget(self._status_label)

#         # Add stretch to push everything up
#         layout.addStretch()

#     def _get_current_high_threshold(self) -> int:
#         """Get current high threshold from AlarmService state machine."""
#         if self._alarm_service:
#             return self._alarm_service.state_machine.config.high_threshold
#         return self._settings.charge_threshold_high

#     def _get_current_low_threshold(self) -> int:
#         """Get current low threshold from AlarmService state machine."""
#         if self._alarm_service:
#             return self._alarm_service.state_machine.config.low_threshold
#         return self._settings.charge_threshold_low

#     def _generate_time_options(self) -> list:
#         """Generate time options for quiet hours."""
#         return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

#     def _on_high_changed(self, value: int) -> None:
#         """Handle high threshold slider change."""
#         self._high_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _on_low_changed(self, value: int) -> None:
#         """Handle low threshold slider change."""
#         self._low_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _validate_thresholds(self) -> bool:
#         """Validate threshold pair and show message if invalid."""
#         high = self._high_slider.value()
#         low = self._low_slider.value()

#         try:
#             validate_threshold_pair(high, low)
#             self._validation_msg.setVisible(False)
#             self._save_btn.setEnabled(True)
#             return True
#         except ValueError as e:
#             self._validation_msg.setText(f"⚠️ {e}")
#             self._validation_msg.setVisible(True)
#             self._save_btn.setEnabled(False)
#             return False

#     def _on_quiet_toggled(self, checked: bool) -> None:
#         """Handle quiet hours toggle."""
#         self._quiet_start.setEnabled(checked)
#         self._quiet_end.setEnabled(checked)

#     @log_entry_exit()
#     def load_settings(self) -> None:
#         """Load settings from AlarmService state machine - NO HARDCODED VALUES."""
#         settings = self._settings

#         # ✅ Thresholds - read from AlarmService state machine
#         high = self._get_current_high_threshold()
#         low = self._get_current_low_threshold()

#         self._high_slider.setValue(high)
#         self._low_slider.setValue(low)
#         self._high_label.setText(f"{high}%")
#         self._low_label.setText(f"{low}%")

#         # ✅ Quiet hours - read from settings
#         quiet_enabled = (
#             settings.quiet_hours_start != "00:00" or settings.quiet_hours_end != "00:00"
#         )
#         self._quiet_enabled.setChecked(quiet_enabled)
#         self._quiet_start.setCurrentText(settings.quiet_hours_start)
#         self._quiet_end.setCurrentText(settings.quiet_hours_end)
#         self._quiet_start.setEnabled(quiet_enabled)
#         self._quiet_end.setEnabled(quiet_enabled)

#         # ✅ Startup - read from settings
#         self._startup_check.setChecked(settings.start_with_os)

#         # ✅ Reports - read from settings
#         self._weekly_report_check.setChecked(settings.weekly_report_enabled)

#         # Validate
#         self._validate_thresholds()

#         logger.info(
#             "Settings loaded from AlarmService: high=%d%%, low=%d%%, quiet=%s",
#             high,
#             low,
#             quiet_enabled,
#         )

#     def save_settings(self) -> None:
#         """
#         Save settings with validation.
#         WRITES DIRECTLY TO ALARMSERVICE AND CONFIG.
#         """
#         # Validate first
#         if not self._validate_thresholds():
#             QMessageBox.warning(
#                 self,
#                 "Invalid Settings",
#                 "Please fix the validation errors before saving."
#             )
#             return

#         try:
#             high = self._high_slider.value()
#             low = self._low_slider.value()

#             # Determine quiet hours
#             if self._quiet_enabled.isChecked():
#                 quiet_start = self._quiet_start.currentText()
#                 quiet_end = self._quiet_end.currentText()
#             else:
#                 quiet_start = "00:00"
#                 quiet_end = "00:00"

#             # ============================================================
#             # ✅ WRITE TO ALARMSERVICE - This updates the state machine LIVE
#             # ============================================================
#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(high=high, low=low)
#                 logger.info("✅ AlarmService thresholds updated: high=%d%%, low=%d%%", high, low)

#             # Update settings config
#             self._settings.update(
#                 charge_threshold_high=high,
#                 charge_threshold_low=low,
#                 quiet_hours_start=quiet_start,
#                 quiet_hours_end=quiet_end,
#                 start_with_os=self._startup_check.isChecked(),
#                 weekly_report_enabled=self._weekly_report_check.isChecked(),
#             )

#             # Save to disk
#             self._config.save()

#             self._status_label.setText("✅ Settings saved successfully!")
#             self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['sm']}px;")

#             # Clear status after 5 seconds
#             QTimer.singleShot(5000, lambda: self._status_label.setText(""))

#             self.settings_saved.emit()
#             logger.info(
#                 "✅ Settings saved: high=%d%%, low=%d%%",
#                 high,
#                 low,
#             )

#         except Exception as e:
#             logger.error("Failed to save settings: %s", e)
#             QMessageBox.critical(
#                 self,
#                 "Error",
#                 f"Failed to save settings: {e}"
#             )

#     def reset_settings(self) -> None:
#         """Reset settings to defaults."""
#         reply = QMessageBox.question(
#             self,
#             "Reset Settings",
#             "Are you sure you want to reset all settings to defaults?",
#             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#         )

#         if reply == QMessageBox.StandardButton.Yes:
#             # Reset config
#             self._config.reset()

#             # Reset AlarmService thresholds
#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(
#                     high=DEFAULT_CHARGE_THRESHOLD_HIGH,
#                     low=DEFAULT_CHARGE_THRESHOLD_LOW,
#                 )
#                 logger.info("AlarmService reset to defaults")

#             self.load_settings()
#             self._status_label.setText("↩️ Settings reset to defaults")
#             self._status_label.setStyleSheet(f"color: {COLORS['warning']}; padding: {SPACING['sm']}px;")
#             logger.info("Settings reset to defaults")















































# """
# FILE: src/voltsentry/ui/settings_panel.py
# PATH: voltsentry/src/voltsentry/ui/settings_panel.py
# DESCRIPTION: Settings panel with validation - Integrated with AlarmService
# PHASE: 4.3 - Settings Panel

# DISCIPLINES:
# - 0.1 Logging: INFO on settings saved, ERROR on validation
# - 0.2 Error Handling: Validation before saving
# - 0.4 Fallback: Previous settings remain active on invalid input
# """

# from pathlib import Path
# from typing import Optional

# from PyQt6.QtCore import Qt, pyqtSignal, QTimer
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QSlider,
#     QPushButton,
#     QCheckBox,
#     QComboBox,
#     QMessageBox,
#     QGroupBox,
#     QSizePolicy,
# )

# from ..core.config import GlobalConfig
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit
# from ..core.validators import validate_threshold_pair
# from ..core.constants import (
#     DEFAULT_CHARGE_THRESHOLD_HIGH,
#     DEFAULT_CHARGE_THRESHOLD_LOW,
#     DEFAULT_QUIET_HOURS_START,
#     DEFAULT_QUIET_HOURS_END,
# )
# from ..services.alarm_service import AlarmService
# from ..utils.startup_utils import set_auto_start, is_auto_start_enabled
# from .styles import COLORS, FONTS, SPACING, RADIUS

# logger = get_logger(__name__)


# class SettingsPanel(QWidget):
#     """
#     Settings panel with validation - Integrated with AlarmService.

#     Features:
#     - Threshold sliders with validation (high must be 10% above low)
#     - READ FROM AlarmService state machine (NOT hardcoded)
#     - WRITE TO AlarmService.update_thresholds()
#     - Quiet hours configuration
#     - Startup options with registry integration
#     - Invalid combinations rejected with inline message
#     """

#     settings_saved = pyqtSignal()

#     def __init__(
#         self,
#         config: GlobalConfig,
#         alarm_service: Optional[AlarmService] = None,
#         parent: Optional[QWidget] = None,
#     ):
#         super().__init__(parent)
#         self._config = config
#         self._settings = config.settings
#         self._alarm_service = alarm_service

#         self._setup_ui()
#         self.load_settings()

#         logger.info("SettingsPanel initialized with AlarmService integration")

#     def _setup_ui(self) -> None:
#         """Set up the UI layout - NO AUDIO SECTION."""
#         layout = QVBoxLayout(self)
#         layout.setSpacing(SPACING["lg"])
#         layout.setContentsMargins(0, 0, 0, 0)

#         # ============================================================
#         # Battery Thresholds - EXPANDED
#         # ============================================================
#         threshold_group = QGroupBox("🔋 Battery Thresholds")
#         threshold_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         threshold_layout = QVBoxLayout(threshold_group)
#         threshold_layout.setSpacing(SPACING["md"])

#         # High threshold
#         high_layout = QHBoxLayout()
#         high_label = QLabel("Stop Charging at:")
#         high_label.setMinimumWidth(130)
#         high_layout.addWidget(high_label)

#         self._high_slider = QSlider(Qt.Orientation.Horizontal)
#         self._high_slider.setRange(50, 100)
#         self._high_slider.setTickInterval(5)
#         self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._high_slider.valueChanged.connect(self._on_high_changed)
#         high_layout.addWidget(self._high_slider, 1)

#         current_high = self._get_current_high_threshold()
#         self._high_label = QLabel(f"{current_high}%")
#         self._high_label.setFixedWidth(50)
#         self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._high_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['primary']};
#             font-size: {FONTS['size_medium']};
#         """)
#         high_layout.addWidget(self._high_label)
#         threshold_layout.addLayout(high_layout)

#         # Low threshold
#         low_layout = QHBoxLayout()
#         low_label = QLabel("Start Charging at:")
#         low_label.setMinimumWidth(130)
#         low_layout.addWidget(low_label)

#         self._low_slider = QSlider(Qt.Orientation.Horizontal)
#         self._low_slider.setRange(5, 50)
#         self._low_slider.setTickInterval(5)
#         self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
#         self._low_slider.valueChanged.connect(self._on_low_changed)
#         low_layout.addWidget(self._low_slider, 1)

#         current_low = self._get_current_low_threshold()
#         self._low_label = QLabel(f"{current_low}%")
#         self._low_label.setFixedWidth(50)
#         self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._low_label.setStyleSheet(f"""
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['warning']};
#             font-size: {FONTS['size_medium']};
#         """)
#         low_layout.addWidget(self._low_label)
#         threshold_layout.addLayout(low_layout)

#         # Validation message
#         self._validation_msg = QLabel("")
#         self._validation_msg.setWordWrap(True)
#         self._validation_msg.setStyleSheet(f"color: {COLORS['danger']}; padding: {SPACING['sm']}px;")
#         self._validation_msg.setVisible(False)
#         threshold_layout.addWidget(self._validation_msg)

#         # Threshold info
#         info_label = QLabel("💡 Keep at least 10% gap between thresholds for optimal battery health.")
#         info_label.setWordWrap(True)
#         info_label.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         threshold_layout.addWidget(info_label)

#         layout.addWidget(threshold_group)

#         # ============================================================
#         # Quiet Hours - EXPANDED
#         # ============================================================
#         quiet_group = QGroupBox("🌙 Quiet Hours")
#         quiet_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         quiet_layout = QVBoxLayout(quiet_group)
#         quiet_layout.setSpacing(SPACING["md"])

#         self._quiet_enabled = QCheckBox("Enable Quiet Hours")
#         self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
#         self._quiet_enabled.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         quiet_layout.addWidget(self._quiet_enabled)

#         time_layout = QHBoxLayout()
#         time_layout.setSpacing(SPACING["md"])

#         time_layout.addWidget(QLabel("From:"))
#         self._quiet_start = QComboBox()
#         self._quiet_start.addItems(self._generate_time_options())
#         self._quiet_start.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_start)

#         time_layout.addWidget(QLabel("To:"))
#         self._quiet_end = QComboBox()
#         self._quiet_end.addItems(self._generate_time_options())
#         self._quiet_end.setMinimumWidth(80)
#         time_layout.addWidget(self._quiet_end)

#         time_layout.addStretch()
#         quiet_layout.addLayout(time_layout)

#         quiet_info = QLabel("💡 Alarms will be silent during quiet hours. Visual alerts still appear.")
#         quiet_info.setWordWrap(True)
#         quiet_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         quiet_layout.addWidget(quiet_info)

#         layout.addWidget(quiet_group)

#         # ============================================================
#         # General Settings - EXPANDED with Startup Toggle
#         # ============================================================
#         misc_group = QGroupBox("⚙️ General Settings")
#         misc_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
#         misc_layout = QVBoxLayout(misc_group)
#         misc_layout.setSpacing(SPACING["md"])

#         # ✅ Startup checkbox - with actual registry control
#         self._startup_check = QCheckBox("Start VoltSentry with Windows")
#         self._startup_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         self._startup_check.toggled.connect(self._on_startup_toggled)
#         misc_layout.addWidget(self._startup_check)

#         startup_info = QLabel("💡 When enabled, VoltSentry will automatically launch when you log in to Windows.")
#         startup_info.setWordWrap(True)
#         startup_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         misc_layout.addWidget(startup_info)

#         self._weekly_report_check = QCheckBox("Enable Weekly Reports")
#         self._weekly_report_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
#         misc_layout.addWidget(self._weekly_report_check)

#         misc_info = QLabel("💡 Weekly reports summarize your battery health and usage patterns.")
#         misc_info.setWordWrap(True)
#         misc_info.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             background-color: {COLORS['gray_100']};
#             border-radius: {RADIUS['md']}px;
#         """)
#         misc_layout.addWidget(misc_info)

#         layout.addWidget(misc_group)

#         # ============================================================
#         # Save & Reset Buttons
#         # ============================================================
#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(SPACING["md"])
#         btn_layout.addStretch()

#         self._save_btn = QPushButton("💾 Save Settings")
#         self._save_btn.setObjectName("primaryButton")
#         self._save_btn.setFixedHeight(40)
#         self._save_btn.setMinimumWidth(140)
#         self._save_btn.clicked.connect(self.save_settings)
#         btn_layout.addWidget(self._save_btn)

#         self._reset_btn = QPushButton("↩️ Reset to Defaults")
#         self._reset_btn.setFixedHeight(40)
#         self._reset_btn.clicked.connect(self.reset_settings)
#         btn_layout.addWidget(self._reset_btn)

#         layout.addLayout(btn_layout)

#         # Status message
#         self._status_label = QLabel("")
#         self._status_label.setWordWrap(True)
#         self._status_label.setStyleSheet(f"""
#             color: {COLORS['gray_500']};
#             padding: {SPACING['sm']}px;
#             font-size: {FONTS['size_normal']};
#         """)
#         layout.addWidget(self._status_label)

#         layout.addStretch()

#     def _get_current_high_threshold(self) -> int:
#         """Get current high threshold from AlarmService state machine."""
#         if self._alarm_service:
#             return self._alarm_service.state_machine.config.high_threshold
#         return self._settings.charge_threshold_high

#     def _get_current_low_threshold(self) -> int:
#         """Get current low threshold from AlarmService state machine."""
#         if self._alarm_service:
#             return self._alarm_service.state_machine.config.low_threshold
#         return self._settings.charge_threshold_low

#     def _generate_time_options(self) -> list:
#         """Generate time options for quiet hours."""
#         return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

#     def _on_high_changed(self, value: int) -> None:
#         """Handle high threshold slider change."""
#         self._high_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _on_low_changed(self, value: int) -> None:
#         """Handle low threshold slider change."""
#         self._low_label.setText(f"{value}%")
#         self._validate_thresholds()

#     def _validate_thresholds(self) -> bool:
#         """Validate threshold pair and show message if invalid."""
#         high = self._high_slider.value()
#         low = self._low_slider.value()

#         try:
#             validate_threshold_pair(high, low)
#             self._validation_msg.setVisible(False)
#             self._save_btn.setEnabled(True)
#             return True
#         except ValueError as e:
#             self._validation_msg.setText(f"⚠️ {e}")
#             self._validation_msg.setVisible(True)
#             self._save_btn.setEnabled(False)
#             return False

#     def _on_quiet_toggled(self, checked: bool) -> None:
#         """Handle quiet hours toggle."""
#         self._quiet_start.setEnabled(checked)
#         self._quiet_end.setEnabled(checked)

#     # ============================================================
#     # ✅ STARTUP TOGGLE HANDLER - Connects to Windows Registry
#     # ============================================================
#     def _on_startup_toggled(self, checked: bool) -> None:
#         """Handle startup toggle - updates Windows Registry."""
#         try:
#             success = set_auto_start(checked)
#             if success:
#                 logger.info(f"✅ Auto-start { 'enabled' if checked else 'disabled' }")
#                 self._settings.start_with_os = checked
#                 self._config.save()
#                 self._status_label.setText(
#                     f"✅ Auto-start { 'enabled' if checked else 'disabled' }"
#                 )
#                 self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['sm']}px;")
#                 QTimer.singleShot(3000, lambda: self._status_label.setText(""))
#             else:
#                 self._startup_check.setChecked(not checked)
#                 QMessageBox.warning(
#                     self,
#                     "Startup Setting Failed",
#                     "Could not modify Windows startup setting.\n\n"
#                     "Please run the app as Administrator to enable this feature."
#                 )
#         except Exception as e:
#             logger.error(f"Failed to toggle startup: {e}")
#             self._startup_check.setChecked(not checked)

#     @log_entry_exit()
#     def load_settings(self) -> None:
#         """Load settings from AlarmService state machine."""
#         settings = self._settings

#         high = self._get_current_high_threshold()
#         low = self._get_current_low_threshold()

#         self._high_slider.setValue(high)
#         self._low_slider.setValue(low)
#         self._high_label.setText(f"{high}%")
#         self._low_label.setText(f"{low}%")

#         quiet_enabled = (
#             settings.quiet_hours_start != "00:00" or settings.quiet_hours_end != "00:00"
#         )
#         self._quiet_enabled.setChecked(quiet_enabled)
#         self._quiet_start.setCurrentText(settings.quiet_hours_start)
#         self._quiet_end.setCurrentText(settings.quiet_hours_end)
#         self._quiet_start.setEnabled(quiet_enabled)
#         self._quiet_end.setEnabled(quiet_enabled)

#         # ✅ Startup checkbox - sync with registry
#         registry_startup = is_auto_start_enabled()
#         self._startup_check.setChecked(registry_startup)
#         if registry_startup != settings.start_with_os:
#             settings.start_with_os = registry_startup
#             self._config.save()

#         self._weekly_report_check.setChecked(settings.weekly_report_enabled)

#         self._validate_thresholds()

#         logger.info(
#             "Settings loaded: high=%d%%, low=%d%%, quiet=%s, startup=%s",
#             high,
#             low,
#             quiet_enabled,
#             registry_startup,
#         )

#     def save_settings(self) -> None:
#         """Save settings with validation."""
#         if not self._validate_thresholds():
#             QMessageBox.warning(
#                 self,
#                 "Invalid Settings",
#                 "Please fix the validation errors before saving."
#             )
#             return

#         try:
#             high = self._high_slider.value()
#             low = self._low_slider.value()

#             if self._quiet_enabled.isChecked():
#                 quiet_start = self._quiet_start.currentText()
#                 quiet_end = self._quiet_end.currentText()
#             else:
#                 quiet_start = "00:00"
#                 quiet_end = "00:00"

#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(high=high, low=low)
#                 logger.info("✅ AlarmService thresholds updated: high=%d%%, low=%d%%", high, low)

#             self._settings.update(
#                 charge_threshold_high=high,
#                 charge_threshold_low=low,
#                 quiet_hours_start=quiet_start,
#                 quiet_hours_end=quiet_end,
#                 start_with_os=self._startup_check.isChecked(),
#                 weekly_report_enabled=self._weekly_report_check.isChecked(),
#             )

#             self._config.save()

#             self._status_label.setText("✅ Settings saved successfully!")
#             self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['sm']}px;")

#             QTimer.singleShot(5000, lambda: self._status_label.setText(""))

#             self.settings_saved.emit()
#             logger.info("✅ Settings saved")

#         except Exception as e:
#             logger.error("Failed to save settings: %s", e)
#             QMessageBox.critical(
#                 self,
#                 "Error",
#                 f"Failed to save settings: {e}"
#             )

#     def reset_settings(self) -> None:
#         """Reset settings to defaults."""
#         reply = QMessageBox.question(
#             self,
#             "Reset Settings",
#             "Are you sure you want to reset all settings to defaults?",
#             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#         )

#         if reply == QMessageBox.StandardButton.Yes:
#             self._config.reset()

#             if self._alarm_service:
#                 self._alarm_service.update_thresholds(
#                     high=DEFAULT_CHARGE_THRESHOLD_HIGH,
#                     low=DEFAULT_CHARGE_THRESHOLD_LOW,
#                 )
#                 logger.info("AlarmService reset to defaults")

#             # Also reset registry startup
#             set_auto_start(False)

#             self.load_settings()
#             self._status_label.setText("↩️ Settings reset to defaults")
#             self._status_label.setStyleSheet(f"color: {COLORS['warning']}; padding: {SPACING['sm']}px;")
#             logger.info("Settings reset to defaults")
            
            
            
            




































































"""
FILE: src/voltsentry/ui/settings_panel.py
PATH: voltsentry/src/voltsentry/ui/settings_panel.py
DESCRIPTION: Settings panel with validation - Integrated with AlarmService
PHASE: 4.3 - Settings Panel

DISCIPLINES:
- 0.1 Logging: INFO on settings saved, ERROR on validation
- 0.2 Error Handling: Validation before saving
- 0.4 Fallback: Previous settings remain active on invalid input
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QCheckBox,
    QComboBox,
    QMessageBox,
    QGroupBox,
    QSizePolicy,
    QScrollArea,
)

from ..core.config import GlobalConfig
from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit
from ..core.validators import validate_threshold_pair
from ..core.constants import (
    DEFAULT_CHARGE_THRESHOLD_HIGH,
    DEFAULT_CHARGE_THRESHOLD_LOW,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
)
from ..services.alarm_service import AlarmService
from ..utils.startup_utils import set_auto_start, is_auto_start_enabled
from .styles import COLORS, FONTS, SPACING, RADIUS

logger = get_logger(__name__)


class SettingsPanel(QWidget):
    """
    Settings panel with validation - Integrated with AlarmService.

    Features:
    - Threshold sliders with validation (high must be 10% above low)
    - READ FROM AlarmService state machine (NOT hardcoded)
    - WRITE TO AlarmService.update_thresholds()
    - Quiet hours configuration
    - Startup options with registry integration
    - Invalid combinations rejected with inline message
    - COMPACT layout fits small screens (11-13 inches)
    """

    settings_saved = pyqtSignal()

    def __init__(
        self,
        config: GlobalConfig,
        alarm_service: Optional[AlarmService] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config = config
        self._settings = config.settings
        self._alarm_service = alarm_service

        self._setup_ui()
        self.load_settings()

        logger.info("SettingsPanel initialized with AlarmService integration (compact)")

    def _setup_ui(self) -> None:
        """Set up the UI layout - COMPACT for small screens."""
        # Main layout with scroll support
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for very small screens (11-13 inches)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(SPACING["sm"])
        layout.setContentsMargins(SPACING["sm"], SPACING["sm"], SPACING["sm"], SPACING["sm"])

        # ============================================================
        # Battery Thresholds - COMPACT
        # ============================================================
        threshold_group = QGroupBox("🔋 Battery Thresholds")
        threshold_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        threshold_layout = QVBoxLayout(threshold_group)
        threshold_layout.setSpacing(SPACING["sm"])

        # High threshold
        high_layout = QHBoxLayout()
        high_layout.setSpacing(SPACING["sm"])
        high_label = QLabel("Stop at:")
        high_label.setMinimumWidth(60)
        high_layout.addWidget(high_label)

        self._high_slider = QSlider(Qt.Orientation.Horizontal)
        self._high_slider.setRange(50, 100)
        self._high_slider.setTickInterval(5)
        self._high_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._high_slider.valueChanged.connect(self._on_high_changed)
        high_layout.addWidget(self._high_slider, 1)

        current_high = self._get_current_high_threshold()
        self._high_label = QLabel(f"{current_high}%")
        self._high_label.setFixedWidth(40)
        self._high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._high_label.setStyleSheet(f"""
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['primary']};
            font-size: {FONTS['size_normal']};
        """)
        high_layout.addWidget(self._high_label)
        threshold_layout.addLayout(high_layout)

        # Low threshold
        low_layout = QHBoxLayout()
        low_layout.setSpacing(SPACING["sm"])
        low_label = QLabel("Start at:")
        low_label.setMinimumWidth(60)
        low_layout.addWidget(low_label)

        self._low_slider = QSlider(Qt.Orientation.Horizontal)
        self._low_slider.setRange(5, 50)
        self._low_slider.setTickInterval(5)
        self._low_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._low_slider.valueChanged.connect(self._on_low_changed)
        low_layout.addWidget(self._low_slider, 1)

        current_low = self._get_current_low_threshold()
        self._low_label = QLabel(f"{current_low}%")
        self._low_label.setFixedWidth(40)
        self._low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._low_label.setStyleSheet(f"""
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['warning']};
            font-size: {FONTS['size_normal']};
        """)
        low_layout.addWidget(self._low_label)
        threshold_layout.addLayout(low_layout)

        # Validation message
        self._validation_msg = QLabel("")
        self._validation_msg.setWordWrap(True)
        self._validation_msg.setStyleSheet(f"color: {COLORS['danger']}; padding: {SPACING['xs']}px; font-size: {FONTS['size_small']};")
        self._validation_msg.setVisible(False)
        threshold_layout.addWidget(self._validation_msg)

        # Compact threshold info
        info_label = QLabel("💡 Keep 10% gap between thresholds")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_500']};
            padding: {SPACING['xs']}px;
        """)
        threshold_layout.addWidget(info_label)

        layout.addWidget(threshold_group)

        # ============================================================
        # Quiet Hours - COMPACT
        # ============================================================
        quiet_group = QGroupBox("🌙 Quiet Hours")
        quiet_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        quiet_layout = QVBoxLayout(quiet_group)
        quiet_layout.setSpacing(SPACING["sm"])

        self._quiet_enabled = QCheckBox("Enable Quiet Hours")
        self._quiet_enabled.toggled.connect(self._on_quiet_toggled)
        self._quiet_enabled.setStyleSheet(f"font-size: {FONTS['size_normal']};")
        quiet_layout.addWidget(self._quiet_enabled)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(SPACING["sm"])

        time_layout.addWidget(QLabel("From:"))
        self._quiet_start = QComboBox()
        self._quiet_start.addItems(self._generate_time_options())
        self._quiet_start.setMinimumWidth(70)
        time_layout.addWidget(self._quiet_start)

        time_layout.addWidget(QLabel("To:"))
        self._quiet_end = QComboBox()
        self._quiet_end.addItems(self._generate_time_options())
        self._quiet_end.setMinimumWidth(70)
        time_layout.addWidget(self._quiet_end)

        time_layout.addStretch()
        quiet_layout.addLayout(time_layout)

        quiet_info = QLabel("💡 Alarms silent during quiet hours")
        quiet_info.setWordWrap(True)
        quiet_info.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_500']};
            padding: {SPACING['xs']}px;
        """)
        quiet_layout.addWidget(quiet_info)

        layout.addWidget(quiet_group)

        # ============================================================
        # Startup Toggle - Compact row (replaces bulky General Settings)
        # ============================================================
        startup_layout = QHBoxLayout()
        startup_layout.setSpacing(SPACING["sm"])
        
        self._startup_check = QCheckBox("🔁 Start with Windows")
        self._startup_check.setStyleSheet(f"font-size: {FONTS['size_normal']};")
        self._startup_check.toggled.connect(self._on_startup_toggled)
        startup_layout.addWidget(self._startup_check)
        startup_layout.addStretch()
        
        layout.addLayout(startup_layout)

        # ============================================================
        # Save & Reset Buttons (Compact)
        # ============================================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING["sm"])

        self._save_btn = QPushButton("💾 Save")
        self._save_btn.setObjectName("primaryButton")
        self._save_btn.setFixedHeight(32)
        self._save_btn.setMinimumWidth(80)
        self._save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self._save_btn)

        self._reset_btn = QPushButton("↩️ Reset")
        self._reset_btn.setFixedHeight(32)
        self._reset_btn.clicked.connect(self.reset_settings)
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Status message (compact)
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"""
            color: {COLORS['gray_500']};
            padding: {SPACING['xs']}px;
            font-size: {FONTS['size_small']};
        """)
        layout.addWidget(self._status_label)

        # Add stretch to push everything up
        layout.addStretch()

        # Set scroll content
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _get_current_high_threshold(self) -> int:
        """Get current high threshold from AlarmService state machine."""
        if self._alarm_service:
            return self._alarm_service.state_machine.config.high_threshold
        return self._settings.charge_threshold_high

    def _get_current_low_threshold(self) -> int:
        """Get current low threshold from AlarmService state machine."""
        if self._alarm_service:
            return self._alarm_service.state_machine.config.low_threshold
        return self._settings.charge_threshold_low

    def _generate_time_options(self) -> list:
        """Generate time options for quiet hours."""
        return [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

    def _on_high_changed(self, value: int) -> None:
        """Handle high threshold slider change."""
        self._high_label.setText(f"{value}%")
        self._validate_thresholds()

    def _on_low_changed(self, value: int) -> None:
        """Handle low threshold slider change."""
        self._low_label.setText(f"{value}%")
        self._validate_thresholds()

    def _validate_thresholds(self) -> bool:
        """Validate threshold pair and show message if invalid."""
        high = self._high_slider.value()
        low = self._low_slider.value()

        try:
            validate_threshold_pair(high, low)
            self._validation_msg.setVisible(False)
            self._save_btn.setEnabled(True)
            return True
        except ValueError as e:
            self._validation_msg.setText(f"⚠️ {e}")
            self._validation_msg.setVisible(True)
            self._save_btn.setEnabled(False)
            return False

    def _on_quiet_toggled(self, checked: bool) -> None:
        """Handle quiet hours toggle."""
        self._quiet_start.setEnabled(checked)
        self._quiet_end.setEnabled(checked)

    # ============================================================
    # ✅ STARTUP TOGGLE HANDLER - Connects to Windows Registry
    # ============================================================
    def _on_startup_toggled(self, checked: bool) -> None:
        """Handle startup toggle - updates Windows Registry."""
        try:
            success = set_auto_start(checked)
            if success:
                logger.info(f"✅ Auto-start {'enabled' if checked else 'disabled'}")
                self._settings.start_with_os = checked
                self._config.save()
                self._status_label.setText(
                    f"✅ Auto-start {'enabled' if checked else 'disabled'}"
                )
                self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['xs']}px;")
                QTimer.singleShot(3000, lambda: self._status_label.setText(""))
            else:
                self._startup_check.setChecked(not checked)
                QMessageBox.warning(
                    self,
                    "Startup Setting Failed",
                    "Could not modify Windows startup setting.\n\n"
                    "Please run the app as Administrator to enable this feature."
                )
        except Exception as e:
            logger.error(f"Failed to toggle startup: {e}")
            self._startup_check.setChecked(not checked)

    @log_entry_exit()
    def load_settings(self) -> None:
        """Load settings from AlarmService state machine."""
        settings = self._settings

        high = self._get_current_high_threshold()
        low = self._get_current_low_threshold()

        self._high_slider.setValue(high)
        self._low_slider.setValue(low)
        self._high_label.setText(f"{high}%")
        self._low_label.setText(f"{low}%")

        quiet_enabled = (
            settings.quiet_hours_start != "00:00" or settings.quiet_hours_end != "00:00"
        )
        self._quiet_enabled.setChecked(quiet_enabled)
        self._quiet_start.setCurrentText(settings.quiet_hours_start)
        self._quiet_end.setCurrentText(settings.quiet_hours_end)
        self._quiet_start.setEnabled(quiet_enabled)
        self._quiet_end.setEnabled(quiet_enabled)

        # ✅ Startup checkbox - sync with registry
        registry_startup = is_auto_start_enabled()
        self._startup_check.setChecked(registry_startup)
        if registry_startup != settings.start_with_os:
            settings.start_with_os = registry_startup
            self._config.save()

        self._validate_thresholds()

        logger.info(
            "Settings loaded: high=%d%%, low=%d%%, quiet=%s, startup=%s",
            high,
            low,
            quiet_enabled,
            registry_startup,
        )

    def save_settings(self) -> None:
        """Save settings with validation."""
        if not self._validate_thresholds():
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please fix the validation errors before saving."
            )
            return

        try:
            high = self._high_slider.value()
            low = self._low_slider.value()

            if self._quiet_enabled.isChecked():
                quiet_start = self._quiet_start.currentText()
                quiet_end = self._quiet_end.currentText()
            else:
                quiet_start = "00:00"
                quiet_end = "00:00"

            if self._alarm_service:
                self._alarm_service.update_thresholds(high=high, low=low)
                logger.info("✅ AlarmService thresholds updated: high=%d%%, low=%d%%", high, low)

            self._settings.update(
                charge_threshold_high=high,
                charge_threshold_low=low,
                quiet_hours_start=quiet_start,
                quiet_hours_end=quiet_end,
                start_with_os=self._startup_check.isChecked(),
            )

            self._config.save()

            self._status_label.setText("✅ Settings saved!")
            self._status_label.setStyleSheet(f"color: {COLORS['success']}; padding: {SPACING['xs']}px;")

            QTimer.singleShot(3000, lambda: self._status_label.setText(""))

            self.settings_saved.emit()
            logger.info("✅ Settings saved")

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings: {e}"
            )

    def reset_settings(self) -> None:
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._config.reset()

            if self._alarm_service:
                self._alarm_service.update_thresholds(
                    high=DEFAULT_CHARGE_THRESHOLD_HIGH,
                    low=DEFAULT_CHARGE_THRESHOLD_LOW,
                )
                logger.info("AlarmService reset to defaults")

            # Also reset registry startup
            set_auto_start(False)

            self.load_settings()
            self._status_label.setText("↩️ Reset to defaults")
            self._status_label.setStyleSheet(f"color: {COLORS['warning']}; padding: {SPACING['xs']}px;")
            logger.info("Settings reset to defaults")