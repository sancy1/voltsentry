"""
FILE: test_full_app.py
PATH: voltsentry/test_full_app.py
DESCRIPTION: Full application test script with live data
PHASE: 5 - Integration Testing

Run this to test the complete application with:
- Live battery data in Dashboard
- Live battery data in Tray icon
- Alarm notifications based on settings
- All services working together
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from voltsentry.app import create_app


def main():
    """Run the full application."""
    print("=" * 60)
    print("🔋 VoltSentry - Full Application Test")
    print("=" * 60)
    print()
    print("📊 Dashboard will show live battery data")
    print("🔔 Tray icon will update with battery status")
    print("⚡ Alarms will trigger based on your settings")
    print()
    print("💡 Commands:")
    print("  - Click tray icon → Open Dashboard")
    print("  - Right-click tray icon → Menu options")
    print("  - Close Dashboard → Minimizes to tray")
    print("  - Right-click tray → Exit to quit")
    print()
    print("=" * 60)
    print()

    # Create and run app
    app = create_app()
    if app is None:
        print("❌ Failed to start application")
        return 1

    print("✅ Application started successfully!")
    print("📊 Dashboard should open automatically")
    print("🔔 Tray icon should appear in system tray")
    print()
    print("Press Ctrl+C to exit")

    try:
        return app.run()
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down...")
        app.shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())