# """
# FILE: src/voltsentry/utils/path_utils.py
# PATH: voltsentry/src/voltsentry/utils/path_utils.py
# DESCRIPTION: Dynamic resource path utilities for packaging
# PHASE: 6 - Packaging & Deployment
# """

# import sys
# from pathlib import Path


# def get_resource_path(relative_path: str) -> Path:
#     """
#     Get the absolute path to a resource.
#     Works for normal development AND PyInstaller bundled executables.
    
#     Args:
#         relative_path: Relative path from the src/voltsentry/ folder
    
#     Returns:
#         Absolute path to the resource
        
#     Example:
#         icon_path = get_resource_path("assets/icon.png")
#     """
#     if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
#         # Running as a compiled PyInstaller executable
#         base_path = Path(sys._MEIPASS)
#     else:
#         # Running in normal Python development environment
#         # Path relative to this file's directory (src/voltsentry/utils/)
#         base_path = Path(__file__).parent.parent
    
#     return base_path / relative_path


















































"""
FILE: src/voltsentry/utils/path_utils.py
PATH: voltsentry/src/voltsentry/utils/path_utils.py
DESCRIPTION: Dynamic resource path utilities for packaging
PHASE: 6 - Packaging & Deployment
"""

import sys
import os
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource.
    Works for normal development AND PyInstaller bundled executables.
    
    For --onefile builds: uses sys._MEIPASS (temp extraction folder)
    For --onedir builds: uses the folder containing the .exe
    For development: uses the source folder
    
    Args:
        relative_path: Relative path from the base folder
    
    Returns:
        Absolute path to the resource
        
    Example:
        icon_path = get_resource_path("assets/icon.png")
    """
    if getattr(sys, 'frozen', False):
        # Running as a compiled PyInstaller executable
        if hasattr(sys, '_MEIPASS'):
            # --onefile mode: extracted to temp folder
            base_path = Path(sys._MEIPASS)
        else:
            # --onedir mode: same folder as executable
            base_path = Path(sys.executable).parent
    else:
        # Running in normal Python development environment
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path


def get_app_data_dir() -> Path:
    """
    Get the application data directory for user-specific files.
    
    Returns:
        Path to app data folder (e.g., %APPDATA%\VoltSentry)
    """
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    
    app_data = base / "VoltSentry"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs = get_app_data_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs