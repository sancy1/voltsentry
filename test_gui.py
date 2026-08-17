"""
FILE: test_gui.py
DESCRIPTION: Quick test script to launch VoltSentry GUI
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtWidgets import QApplication

from voltsentry.core.logging_config import setup_logging
from voltsentry.ui.dashboard import DashboardWindow


def main():
    # Setup logging
    setup_logging(verbose=True)

    # Create app
    app = QApplication(sys.argv)
    app.setApplicationName("VoltSentry")

    # Create and show dashboard
    window = DashboardWindow()
    window.show()

    print("✅ VoltSentry GUI is running!")
    print("📊 Dashboard should be visible on screen")
    print("Press Ctrl+C or close window to exit")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()