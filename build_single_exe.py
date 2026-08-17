"""
FILE: build_single_exe.py
PATH: voltsentry/build_single_exe.py
DESCRIPTION: PyInstaller build script using run.py as entry point
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def clean_build():
    """Clean previous build artifacts to avoid conflicts."""
    for folder in ["dist", "build", "__pycache__"]:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"✅ Cleaned: {folder}")


def build_exe():
    """Build the single .exe file using run.py as entry point."""
    print("=" * 60)
    print("  Building VoltSentry Single .exe")
    print("=" * 60)
    print()
    
    # Clean
    clean_build()
    
    project_root = Path(__file__).parent.resolve()
    
    # Check required files
    entry_stub = project_root / "run.py"
    if not entry_stub.exists():
        print(f"❌ Error: run.py not found at {entry_stub}")
        print("   Please create run.py in the project root")
        return False
    
    icon_path = project_root / "src" / "voltsentry" / "assets" / "icon.ico"
    if not icon_path.exists():
        print(f"❌ Error: Icon not found at {icon_path}")
        return False
    
    assets_dir = project_root / "src" / "voltsentry" / "assets"
    resources_dir = project_root / "src" / "voltsentry" / "resources"
    version_file = project_root / "version_info.txt"
    
    print("📦 Building VoltSentry.exe...")
    print(f"   Entry point: {entry_stub}")
    print(f"   Icon: {icon_path}")
    print()
    
    # ============================================================
    # PYINSTALLER COMMAND - Uses run.py as entry point
    # ============================================================
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f'--name="VoltSentry"',
        f'--icon="{icon_path}"',
        f'--add-data="{assets_dir};assets"',
        f'--add-data="{resources_dir};resources"',
        f'--paths="{project_root / "src"}"',
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=sqlalchemy",
        "--hidden-import=alembic",
        "--hidden-import=psutil",
        "--hidden-import=pygame",
        "--hidden-import=cryptography",
        "--hidden-import=requests",
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_qt5agg",
        "--hidden-import=winrt.windows.ui.notifications",
    ]
    
    if version_file.exists():
        cmd.append(f'--version-file="{version_file}"')
    
    cmd.append(str(entry_stub))
    
    print("   Running PyInstaller...")
    print("   This may take 3-8 minutes...")
    print()
    
    # Run PyInstaller
    result = subprocess.run(" ".join(cmd), shell=True, cwd=project_root)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        return False
    
    # Check output
    exe_path = project_root / "dist" / "VoltSentry.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print()
        print("=" * 60)
        print(f"✅ Build successful!")
        print(f"   File: {exe_path}")
        print(f"   Size: {size_mb:.1f} MB")
        print("=" * 60)
        return True
    else:
        print("❌ Build failed - .exe not found")
        return False


if __name__ == "__main__":
    # Check virtual environment
    if not os.environ.get("VIRTUAL_ENV"):
        print("⚠️  Virtual environment not detected.")
        print("   Please activate it first:")
        print("   venv\\Scripts\\activate")
        sys.exit(1)
    
    success = build_exe()
    sys.exit(0 if success else 1)