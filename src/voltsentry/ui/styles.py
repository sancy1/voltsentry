"""
FILE: src/voltsentry/ui/styles.py
PATH: voltsentry/src/voltsentry/ui/styles.py
DESCRIPTION: Centralized Windows 11 native styling for VoltSentry UI
PHASE: 4 - System Tray & Dashboard UI

DISCIPLINES:
- 0.1 Logging: Debug for style loading
- DRY: Single source of truth for all styles
"""

"""Windows 11 native styling for VoltSentry UI."""

# ============================================================================
# Windows 11 Color Palette
# ============================================================================
COLORS = {
    # Primary
    "primary": "#0078D4",           # Windows Blue
    "primary_dark": "#106EBE",
    "primary_light": "#E5F1FB",
    
    # Accent
    "accent": "#FFB900",            # Windows Yellow
    
    # Status
    "success": "#107C10",           # Green
    "warning": "#FF8C00",           # Orange
    "danger": "#D13438",            # Red
    "info": "#0078D4",              # Blue
    
    # Neutral
    "white": "#FFFFFF",
    "black": "#000000",
    "gray_100": "#F3F3F3",
    "gray_200": "#E6E6E6",
    "gray_300": "#CCCCCC",
    "gray_400": "#ADADAD",
    "gray_500": "#8A8A8A",
    "gray_600": "#666666",
    "gray_700": "#4A4A4A",
    "gray_800": "#2E2E2E",
    "gray_900": "#1A1A1A",
    
    # Battery status colors
    "battery_high": "#107C10",      # Green - 60-100%
    "battery_medium": "#FF8C00",    # Orange - 20-59%
    "battery_low": "#D13438",       # Red - 0-19%
    "battery_charging": "#0078D4",  # Blue - charging
}


# ============================================================================
# Windows 11 Typography
# ============================================================================
FONTS = {
    "family": "Segoe UI, Segoe UI Variable Display, sans-serif",
    "size_small": "11px",
    "size_normal": "13px",
    "size_medium": "15px",
    "size_large": "18px",
    "size_xlarge": "24px",
    "size_xxlarge": "32px",
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",
}


# ============================================================================
# Windows 11 Spacing
# ============================================================================
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
    "xxxl": 48,
}


# ============================================================================
# Windows 11 Border Radius
# ============================================================================
RADIUS = {
    "sm": 2,
    "md": 4,
    "lg": 8,
    "xl": 12,
    "circle": 999,
}


