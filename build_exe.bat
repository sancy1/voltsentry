@echo off
echo ============================================
echo  Building VoltSentry Standalone .exe
echo ============================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Install PyInstaller if not installed
pip install pyinstaller

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo.
echo Building VoltSentry.exe (single file)...
echo.

pyinstaller --noconfirm --onefile --windowed ^
    --icon="src/voltsentry/assets/icon.ico" ^
    --add-data "src/voltsentry/assets;assets" ^
    --add-data "src/voltsentry/resources;resources" ^
    --name "VoltSentry" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "sqlalchemy" ^
    --hidden-import "alembic" ^
    --hidden-import "psutil" ^
    --hidden-import "pygame" ^
    --hidden-import "cryptography" ^
    --hidden-import "requests" ^
    --hidden-import "matplotlib" ^
    --hidden-import "matplotlib.backends.backend_qt5agg" ^
    --hidden-import "winrt.windows.ui.notifications" ^
    --collect-all "PyQt6" ^
    --collect-all "matplotlib" ^
    --collect-all "sqlalchemy" ^
    --version-file "version_info.txt" ^
    src/voltsentry/app.py

echo.
echo ============================================
echo  Build complete!
echo  Output: dist\VoltSentry.exe
echo ============================================
pause