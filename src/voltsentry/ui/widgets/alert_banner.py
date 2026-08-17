# """
# FILE: src/voltsentry/ui/widgets/alert_banner.py
# PATH: voltsentry/src/voltsentry/ui/widgets/alert_banner.py
# DESCRIPTION: In-app alert banner widget
# PHASE: 4.2 - Dashboard Main Window

# DISCIPLINES:
# - 0.1 Logging: DEBUG for visibility changes
# - 0.2 Error Handling: Rendering wrapped
# """

# from typing import Optional

# from PyQt6.QtCore import Qt, QTimer, pyqtSignal
# from PyQt6.QtWidgets import (
#     QWidget,
#     QHBoxLayout,
#     QLabel,
#     QPushButton,
#     QFrame,
# )

# from ..styles import COLORS, FONTS, SPACING, RADIUS


# class AlertBanner(QFrame):
#     """
#     In-app alert banner widget.

#     Features:
#     - Multiple alert levels (info, success, warning, danger)
#     - Dismiss button
#     - Auto-dismiss timer
#     - Snooze button for alarms
#     """

#     dismissed = pyqtSignal()
#     snoozed = pyqtSignal()

#     def __init__(
#         self,
#         message: str = "",
#         alert_type: str = "info",  # info, success, warning, danger
#         show_snooze: bool = False,
#         auto_dismiss_seconds: int = 0,
#         parent: Optional[QWidget] = None,
#     ):
#         super().__init__(parent)
#         self._message = message
#         self._alert_type = alert_type
#         self._show_snooze = show_snooze
#         self._auto_dismiss_seconds = auto_dismiss_seconds
#         self._visible = False

#         self._setup_ui()
#         self._apply_styles()

