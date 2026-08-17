"""
FILE: src/voltsentry/ui/calibration_wizard.py
PATH: voltsentry/src/voltsentry/ui/calibration_wizard.py
DESCRIPTION: GUI wizard for guided battery calibration
PHASE: 5.2 - Guided Calibration Mode
DISCIPLINES:
- 0.1 Logging: INFO on state transitions
- 0.2 Error Handling: Handles abort, sleep/wake
- BATTERY OPTIMIZATION: User-initiated only
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWidget,
    QWizardPage,
)

from ..core.logging_config import get_logger
from ..services.calibration import CalibrationService, CalibrationState
from .styles import COLORS, FONTS, RADIUS, SPACING

logger = get_logger(__name__)


class CalibrationWizard(QWizard):
    """
    Guided battery calibration wizard.

    Steps:
    1. Introduction
    2. Charge to 100%
    3. Discharge to 0%
    4. Complete
    """

    calibration_complete = pyqtSignal(int)  # health_score

    def __init__(
        self,
        calibration_service: CalibrationService,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.calibration_service = calibration_service

        # Setup wizard
        self.setWindowTitle("🔋 Battery Calibration Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(500, 400)
        self.resize(600, 450)

        # Add pages
        self.intro_page = IntroPage()
        self.charge_page = ChargePage()
        self.discharge_page = DischargePage()
        self.complete_page = CompletePage()

        self.addPage(self.intro_page)
        self.addPage(self.charge_page)
        self.addPage(self.discharge_page)
        self.addPage(self.complete_page)

        # Connect service signals
        self.calibration_service.add_state_change_callback(
            self._on_state_change
        )
        self.calibration_service.add_progress_callback(self._on_progress)
        self.calibration_service.add_complete_callback(self._on_complete)
        self.calibration_service.add_abort_callback(self._on_abort)

        # Start the service
        try:
            self.calibration_service.start_calibration()
        except Exception as e:
            logger.error("Failed to start calibration: %s", e)

        logger.info("CalibrationWizard initialized")

    def _on_state_change(
        self, old_state: CalibrationState, new_state: CalibrationState
    ) -> None:
        """Handle state change."""
        if new_state == CalibrationState.AWAITING_FULL_CHARGE:
            self.setCurrentId(1)  # Charge page
        elif new_state == CalibrationState.AWAITING_FULL_DISCHARGE:
            self.setCurrentId(2)  # Discharge page
        elif new_state == CalibrationState.COMPLETE:
            self.setCurrentId(3)  # Complete page
        elif new_state == CalibrationState.ABORTED:
            self.reject()

    def _on_progress(self, progress: int, message: str) -> None:
        """Handle progress update."""
        # Update current page's status
        current_page = self.currentPage()
        if hasattr(current_page, "update_status"):
            current_page.update_status(progress, message)

    def _on_complete(self, health_score: int) -> None:
        """Handle calibration complete."""
        self.calibration_complete.emit(health_score)
        self.setCurrentId(3)  # Complete page

    def _on_abort(self) -> None:
        """Handle calibration abort."""
        self.reject()

    def reject(self) -> None:
        """Handle wizard rejection (close/cancel)."""
        if self.calibration_service.is_active:
            self.calibration_service.abort_calibration()
        super().reject()


class IntroPage(QWizardPage):
    """Introduction page for calibration wizard."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("🔋 Battery Calibration")
        self.setSubTitle("Calibrate your battery for accurate health reporting")

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING["lg"])

        # Description
        desc = QLabel(
            "This wizard will guide you through a full battery calibration"
            " cycle.\n\n"
            "📌 What will happen:\n"
            "• Charge your battery to 100%\n"
            "• Discharge your battery to 0%\n"
            "• Recalculate battery health\n\n"
            "⏱️ This process may take several hours.\n"
            "🔌 Keep your laptop plugged in during the charge phase.\n"
            "⚠️ Do not use your laptop during the discharge phase."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            font-size: {FONTS['size_normal']};
            color: {COLORS['gray_700']};
            padding: {SPACING['md']}px;
        """)
        layout.addWidget(desc)

        layout.addStretch()

        # Progress note
        note = QLabel(
            "💡 Tip: Close other applications to speed up the process."
        )
        note.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_500']};
            font-style: italic;
        """)
        layout.addWidget(note)

    def initializePage(self) -> None:
        """Initialize the page."""
        self.setButtonText(
            QWizard.WizardButton.NextButton, "Start Calibration"
        )


