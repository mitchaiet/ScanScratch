@echo off
REM Build script for ScanScratch Windows app

echo === Building ScanScratch Windows App ===

REM Clean previous builds
echo Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Generate icon if it doesn't exist
if not exist "assets\icon.ico" (
    echo Generating app icon...
    python generate_icon.py
)

REM Install PyInstaller if needed
echo Checking for PyInstaller...
pip install pyinstaller

REM Build the app using spec file
echo Building app...
pyinstaller ScanScratch-windows.spec --noconfirm

echo.
echo === Build Complete ===
echo Your app is in: dist\ScanScratch\
echo.
echo To test: dist\ScanScratch\ScanScratch.exe
echo.
pause
