"""
FILE: test_simple.py
PATH: voltsentry/test_simple.py
DESCRIPTION: Simple test to verify UI shows up
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from voltsentry.core.logging_config import setup_logging
from voltsentry.services.alarm_service import AlarmService
from voltsentry.services.battery_poller import BatteryPoller
from voltsentry.services.heartbeat import get_heartbeat_service
from voltsentry.ui.dashboard import DashboardWindow
from voltsentry.ui.tray import TrayIcon


def main():
    """Simple test to verify UI works."""
    print("=" * 60)
    print("🔋 VoltSentry - Simple UI Test")
    print("=" * 60)
    print()
    print("Starting application...")

    # Setup logging
    setup_logging(verbose=True)

    # Create app
    app = QApplication(sys.argv)
    app.setApplicationName("VoltSentry")

    print("✅ QApplication created")

    # Create services
    print("Creating services...")
    poller = BatteryPoller()
    alarm_service = AlarmService()
    heartbeat = get_heartbeat_service()

    print("✅ Services created")

    # Create UI
    print("Creating UI...")
    dashboard = DashboardWindow(poller=poller, alarm_service=alarm_service)
    tray = TrayIcon()

    print("✅ UI created")

    # Connect poller to UI
    print("Connecting signals...")
    poller.reading_updated.connect(dashboard._on_reading_updated)
    poller.reading_updated.connect(
        lambda r: tray.update_battery(r.percent, r.is_charging)
    )
    poller.state_changed.connect(dashboard._on_state_changed)
    poller.error_occurred.connect(dashboard._on_poller_error)

    # Connect tray signals
    tray.dashboard_requested.connect(dashboard.show_event)
    tray.settings_requested.connect(
        lambda: dashboard._tab_widget.setCurrentIndex(0)
    )
    tray.exit_requested.connect(app.quit)

    print("✅ Signals connected")

    # Start poller
    print("Starting poller...")
    poller.start()
    heartbeat.beat()
    print("✅ Poller started")

    # Show UI
    print("Showing UI...")
    tray.show_tray()
    dashboard.show_event()
    print("✅ UI should be visible now")

    # Heartbeat timer
    timer = QTimer()
    timer.timeout.connect(heartbeat.beat)
    timer.start(5000)

    print()
    print("=" * 60)
    print("🔔 UI should be visible on screen")
    print("📊 Dashboard should show battery data")
    print("🔔 Tray icon should appear in system tray")
    print()
    print("Press Ctrl+C or close window to exit")
    print("=" * 60)

    # Run
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down...")
        app.quit()


if __name__ == "__main__":
    main()