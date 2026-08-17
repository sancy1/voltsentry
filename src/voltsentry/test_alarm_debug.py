"""
FILE: test_alarm_debug.py
PATH: voltsentry/test_alarm_debug.py
DESCRIPTION: Direct alarm test - forces alarm to debug sound and tray
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from voltsentry.core.logging_config import setup_logging
from voltsentry.services.alarm_manager import AlarmManager, AlarmType
from voltsentry.services.notification_manager import NotificationManager, Notification
from voltsentry.services.alarm_service import AlarmService
from voltsentry.core.types import BatteryReading, HealthSource
from voltsentry.ui.tray import TrayIcon
from voltsentry.ui.dashboard import DashboardWindow
from datetime import datetime

def main():
    print("=" * 60)
    print("🔧 ALARM DEBUG TEST")
    print("=" * 60)
    print()
    
    # Setup
    setup_logging(verbose=True)
    app = QApplication(sys.argv)
    
    print("1. Creating services...")
    
    # Create tray FIRST
    tray = TrayIcon()
    tray.show_tray()
    print("   ✅ Tray created")
    
    # Create alarm service
    alarm_service = AlarmService()
    print("   ✅ AlarmService created")
    
    # Create dashboard
    dashboard = DashboardWindow(alarm_service=alarm_service)
    print("   ✅ Dashboard created")
    
    # Connect tray to alarm service
    alarm_service.set_tray(tray)
    print("   ✅ Tray connected to AlarmService")
    
    # Show dashboard
    dashboard.show_event()
    print("   ✅ Dashboard shown")
    
    print()
    print("2. Testing audio directly...")
    print()
    
    # Test 1: Test alarm manager directly
    print("🔊 TEST 1: Direct AlarmManager.play()")
    alarm_manager = AlarmManager(volume=1.0)
    result = alarm_manager.play(AlarmType.FULL_CHARGE)
    print(f"   Result: {result}")
    print(f"   Is playing: {alarm_manager.is_playing}")
    print(f"   Audio OK: {alarm_manager.is_audio_available()}")
    print(f"   Active alarm: {alarm_manager.active_alarm}")
    
    # Wait 2 seconds
    import time
    time.sleep(2)
    alarm_manager.stop()
    print()
    
    # Test 2: Test notification directly
    print("🔔 TEST 2: Direct Notification")
    notification = Notification(
        title="🔋 Test Notification",
        message="This is a direct test notification",
        duration=5
    )
    notification_manager = NotificationManager()
    notification_manager.notify(notification)
    
    # Show tray popup directly
    tray.show_notification("🔋 Direct Tray Test", "This is a direct tray popup!", urgency="critical")
    print("   ✅ Tray popup sent")
    print()
    
    # Test 3: Force alarm via alarm service
    print("🔔 TEST 3: Force Alarm via AlarmService")
    reading = BatteryReading(
        timestamp=datetime.now(),
        percent=85,
        is_charging=True,
        power_draw_watts=12.5,
        source=HealthSource.OS_REPORT
    )
    
    print(f"   Reading: {reading.percent}%, charging={reading.is_charging}")
    alarm_service.process_reading(reading)
    print("   ✅ Alarm processing triggered")
    
    # Get status
    status = alarm_service.get_status()
    print(f"   Alarm state: {status['state']['current_state']}")
    print(f"   Alarm playing: {status['alarm']['is_playing']}")
    print(f"   Audio OK: {status['alarm']['audio_ok']}")
    print()
    
    print("=" * 60)
    print("✅ Debug test complete!")
    print("📊 Check:")
    print("   1. Did you hear a sound? (Test 1)")
    print("   2. Did you see a tray popup? (Test 2)")
    print("   3. Did the alarm trigger? (Test 3)")
    print("=" * 60)
    
    # Keep running so user can see results
    QTimer.singleShot(10000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()