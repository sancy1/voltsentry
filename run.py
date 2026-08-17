"""
FILE: run.py
PATH: voltsentry/run.py
DESCRIPTION: Clean entry point stub for PyInstaller to fix relative import errors
"""

import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.resolve()
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import and run the app
from voltsentry.app import main

if __name__ == "__main__":
    main()