class ChargePage(QWizardPage):
    """Charge phase page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("🔌 Step 1: Charge to 100%")
        self.setSubTitle("Plug in your laptop and wait for full charge")

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING["lg"])

        # Status
        self.status_label = QLabel("⏳ Charging... Please wait.")
        self.status_label.setStyleSheet(f"""
            font-size: {FONTS['size_medium']};
            font-weight: {FONTS['weight_semibold']};
            color: {COLORS['primary']};
        """)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                height: 20px;
                border-radius: {RADIUS['md']}px;
                background-color: {COLORS['gray_200']};
            }}
            QProgressBar::chunk {{
                border-radius: {RADIUS['md']}px;
                background-color: {COLORS['primary']};
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Instructions
        instructions = QLabel(
            "🔌 Keep your laptop plugged in.\n⚡ The battery will charge to 100%."
        )
        instructions.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_600']};
            padding: {SPACING['md']}px;
            background-color: {COLORS['gray_100']};
            border-radius: {RADIUS['lg']}px;
        """)
        layout.addWidget(instructions)

        layout.addStretch()

    def update_status(self, progress: int, message: str) -> None:
        """Update status display."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def initializePage(self) -> None:
        """Initialize the page."""
        self.setButtonText(QWizard.WizardButton.NextButton, "")
        self.setButtonEnabled(QWizard.WizardButton.NextButton, False)


class DischargePage(QWizardPage):
    """Discharge phase page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("🔋 Step 2: Discharge to 0%")
        self.setSubTitle("Unplug your laptop and let it discharge")

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING["lg"])

        # Status
        self.status_label = QLabel("⏳ Discharging... Please wait.")
        self.status_label.setStyleSheet(f"""
            font-size: {FONTS['size_medium']};
            font-weight: {FONTS['weight_semibold']};
            color: {COLORS['warning']};
        """)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                height: 20px;
                border-radius: {RADIUS['md']}px;
                background-color: {COLORS['gray_200']};
            }}
            QProgressBar::chunk {{
                border-radius: {RADIUS['md']}px;
                background-color: {COLORS['warning']};
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Instructions
        instructions = QLabel(
            "🔌 Unplug your laptop.\n"
            "⚡ The battery will discharge to 0%.\n"
            "⚠️ Do not use your laptop during this process."
        )
        instructions.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_600']};
            padding: {SPACING['md']}px;
            background-color: {COLORS['gray_100']};
            border-radius: {RADIUS['lg']}px;
        """)
        layout.addWidget(instructions)

        layout.addStretch()

    def update_status(self, progress: int, message: str) -> None:
        """Update status display."""
        # Progress goes from 100 down to 0
        display_progress = 100 - progress
        self.progress_bar.setValue(display_progress)
        self.status_label.setText(message)

    def initializePage(self) -> None:
        """Initialize the page."""
        self.setButtonText(QWizard.WizardButton.NextButton, "")
        self.setButtonEnabled(QWizard.WizardButton.NextButton, False)


class CompletePage(QWizardPage):
    """Completion page."""

    calibration_complete = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("✅ Calibration Complete!")
        self.setSubTitle("Battery calibration has been completed successfully")

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING["lg"])

        # Result
        self.result_label = QLabel("🎉 Calibration complete!")
        self.result_label.setStyleSheet(f"""
            font-size: {FONTS['size_large']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['success']};
        """)
        layout.addWidget(self.result_label)

        # Health score
        self.health_label = QLabel("Battery Health: --%")
        self.health_label.setStyleSheet(f"""
            font-size: {FONTS['size_xlarge']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['primary']};
            padding: {SPACING['lg']}px;
            background-color: {COLORS['primary_light']};
            border-radius: {RADIUS['lg']}px;
        """)
        self.health_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.health_label)

        # Tips
        tips = QLabel(
            "💡 Tips to maintain battery health:\n"
            "• Keep your battery between 20% and 80%\n"
            "• Avoid extreme temperatures\n"
            "• Calibrate every 3-6 months"
        )
        tips.setStyleSheet(f"""
            font-size: {FONTS['size_small']};
            color: {COLORS['gray_600']};
            padding: {SPACING['md']}px;
            background-color: {COLORS['gray_100']};
            border-radius: {RADIUS['lg']}px;
        """)
        layout.addWidget(tips)

        layout.addStretch()

    def set_health_score(self, health_score: int) -> None:
        """Set the health score."""
        self.health_label.setText(f"Battery Health: {health_score}%")

        # Color based on score
        if health_score >= 80:
            color = COLORS["success"]
        elif health_score >= 60:
            color = COLORS["warning"]
        else:
            color = COLORS["danger"]

        self.health_label.setStyleSheet(f"""
            font-size: {FONTS['size_xlarge']};
            font-weight: {FONTS['weight_bold']};
            color: {color};
            padding: {SPACING['lg']}px;
            background-color: {COLORS['gray_100']};
            border-radius: {RADIUS['lg']}px;
        """)

    def initializePage(self) -> None:
        """Initialize the page."""
        self.setButtonText(QWizard.WizardButton.NextButton, "Finish")
        self.setButtonEnabled(QWizard.WizardButton.NextButton, True)
        self.setButtonText(QWizard.WizardButton.CancelButton, "Close")