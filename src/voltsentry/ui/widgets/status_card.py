# """
# FILE: src/voltsentry/ui/widgets/status_card.py
# PATH: voltsentry/src/voltsentry/ui/widgets/status_card.py
# DESCRIPTION: Reusable status card widget for dashboard
# PHASE: 4.2 - Dashboard Main Window

# DISCIPLINES:
# - DRY: Reusable widget used across dashboard
# - 0.2 Error Handling: Rendering wrapped individually
# """

# from typing import Optional
# from PyQt6.QtCore import Qt, pyqtSignal
# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QFrame,
# )
# from ..styles import COLORS, FONTS, SPACING, RADIUS


# class StatusCard(QFrame):
#     """
#     Reusable status card widget.

#     Features:
#     - Title, value, subtitle
#     - Optional icon/emoji
#     - Status color border
#     - Clickable signal
#     """

#     clicked = pyqtSignal()

#     def __init__(
#         self,
#         title: str,
#         value: str,
#         subtitle: str = "",
#         icon: str = "",
#         status: str = "info",  # info, success, warning, danger
#         parent: Optional[QWidget] = None,
#     ):
#         super().__init__(parent)
#         self._title = title
#         self._value = value
#         self._subtitle = subtitle
#         self._icon = icon
#         self._status = status

#         self._setup_ui()
#         self._apply_styles()

#     def _setup_ui(self) -> None:
#         """Set up the UI layout."""
#         # Main layout
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(
#             SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
#         )
#         layout.setSpacing(SPACING["sm"])

#         # Top row: icon + title
#         top_layout = QHBoxLayout()
#         top_layout.setSpacing(SPACING["sm"])

#         # Icon
#         if self._icon:
#             self._icon_label = QLabel(self._icon)
#             self._icon_label.setStyleSheet(f"font-size: {FONTS['size_large']};")
#             top_layout.addWidget(self._icon_label)

#         # Title
#         self._title_label = QLabel(self._title)
#         self._title_label.setStyleSheet(f"""
#             font-size: {FONTS['size_small']};
#             color: {COLORS['gray_600']};
#             font-weight: {FONTS['weight_medium']};
#         """)
#         top_layout.addWidget(self._title_label)
#         top_layout.addStretch()

#         layout.addLayout(top_layout)

#         # Value
#         self._value_label = QLabel(self._value)
#         self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self._value_label.setStyleSheet(f"""
#             font-size: {FONTS['size_xlarge']};
#             font-weight: {FONTS['weight_bold']};
#             color: {COLORS['gray_900']};
#         """)
#         layout.addWidget(self._value_label)

#         # Subtitle
#         if self._subtitle:
#             self._subtitle_label = QLabel(self._subtitle)
#             self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#             self._subtitle_label.setStyleSheet(f"""
#                 font-size: {FONTS['size_small']};
#                 color: {COLORS['gray_500']};
#             """)
#             layout.addWidget(self._subtitle_label)

#         # Set minimum size
#         self.setMinimumWidth(120)
#         self.setMinimumHeight(100)

#     def _apply_styles(self) -> None:
#         """Apply status-specific styles."""
#         status_color = {
#             "info": COLORS["info"],
#             "success": COLORS["success"],
#             "warning": COLORS["warning"],
#             "danger": COLORS["danger"],
#         }.get(self._status, COLORS["gray_300"])

#         self.setStyleSheet(f"""
#             StatusCard {{
#                 background-color: {COLORS['gray_100']};
#                 border-radius: {RADIUS['lg']}px;
#                 border-left: 4px solid {status_color};
#             }}
#             StatusCard:hover {{
#                 background-color: {COLORS['gray_200']};
#             }}
#         """)

#     def set_value(self, value: str) -> None:
#         """Update the value displayed."""
#         self._value = value
#         self._value_label.setText(value)

#     def set_subtitle(self, subtitle: str) -> None:
#         """Update the subtitle."""
#         self._subtitle = subtitle
#         if hasattr(self, "_subtitle_label"):
#             self._subtitle_label.setText(subtitle)

#     def set_status(self, status: str) -> None:
#         """Update the status color."""
#         self._status = status
#         self._apply_styles()

#     def mousePressEvent(self, event) -> None:
#         """Handle mouse click."""
#         self.clicked.emit()
#         super().mousePressEvent(event)

#     def enterEvent(self, event) -> None:
#         """Handle mouse enter."""
#         self.setCursor(Qt.CursorShape.PointingHandCursor)
#         super().enterEvent(event)

#     def leaveEvent(self, event) -> None:
#         """Handle mouse leave."""
#         self.unsetCursor()
#         super().leaveEvent(event)








































"""
FILE: src/voltsentry/ui/widgets/status_card.py
PATH: voltsentry/src/voltsentry/ui/widgets/status_card.py
DESCRIPTION: Reusable status card widget with proper text wrapping
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from ..styles import COLORS, FONTS, SPACING, RADIUS


class StatusCard(QFrame):
    """
    Reusable status card widget with proper text wrapping.

    Features:
    - Title, value, subtitle with word wrap
    - Left-aligned text (better readability)
    - Status color border
    - Clickable signal
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        icon: str = "",
        status: str = "info",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._icon = icon
        self._status = status

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """Set up the UI layout with proper text wrapping."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["md"]
        )
        layout.setSpacing(SPACING["xs"])

        # Title
        self._title_label = QLabel(self._title)
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            font-weight: {FONTS['weight_medium']};
            color: {COLORS['gray_600']};
            text-transform: uppercase;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(self._title_label)

        # Value - large, bold, left-aligned, with word wrap
        self._value_label = QLabel(self._value)
        self._value_label.setWordWrap(True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._value_label.setStyleSheet(f"""
            font-size: {FONTS['size_xxlarge']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['gray_900']};
            line-height: 1.2;
            min-height: 40px;
        """)
        layout.addWidget(self._value_label)

        # Subtitle - with word wrap
        self._subtitle_label = QLabel(self._subtitle)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._subtitle_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._subtitle_label.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_500']};
        """)
        layout.addWidget(self._subtitle_label)

        self.setMinimumHeight(100)
        self.setMinimumWidth(120)

    def _apply_styles(self) -> None:
        """Apply status-specific styles."""
        status_color = {
            "info": COLORS["info"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }.get(self._status, COLORS["gray_300"])

        self.setStyleSheet(f"""
            StatusCard {{
                background-color: {COLORS['white']};
                border: 1px solid {COLORS['gray_200']};
                border-radius: {RADIUS['lg']}px;
                border-left: 4px solid {status_color};
            }}
            StatusCard:hover {{
                background-color: {COLORS['gray_100']};
                border-color: {COLORS['gray_300']};
            }}
        """)

        # Update value color based on status
        self._value_label.setStyleSheet(f"""
            font-size: {FONTS['size_xxlarge']};
            font-weight: {FONTS['weight_bold']};
            color: {status_color};
            line-height: 1.2;
            min-height: 40px;
        """)

    def set_value(self, value: str) -> None:
        """Update the value displayed."""
        self._value = value
        self._value_label.setText(value)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle."""
        self._subtitle = subtitle
        self._subtitle_label.setText(subtitle)

    def set_status(self, status: str) -> None:
        """Update the status color."""
        self._status = status
        self._apply_styles()

    def mousePressEvent(self, event) -> None:
        """Handle mouse click."""
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter."""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave."""
        self.unsetCursor()
        super().leaveEvent(event)