# ============================================================================
# Main Application Stylesheet - NO word-wrap (handled in Python code)
# ============================================================================
MAIN_STYLESHEET = f"""
/* ============================================================================
   Main Window - Windows 11 Native Look
   ============================================================================ */
QMainWindow, QWidget {{
    background-color: {COLORS['white']};
    font-family: {FONTS['family']};
    font-size: {FONTS['size_normal']};
    color: {COLORS['gray_900']};
}}

/* ============================================================================
   Title Bar - Windows 11 Style
   ============================================================================ */
QMenuBar {{
    background-color: {COLORS['white']};
    border: none;
    padding: {SPACING['sm']}px 0;
    font-size: {FONTS['size_normal']};
}}

QMenuBar::item {{
    background: transparent;
    padding: {SPACING['sm']}px {SPACING['lg']}px;
    border-radius: {RADIUS['sm']}px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['gray_200']};
}}

QMenu {{
    background-color: {COLORS['white']};
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['sm']}px;
}}

QMenu::item {{
    padding: {SPACING['sm']}px {SPACING['xl']}px;
    border-radius: {RADIUS['md']}px;
}}

QMenu::item:selected {{
    background-color: {COLORS['primary_light']};
    color: {COLORS['primary']};
}}

/* ============================================================================
   Cards / Containers
   ============================================================================ */
.card {{
    background-color: {COLORS['gray_100']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['lg']}px;
    margin: {SPACING['sm']}px;
}}

.card-title {{
    font-size: {FONTS['size_medium']};
    font-weight: {FONTS['weight_semibold']};
    color: {COLORS['gray_700']};
    margin-bottom: {SPACING['md']}px;
}}

.card-value {{
    font-size: {FONTS['size_xlarge']};
    font-weight: {FONTS['weight_bold']};
    color: {COLORS['gray_900']};
}}

.card-subtitle {{
    font-size: {FONTS['size_small']};
    color: {COLORS['gray_500']};
}}

/* ============================================================================
   Status Cards
   ============================================================================ */
.status-card {{
    background-color: {COLORS['gray_100']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['lg']}px;
    min-width: 120px;
    border-left: 4px solid {COLORS['gray_300']};
}}

.status-card.success {{
    border-left-color: {COLORS['success']};
}}
.status-card.success .value {{
    color: {COLORS['success']};
}}

.status-card.warning {{
    border-left-color: {COLORS['warning']};
}}
.status-card.warning .value {{
    color: {COLORS['warning']};
}}

.status-card.danger {{
    border-left-color: {COLORS['danger']};
}}
.status-card.danger .value {{
    color: {COLORS['danger']};
}}

.status-card.info {{
    border-left-color: {COLORS['info']};
}}
.status-card.info .value {{
    color: {COLORS['info']};
}}

/* ============================================================================
   Buttons - Windows 11 Style
   ============================================================================ */
QPushButton {{
    background-color: {COLORS['gray_200']};
    border: none;
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px {SPACING['lg']}px;
    font-family: {FONTS['family']};
    font-size: {FONTS['size_normal']};
    font-weight: {FONTS['weight_medium']};
    color: {COLORS['gray_900']};
    min-height: 32px;
}}

QPushButton:hover {{
    background-color: {COLORS['gray_300']};
}}

QPushButton:pressed {{
    background-color: {COLORS['gray_400']};
}}

QPushButton:disabled {{
    color: {COLORS['gray_500']};
}}

/* Primary Button */
QPushButton#primaryButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['white']};
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS['primary_dark']};
}}

QPushButton#primaryButton:pressed {{
    background-color: {COLORS['primary_dark']};
}}

/* Danger Button */
QPushButton#dangerButton {{
    background-color: {COLORS['danger']};
    color: {COLORS['white']};
}}

QPushButton#dangerButton:hover {{
    background-color: #A6262E;
}}

/* ============================================================================
   Sliders - Windows 11 Style
   ============================================================================ */
QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['gray_300']};
    border-radius: {RADIUS['sm']}px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['primary']};
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: {RADIUS['circle']}px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['primary_dark']};
    width: 20px;
    height: 20px;
    margin: -7px 0;
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['primary']};
    border-radius: {RADIUS['sm']}px;
}}

/* ============================================================================
   Labels
   ============================================================================ */
QLabel {{
    color: {COLORS['gray_900']};
}}

QLabel#heading {{
    font-size: {FONTS['size_large']};
    font-weight: {FONTS['weight_bold']};
    color: {COLORS['gray_900']};
}}

QLabel#subheading {{
    font-size: {FONTS['size_medium']};
    font-weight: {FONTS['weight_medium']};
    color: {COLORS['gray_600']};
}}

QLabel#small {{
    font-size: {FONTS['size_small']};
    color: {COLORS['gray_500']};
}}

QLabel#percent {{
    font-size: {FONTS['size_xxlarge']};
    font-weight: {FONTS['weight_bold']};
}}

/* ============================================================================
   Scrollbar - Windows 11 Style
   ============================================================================ */
QScrollBar:vertical {{
    background: {COLORS['gray_100']};
    width: 12px;
    border-radius: {RADIUS['md']}px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['gray_400']};
    min-height: 20px;
    border-radius: {RADIUS['md']}px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['gray_500']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ============================================================================
   Table - Windows 11 Style
   ============================================================================ */
QTableWidget {{
    background-color: {COLORS['white']};
    alternate-background-color: {COLORS['gray_100']};
    gridline-color: {COLORS['gray_200']};
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['md']}px;
}}

QTableWidget::item {{
    padding: {SPACING['sm']}px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary_light']};
    color: {COLORS['primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['gray_200']};
    padding: {SPACING['sm']}px;
    border: none;
    font-weight: {FONTS['weight_semibold']};
}}

/* ============================================================================
   Combobox
   ============================================================================ */
QComboBox {{
    background-color: {COLORS['gray_100']};
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px;
    min-height: 28px;
}}

QComboBox:hover {{
    border-color: {COLORS['primary']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: {SPACING['sm']}px;
}}

/* ============================================================================
   Checkbox
   ============================================================================ */
QCheckBox {{
    spacing: {SPACING['sm']}px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: {RADIUS['sm']}px;
}}

/* ============================================================================
   Alert Banner
   ============================================================================ */
.alert-banner {{
    background-color: {COLORS['gray_100']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['md']}px {SPACING['lg']}px;
    margin: {SPACING['sm']}px 0;
}}

.alert-banner.success {{
    background-color: #DFF6DD;
    border-left: 4px solid {COLORS['success']};
}}

.alert-banner.warning {{
    background-color: #FFF4CE;
    border-left: 4px solid {COLORS['warning']};
}}

.alert-banner.danger {{
    background-color: #FDE7E9;
    border-left: 4px solid {COLORS['danger']};
}}

.alert-banner.info {{
    background-color: {COLORS['primary_light']};
    border-left: 4px solid {COLORS['info']};
}}

/* ============================================================================
   Tooltip
   ============================================================================ */
QToolTip {{
    background-color: {COLORS['gray_800']};
    color: {COLORS['white']};
    border: none;
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px {SPACING['lg']}px;
    font-size: {FONTS['size_small']};
}}

/* ============================================================================
   Progress Bar - Battery Style
   ============================================================================ */
QProgressBar {{
    height: 12px;
    background: {COLORS['gray_200']};
    border-radius: {RADIUS['md']}px;
    text-align: center;
    font-size: {FONTS['size_small']};
    font-weight: {FONTS['weight_medium']};
    color: {COLORS['gray_700']};
}}

QProgressBar::chunk {{
    border-radius: {RADIUS['md']}px;
}}

/* Battery colors for progress bar */
.battery-critical::chunk {{
    background: {COLORS['battery_low']};
}}

.battery-low::chunk {{
    background: {COLORS['battery_low']};
}}

.battery-medium::chunk {{
    background: {COLORS['battery_medium']};
}}

.battery-high::chunk {{
    background: {COLORS['battery_high']};
}}

.battery-charging::chunk {{
    background: {COLORS['battery_charging']};
}}

/* ============================================================================
   Group Box
   ============================================================================ */
QGroupBox {{
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['lg']}px;
    margin-top: {SPACING['lg']}px;
    padding: {SPACING['lg']}px;
    font-weight: {FONTS['weight_semibold']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {SPACING['lg']}px;
    padding: 0 {SPACING['sm']}px;
    color: {COLORS['gray_600']};
}}

/* ============================================================================
   Line Edit
   ============================================================================ */
QLineEdit {{
    background-color: {COLORS['gray_100']};
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px;
    min-height: 28px;
}}

QLineEdit:focus {{
    border-color: {COLORS['primary']};
}}

/* ============================================================================
   Tab Widget
   ============================================================================ */
QTabWidget::pane {{
    border: 1px solid {COLORS['gray_300']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['lg']}px;
    background: {COLORS['white']};
}}

QTabBar::tab {{
    background: {COLORS['gray_200']};
    padding: {SPACING['sm']}px {SPACING['lg']}px;
    border: none;
    border-top-left-radius: {RADIUS['md']}px;
    border-top-right-radius: {RADIUS['md']}px;
    margin-right: 2px;
    font-weight: {FONTS['weight_medium']};
}}

QTabBar::tab:selected {{
    background: {COLORS['primary']};
    color: {COLORS['white']};
}}

QTabBar::tab:hover:!selected {{
    background: {COLORS['gray_300']};
}}
"""


def get_battery_class(percent: int, is_charging: bool) -> str:
    """
    Get CSS class for battery progress bar based on percent.
    
    Args:
        percent: Battery percentage (0-100)
        is_charging: True if charging
    
    Returns:
        CSS class name
    """
    if is_charging:
        return "battery-charging"
    elif percent >= 60:
        return "battery-high"
    elif percent >= 20:
        return "battery-medium"
    else:
        return "battery-low"


def get_status_color(percent: int, is_charging: bool) -> str:
    """
    Get status color based on battery level.
    
    Args:
        percent: Battery percentage (0-100)
        is_charging: True if charging
    
    Returns:
        Color hex string
    """
    if is_charging:
        return COLORS["battery_charging"]
    elif percent >= 60:
        return COLORS["battery_high"]
    elif percent >= 20:
        return COLORS["battery_medium"]
    else:
        return COLORS["battery_low"]