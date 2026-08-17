"""
FILE: test_sound_debug.py
PATH: voltsentry/test_sound_debug.py
DESCRIPTION: Dedicated sound debugging - test each method individually
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pathlib import Path
from voltsentry.core.constants import FULL_CHARGE_SOUND, LOW_BATTERY_SOUND

print("=" * 60)
print("🔊 SOUND DEBUG TEST")
print("=" * 60)
print()

# ============================================================
# 1. CHECK FILES EXIST
# ============================================================
print("1. CHECKING SOUND FILES...")
print(f"   Full charge sound: {FULL_CHARGE_SOUND}")
print(f"   Exists: {FULL_CHARGE_SOUND.exists()}")
print(f"   Size: {FULL_CHARGE_SOUND.stat().st_size if FULL_CHARGE_SOUND.exists() else 'N/A'} bytes")
print(f"   Extension: {FULL_CHARGE_SOUND.suffix}")
print()
print(f"   Low battery sound: {LOW_BATTERY_SOUND}")
print(f"   Exists: {LOW_BATTERY_SOUND.exists()}")
print(f"   Size: {LOW_BATTERY_SOUND.stat().st_size if LOW_BATTERY_SOUND.exists() else 'N/A'} bytes")
print(f"   Extension: {LOW_BATTERY_SOUND.suffix}")
print()

# ============================================================
# 2. TEST PYGAME DIRECTLY
# ============================================================
print("2. TESTING PYGAME...")

try:
    import pygame
    print("   ✅ Pygame imported successfully")
except ImportError as e:
    print(f"   ❌ Pygame import failed: {e}")
    sys.exit(1)

# Test mixer init
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    print("   ✅ Pygame mixer initialized")
except Exception as e:
    print(f"   ❌ Pygame mixer init failed: {e}")
    try:
        pygame.mixer.init()
        print("   ✅ Pygame mixer initialized (fallback mode)")
    except Exception as e2:
        print(f"   ❌ Pygame mixer fallback failed: {e2}")
        sys.exit(1)

print()

# ============================================================
# 3. TEST PLAYING EACH FILE
# ============================================================
def test_play_file(file_path: Path, description: str) -> bool:
    """Test playing a single file."""
    print(f"   Testing: {description}")
    print(f"      Path: {file_path}")
    print(f"      Exists: {file_path.exists()}")
    
    if not file_path.exists():
        print(f"      ❌ File not found")
        return False
    
    try:
        # Try loading
        print(f"      Loading file...")
        pygame.mixer.music.load(str(file_path))
        print(f"      ✅ Loaded successfully")
        
        # Try playing
        print(f"      Playing...")
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(loops=-1)
        
        # Check if playing
        import time
        time.sleep(0.5)
        if pygame.mixer.music.get_busy():
            print(f"      ✅ PLAYING! You should hear sound!")
            return True
        else:
            print(f"      ⚠️ Loaded but not playing")
            return False
            
    except pygame.error as e:
        print(f"      ❌ Pygame error: {e}")
        return False
    except Exception as e:
        print(f"      ❌ Unexpected error: {e}")
        return False

print("3. TESTING PLAYBACK...")
print()

full_result = test_play_file(FULL_CHARGE_SOUND, "Full Charge Sound")
print()
low_result = test_play_file(LOW_BATTERY_SOUND, "Low Battery Sound")
print()

# ============================================================
# 4. STOP AND CLEANUP
# ============================================================
print("4. CLEANUP...")
pygame.mixer.music.stop()
pygame.mixer.music.unload()
print("   ✅ Stopped all playback")
print()

# ============================================================
# 5. SUMMARY
# ============================================================
print("=" * 60)
print("📊 SUMMARY")
print("=" * 60)
print(f"   Full Charge Sound: {'✅ WORKING' if full_result else '❌ NOT WORKING'}")
print(f"   Low Battery Sound: {'✅ WORKING' if low_result else '❌ NOT WORKING'}")
print()

if not full_result and not low_result:
    print("🔍 POSSIBLE ISSUES:")
    print("   1. File format not supported (use MP3 or WAV)")
    print("   2. File is corrupted")
    print("   3. Audio device/driver issue")
    print("   4. File permissions")
    print()
    print("💡 TRY:")
    print("   - Convert file to standard MP3 (128kbps, 44.1kHz)")
    print("   - Or use WAV format (16-bit PCM)")
    print("   - Check Windows volume mixer")

print("=" * 60)