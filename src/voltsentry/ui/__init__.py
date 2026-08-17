"""
FILE: src/voltsentry/ui/__init__.py
PATH: voltsentry/src/voltsentry/ui/__init__.py
DESCRIPTION: UI module exports
PHASE: 4 - System Tray & Dashboard UI
"""

"""UI layer - PyQt6 GUI components for VoltSentry."""

from .dashboard import DashboardWindow
from .health_graph import HealthGraph
from .history_log import HistoryLogView
from .settings_panel import SettingsPanel
from .styles import (
    COLORS,
    FONTS,
    MAIN_STYLESHEET,
    SPACING,
    get_battery_class,
    get_status_color,
)
from .tray import TrayIcon
from .widgets.alert_banner import AlertBanner
from .widgets.status_card import StatusCard

__all__ = [
    "TrayIcon",
    "DashboardWindow",
    "SettingsPanel",
    "HealthGraph",
    "HistoryLogView",
    "MAIN_STYLESHEET",
    "COLORS",
    "FONTS",
    "SPACING",
    "get_battery_class",
    "get_status_color",
    "StatusCard",
    "AlertBanner",
]