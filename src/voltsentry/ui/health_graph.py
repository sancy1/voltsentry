"""
FILE: src/voltsentry/ui/health_graph.py
PATH: voltsentry/src/voltsentry/ui/health_graph.py
DESCRIPTION: Battery health graph using matplotlib
PHASE: 4.4 - Health Graph

DISCIPLINES:
- 0.1 Logging: DEBUG for empty graph (expected)
- 0.2 Error Handling: Matplotlib rendering wrapped
- 0.4 Fallback: Placeholder on insufficient data
"""

from datetime import datetime, timedelta
from typing import Optional, List
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
)
from PyQt6.QtGui import QFont

import matplotlib
import matplotlib.dates as mdates

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit
from ..db.repositories import BatteryReadingRepository
from ..db.models import BatteryReading
from .styles import COLORS, FONTS, RADIUS, SPACING

logger = get_logger(__name__)


class HealthGraph(QWidget):
    """
    Battery health graph using matplotlib.

    Features:
    - 30/90/365 day views
    - Capacity degradation visualization
    - Placeholder for insufficient data
    - Each rendering wrapped with error handling
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._repository = BatteryReadingRepository()
        self._current_range = 30  # days
        self._data: List[BatteryReading] = []

        self._setup_ui()
        self._setup_canvas()

        logger.info("HealthGraph initialized")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING["md"])

        # Control bar
        control_layout = QHBoxLayout()
        control_layout.setSpacing(SPACING["sm"])

        self._title_label = QLabel("📈 Battery Health Trends")
        self._title_label.setStyleSheet(f"""
            font-size: {FONTS['size_medium']};
            font-weight: {FONTS['weight_semibold']};
            color: {COLORS['gray_700']};
        """)
        control_layout.addWidget(self._title_label)

        control_layout.addStretch()

        # Range buttons
        for days, label in [(30, "30D"), (90, "90D"), (365, "1Y")]:
            btn = QPushButton(label)
            btn.setFixedWidth(50)
            btn.setCheckable(True)
            btn.setProperty("days", days)
            btn.clicked.connect(lambda checked, d=days: self._set_range(d))
            control_layout.addWidget(btn)
            setattr(self, f"_range_btn_{days}", btn)

        self._range_btn_30.setChecked(True)

        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        control_layout.addWidget(self._refresh_btn)

        layout.addLayout(control_layout)

        # Graph frame
        self._graph_frame = QFrame()
        self._graph_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['gray_100']};
                border-radius: {RADIUS['lg']}px;
            }}
        """)
        graph_layout = QVBoxLayout(self._graph_frame)
        graph_layout.setContentsMargins(
            SPACING["md"], SPACING["md"], SPACING["md"], SPACING["md"]
        )

        # Placeholder for matplotlib canvas
        self._canvas_placeholder = QLabel("Loading graph...")
        self._canvas_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas_placeholder.setStyleSheet(f"""
            color: {COLORS['gray_500']};
            font-size: {FONTS['size_medium']};
        """)
        graph_layout.addWidget(self._canvas_placeholder)

        layout.addWidget(self._graph_frame, 1)

        # Status
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {COLORS['gray_500']}; font-size: {FONTS['size_small']};"
        )
        layout.addWidget(self._status_label)

    def _setup_canvas(self) -> None:
        """Set up the matplotlib canvas."""
        # Create figure and canvas
        self._figure = Figure(figsize=(8, 4), dpi=100, facecolor="#F3F3F3")
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setParent(self)
        self._canvas.hide()

        # Add to graph frame
        self._graph_frame.layout().addWidget(self._canvas)

        # Set style
        self._figure.patch.set_facecolor("#F3F3F3")

        logger.debug("Matplotlib canvas created")

    def _set_range(self, days: int) -> None:
        """Set the time range for the graph."""
        self._current_range = days

        # Update button states
        for d in [30, 90, 365]:
            btn = getattr(self, f"_range_btn_{d}", None)
            if btn:
                btn.setChecked(d == days)

        self.refresh()

    @log_entry_exit()
    def refresh(self) -> None:
        """Refresh the graph with latest data."""
        try:
            # Get data
            from_date = datetime.now() - timedelta(days=self._current_range)
            self._data = self._repository.get_history(
                limit=10000,
                from_date=from_date,
            )

            if not self._data:
                logger.debug("No readings retrieved for the selected date range")
                self._show_placeholder("Not enough data yet — check back in a few days")
                return

            # Render graph
            self._render_graph()

            # Update status
            self._status_label.setText(
                f"Showing {len(self._data)} readings over {self._current_range} days"
            )

        except Exception as e:
            logger.error("Failed to refresh graph: %s", e)
            self._show_placeholder("⚠️ Graph temporarily unavailable")

    def _render_graph(self) -> None:
        """Render the graph with the current data."""
        try:
            self._canvas.show()
            self._canvas_placeholder.hide()

            # Clear figure
            self._figure.clear()
            ax = self._figure.add_subplot(111)

            # Extract data
            timestamps = [r.timestamp for r in self._data]
            percents = [r.percent for r in self._data]

            # Sort by timestamp
            sorted_data = sorted(zip(timestamps, percents))
            timestamps, percents = zip(*sorted_data)

            # Plot
            ax.plot(timestamps, percents, color=COLORS["primary"], linewidth=2, alpha=0.8)

            # Fill under curve
            ax.fill_between(timestamps, 0, percents, color=COLORS["primary"], alpha=0.1)

            # Style
            ax.set_facecolor("#FFFFFF")
            ax.grid(True, alpha=0.3, linestyle="--")
            ax.set_xlabel("Time", fontsize=10)
            ax.set_ylabel("Battery %", fontsize=10)
            ax.set_title(
                f"Battery Level - Last {self._current_range} Days",
                fontsize=12,
                fontweight="bold",
            )
            ax.set_ylim(0, 105)

            # Format x-axis
            if self._current_range <= 30:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            elif self._current_range <= 90:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

            # Rotate labels
            self._figure.autofmt_xdate()

            # Tight layout
            self._figure.tight_layout()

            # Draw
            self._canvas.draw()

            logger.debug("Graph rendered: %d data points", len(self._data))

        except Exception as e:
            logger.error("Failed to render graph: %s", e)
            self._show_placeholder("⚠️ Graph temporarily unavailable")

    def _show_placeholder(self, message: str) -> None:
        """Show a placeholder when no data is available."""
        self._canvas.hide()
        self._canvas_placeholder.setText(f"📊 {message}")
        self._canvas_placeholder.show()
        self._status_label.setText("No data available yet")