#         if auto_dismiss_seconds > 0:
#             self._setup_auto_dismiss()

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(
#             SPACING["md"], SPACING["sm"], SPACING["md"], SPACING["sm"]
#         )
#         layout.setSpacing(SPACING["md"])

#         # Icon
#         icons = {
#             "info": "ℹ️",
#             "success": "✅",
#             "warning": "⚠️",
#             "danger": "🔴",
#         }
#         icon = icons.get(self._alert_type, "ℹ️")
#         self._icon_label = QLabel(icon)
#         self._icon_label.setStyleSheet(f"font-size: {FONTS['size_large']};")
#         layout.addWidget(self._icon_label)

#         # Message
#         self._message_label = QLabel(self._message)
#         self._message_label.setWordWrap(True)
#         self._message_label.setStyleSheet(f"""
#             font-size: {FONTS['size_normal']};
#             font-weight: {FONTS['weight_medium']};
#             color: {COLORS['gray_900']};
#         """)
#         layout.addWidget(self._message_label, 1)

#         # Snooze button
#         if self._show_snooze:
#             self._snooze_button = QPushButton("😴 Snooze")
#             self._snooze_button.setObjectName("primaryButton")
#             self._snooze_button.clicked.connect(self.snoozed.emit)
#             self._snooze_button.setFixedHeight(28)
#             layout.addWidget(self._snooze_button)

#         # Dismiss button
#         self._dismiss_button = QPushButton("✕")
#         self._dismiss_button.setFixedSize(28, 28)
#         self._dismiss_button.setStyleSheet(f"""
#             QPushButton {{
#                 background: transparent;
#                 border: none;
#                 font-size: {FONTS['size_medium']};
#                 color: {COLORS['gray_500']};
#                 border-radius: {RADIUS['circle']}px;
#             }}
#             QPushButton:hover {{
#                 background: {COLORS['gray_300']};
#             }}
#         """)
#         self._dismiss_button.clicked.connect(self.dismiss)
#         layout.addWidget(self._dismiss_button)

#         # Initially hidden
#         self.hide()

#     def _apply_styles(self) -> None:
#         """Apply alert type-specific styles."""
#         bg_colors = {
#             "info": COLORS["primary_light"],
#             "success": "#DFF6DD",
#             "warning": "#FFF4CE",
#             "danger": "#FDE7E9",
#         }
#         border_colors = {
#             "info": COLORS["info"],
#             "success": COLORS["success"],
#             "warning": COLORS["warning"],
#             "danger": COLORS["danger"],
#         }

#         bg = bg_colors.get(self._alert_type, COLORS["gray_100"])
#         border = border_colors.get(self._alert_type, COLORS["gray_300"])

#         self.setStyleSheet(f"""
#             AlertBanner {{
#                 background-color: {bg};
#                 border-radius: {RADIUS['lg']}px;
#                 border-left: 4px solid {border};
#                 margin: {SPACING['sm']}px;
#             }}
#         """)

#     def _setup_auto_dismiss(self) -> None:
#         """Set up auto-dismiss timer."""
#         self._dismiss_timer = QTimer()
#         self._dismiss_timer.setSingleShot(True)
#         self._dismiss_timer.timeout.connect(self.dismiss)

#     def show_alert(
#         self,
#         message: Optional[str] = None,
#         alert_type: Optional[str] = None,
#         show_snooze: Optional[bool] = None,
#     ) -> None:
#         """
#         Show the alert banner.

#         Args:
#             message: Alert message (updates if provided)
#             alert_type: Alert type (updates if provided)
#             show_snooze: Show snooze button (updates if provided)
#         """
#         if message is not None:
#             self._message = message
#             self._message_label.setText(message)

#         if alert_type is not None:
#             self._alert_type = alert_type
#             icons = {
#                 "info": "ℹ️",
#                 "success": "✅",
#                 "warning": "⚠️",
#                 "danger": "🔴",
#             }
#             self._icon_label.setText(icons.get(alert_type, "ℹ️"))
#             self._apply_styles()

#         if show_snooze is not None:
#             self._show_snooze = show_snooze
#             if hasattr(self, "_snooze_button"):
#                 self._snooze_button.setVisible(show_snooze)

#         self.show()
#         self._visible = True

#         # Start auto-dismiss timer if set
#         if self._auto_dismiss_seconds > 0:
#             self._dismiss_timer.start(self._auto_dismiss_seconds * 1000)

#     def dismiss(self) -> None:
#         """Dismiss the alert banner."""
#         self.hide()
#         self._visible = False
#         if hasattr(self, "_dismiss_timer"):
#             self._dismiss_timer.stop()
#         self.dismissed.emit()

#     def is_visible(self) -> bool:
#         """Check if the banner is visible."""
#         return self._visible

#     def set_message(self, message: str) -> None:
#         """Update the message."""
#         self._message = message
#         self._message_label.setText(message)
































"""
FILE: src/voltsentry/ui/widgets/alert_banner.py
PATH: voltsentry/src/voltsentry/ui/widgets/alert_banner.py
DESCRIPTION: In-app alert banner - pushes content down when visible
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from ..styles import COLORS, FONTS, SPACING, RADIUS


class AlertBanner(QFrame):
    """
    In-app alert banner.
    Stays visible until user dismisses or snoozes.
    Pushes content down when visible (does NOT overlap).
    """

    dismissed = pyqtSignal()
    snoozed = pyqtSignal()

    def __init__(
        self,
        message: str = "",
        alert_type: str = "info",
        show_snooze: bool = False,
        auto_dismiss_seconds: int = 0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._message = message
        self._alert_type = alert_type
        self._show_snooze = show_snooze
        self._visible = False

        # IMPORTANT: Allow the banner to expand vertically
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setVisible(False)

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI layout with proper sizing."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING["md"], SPACING["sm"], SPACING["md"], SPACING["sm"])
        layout.setSpacing(SPACING["md"])

        # Icon
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "danger": "🔴",
        }
        icon = icons.get(self._alert_type, "ℹ️")
        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet(f"font-size: {FONTS['size_large']};")
        self._icon_label.setFixedWidth(30)
        layout.addWidget(self._icon_label)

        # Message - with word wrap!
        self._message_label = QLabel(self._message)
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._message_label.setStyleSheet(f"""
            font-size: {FONTS['size_normal']};
            font-weight: {FONTS['weight_medium']};
            color: {COLORS['gray_900']};
        """)
        layout.addWidget(self._message_label, 1)

        # Snooze button
        self._snooze_button = QPushButton("😴 Snooze")
        self._snooze_button.setObjectName("primaryButton")
        self._snooze_button.clicked.connect(self.snoozed.emit)
        self._snooze_button.setFixedHeight(32)
        self._snooze_button.setVisible(self._show_snooze)
        layout.addWidget(self._snooze_button)

        # Dismiss button
        self._dismiss_button = QPushButton("✕")
        self._dismiss_button.setFixedSize(32, 32)
        self._dismiss_button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: {FONTS['size_medium']};
                color: {COLORS['gray_500']};
                border-radius: {RADIUS['circle']}px;
            }}
            QPushButton:hover {{
                background: {COLORS['gray_300']};
            }}
        """)
        self._dismiss_button.clicked.connect(self.dismiss)
        layout.addWidget(self._dismiss_button)

    def _apply_styles(self) -> None:
        """Apply alert type-specific styles."""
        bg_colors = {
            "info": COLORS["primary_light"],
            "success": "#DFF6DD",
            "warning": "#FFF4CE",
            "danger": "#FDE7E9",
        }
        border_colors = {
            "info": COLORS["info"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }

        bg = bg_colors.get(self._alert_type, COLORS["gray_100"])
        border = border_colors.get(self._alert_type, COLORS["gray_300"])

        self.setStyleSheet(f"""
            AlertBanner {{
                background-color: {bg};
                border-radius: {RADIUS['lg']}px;
                border-left: 4px solid {border};
                margin: {SPACING['sm']}px 0;
                min-height: 40px;
            }}
        """)

    def show_alert(
        self,
        message: Optional[str] = None,
        alert_type: Optional[str] = None,
        show_snooze: Optional[bool] = None,
    ) -> None:
        """Show the alert banner - PUSHES CONTENT DOWN."""
        if message is not None:
            self._message = message
            self._message_label.setText(message)

        if alert_type is not None:
            self._alert_type = alert_type
            icons = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "danger": "🔴",
            }
            self._icon_label.setText(icons.get(alert_type, "ℹ️"))
            self._apply_styles()

        if show_snooze is not None:
            self._show_snooze = show_snooze
            self._snooze_button.setVisible(show_snooze)

        # Make visible - this will push content down
        self.setVisible(True)
        self._visible = True

        # Force layout update
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def dismiss(self) -> None:
        """Dismiss the alert banner - CONTENT MOVES BACK UP."""
        self.setVisible(False)
        self._visible = False
        self.dismissed.emit()

        # Force layout update
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def is_visible(self) -> bool:
        """Check if the banner is visible."""
        return self._visible

    def set_message(self, message: str) -> None:
        """Update the message."""
        self._message = message
        self._message_label.setText(message)