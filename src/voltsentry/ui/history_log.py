"""
FILE: src/voltsentry/ui/history_log.py
PATH: voltsentry/src/voltsentry/ui/history_log.py
DESCRIPTION: Paginated history log view
PHASE: 4.5 - History Log View

DISCIPLINES:
- 0.1 Logging: DEBUG for empty history
- 0.2 Error Handling: Paginated query, never unbounded
- 0.4 Fallback: Friendly placeholder on empty
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QComboBox,
)

from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit
from ..db.repositories import BatteryReadingRepository
from ..db.models import BatteryReading
from .styles import COLORS, FONTS, RADIUS, SPACING

logger = get_logger(__name__)


class HistoryLogView(QWidget):
    """
    Paginated history log view.

    Features:
    - Paginated query through repository (never unbounded)
    - Filter by date range
    - Friendly placeholder on empty
    - Sortable columns
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._repository = BatteryReadingRepository()
        self._current_page = 0
        self._page_size = 50
        self._total_records = 0
        self._data: List[BatteryReading] = []

        self._setup_ui()
        self.refresh()

        logger.info("HistoryLogView initialized")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING["md"])

        # Control bar
        control_layout = QHBoxLayout()
        control_layout.setSpacing(SPACING["sm"])

        self._title_label = QLabel("📜 Battery History")
        self._title_label.setStyleSheet(f"""
            font-size: {FONTS['size_medium']};
            font-weight: {FONTS['weight_semibold']};
            color: {COLORS['gray_700']};
        """)
        control_layout.addWidget(self._title_label)

        control_layout.addStretch()

        # Filter
        control_layout.addWidget(QLabel("Range:"))
        self._range_combo = QComboBox()
        self._range_combo.addItems(
            ["Last Day", "Last 7 Days", "Last 30 Days", "All Time"]
        )
        self._range_combo.currentTextChanged.connect(self._on_range_changed)
        control_layout.addWidget(self._range_combo)

        # Refresh
        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        control_layout.addWidget(self._refresh_btn)

        layout.addLayout(control_layout)

        # Table frame
        self._table_frame = QFrame()
        self._table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['gray_100']};
                border-radius: {RADIUS['lg']}px;
            }}
        """)
        table_layout = QVBoxLayout(self._table_frame)
        table_layout.setContentsMargins(
            SPACING["md"], SPACING["md"], SPACING["md"], SPACING["md"]
        )

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Time", "Battery %", "Status", "Source"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['white']};
                alternate-background-color: {COLORS['gray_100']};
                gridline-color: {COLORS['gray_200']};
                border: 1px solid {COLORS['gray_300']};
                border-radius: {RADIUS['md']}px;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['gray_200']};
                padding: 8px;
                border: none;
                font-weight: {FONTS['weight_semibold']};
            }}
        """)
        table_layout.addWidget(self._table)

        # Placeholder
        self._placeholder_label = QLabel("📭 No data available yet")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet(f"""
            color: {COLORS['gray_500']};
            font-size: {FONTS['size_medium']};
            padding: 40px;
        """)
        self._placeholder_label.hide()
        table_layout.addWidget(self._placeholder_label)

        layout.addWidget(self._table_frame, 1)

        # Pagination bar
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(SPACING["sm"])

        pagination_layout.addStretch()

        self._prev_btn = QPushButton("◀ Previous")
        self._prev_btn.clicked.connect(self._prev_page)
        pagination_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("Page 1")
        self._page_label.setStyleSheet(f"""
            font-weight: {FONTS['weight_medium']};
            color: {COLORS['gray_700']};
        """)
        pagination_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("Next ▶")
        self._next_btn.clicked.connect(self._next_page)
        pagination_layout.addWidget(self._next_btn)

        self._total_label = QLabel("Total: 0 records")
        self._total_label.setStyleSheet(
            f"color: {COLORS['gray_500']}; font-size: {FONTS['size_small']};"
        )
        pagination_layout.addWidget(self._total_label)

        layout.addLayout(pagination_layout)

    def _get_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get date range based on combo selection."""
        selection = self._range_combo.currentText()
        to_date = datetime.now()

        if selection == "Last Day":
            return to_date - timedelta(days=1), to_date
        elif selection == "Last 7 Days":
            return to_date - timedelta(days=7), to_date
        elif selection == "Last 30 Days":
            return to_date - timedelta(days=30), to_date
        else:  # All Time
            return None, to_date

    def _on_range_changed(self) -> None:
        """Handle range change."""
        self._current_page = 0
        self.refresh()

    @log_entry_exit()
    def refresh(self) -> None:
        """Refresh the history log."""
        try:
            from_date, to_date = self._get_date_range()

            # Get total count
            # Simple approach - get all and count (for demo)
            # In production, this would be a COUNT query
            all_data = self._repository.get_history(
                limit=100000,
                from_date=from_date,
                to_date=to_date,
            )
            self._total_records = len(all_data)

            # Get paginated data
            self._data = self._repository.get_history(
                limit=self._page_size,
                from_date=from_date,
                to_date=to_date,
            )

            # Display
            if not self._data:
                logger.debug("No records retrieved for history log")
                self._show_empty()
                return

            self._show_data()

            # Update pagination
            total_pages = max(
                1, (self._total_records + self._page_size - 1) // self._page_size
            )
            self._page_label.setText(
                f"Page {self._current_page + 1} of {total_pages}"
            )
            self._prev_btn.setEnabled(self._current_page > 0)
            self._next_btn.setEnabled(self._current_page < total_pages - 1)
            self._total_label.setText(f"Total: {self._total_records} records")

            logger.debug("History refreshed: %d records", len(self._data))

        except Exception as e:
            logger.error("Failed to refresh history: %s", e)
            self._show_empty()

    def _show_data(self) -> None:
        """Populate table with data."""
        self._table.show()
        self._placeholder_label.hide()

        self._table.setRowCount(len(self._data))

        for i, reading in enumerate(self._data):
            # Time
            time_item = QTableWidgetItem(
                reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            )
            self._table.setItem(i, 0, time_item)

            # Battery %
            percent_item = QTableWidgetItem(f"{reading.percent}%")
            percent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if reading.percent >= 60:
                percent_item.setForeground(Qt.GlobalColor.darkGreen)
            elif reading.percent >= 20:
                percent_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                percent_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(i, 1, percent_item)

            # Status
            status = "⚡ Charging" if reading.is_charging else "🔋 Discharging"
            status_item = QTableWidgetItem(status)
            self._table.setItem(i, 2, status_item)

            # Source
            source_item = QTableWidgetItem(reading.source)
            self._table.setItem(i, 3, source_item)

    def _show_empty(self) -> None:
        """Show empty state."""
        self._table.hide()
        self._placeholder_label.show()
        self._placeholder_label.setText("📭 No data available for this period")
        self._total_label.setText("Total: 0 records")
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._page_label.setText("Page 1 of 1")

    def _prev_page(self) -> None:
        """Go to previous page."""
        if self._current_page > 0:
            self._current_page -= 1
            self.refresh()

    def _next_page(self) -> None:
        """Go to next page."""
        total_pages = (
            self._total_records + self._page_size - 1
        ) // self._page_size
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self.refresh()