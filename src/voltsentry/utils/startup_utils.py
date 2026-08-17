"""
FILE: src/voltsentry/utils/startup_utils.py
PATH: voltsentry/src/voltsentry/utils/startup_utils.py
DESCRIPTION: Windows Registry auto-start manager for VoltSentry
"""

import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None

REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VoltSentry"


def get_current_exe_path() -> str:
    """
    Returns the path to the running executable.
    Works for both development and packaged .exe.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled PyInstaller .exe
        return f'"{sys.executable}"'
    else:
        # Running in development mode - point to run.py
        entry_point = Path(__file__).parent.parent.parent.parent / "run.py"
        return f'"{sys.executable}" "{entry_point}"'


def set_auto_start(enable: bool) -> bool:
    """
    Add or remove VoltSentry from Windows startup via Registry.
    
    Args:
        enable: True to enable, False to disable
    
    Returns:
        True if successful, False otherwise
    """
    if winreg is None:
        return False

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_SUBKEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        
        if enable:
            exe_path = get_current_exe_path()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            print(f"[✓] Added startup registry entry: {exe_path}")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                print("[✓] Removed startup registry entry.")
            except FileNotFoundError:
                pass
        
        winreg.CloseKey(key)
        return True
        
    except PermissionError:
        print("[!] Permission denied - run as Administrator")
        return False
    except Exception as e:
        print(f"[!] Startup registry error: {e}")
        return False


def is_auto_start_enabled() -> bool:
    """
    Check if VoltSentry is configured to launch on Windows boot.
    
    Returns:
        True if enabled, False otherwise
    """
    if winreg is None:
        return False

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_SUBKEY,
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False