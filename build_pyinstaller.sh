#!/bin/bash
# Alternative build script using PyInstaller

set -e

echo "=== Building ScanScratch with PyInstaller ==="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Install PyInstaller if needed
echo "Checking for PyInstaller..."
pip3 install pyinstaller 2>/dev/null || echo "PyInstaller already installed"

# Build the app
echo "Building app bundle..."
pyinstaller --name "ScanScratch" \
    --windowed \
    --onedir \
    --clean \
    --noconfirm \
    --osx-bundle-identifier "com.scanscratch.app" \
    --hidden-import sounddevice \
    --hidden-import soundfile \
    --hidden-import scipy.special.cython_special \
    --collect-all pysstv \
    --exclude-module IPython \
    --exclude-module matplotlib \
    --exclude-module pandas \
    --exclude-module torch \
    --exclude-module tensorflow \
    --exclude-module transformers \
    --exclude-module nltk \
    --exclude-module jedi \
    --exclude-module zmq \
    --exclude-module pygments \
    --exclude-module moviepy \
    --exclude-module imageio \
    --exclude-module cv2 \
    --exclude-module skimage \
    --exclude-module lxml \
    --exclude-module pyarrow \
    --exclude-module tkinter \
    --exclude-module _tkinter \
    main.py

echo ""
echo "=== Build Complete ==="
echo "Your app is in: dist/ScanScratch.app"
echo ""
echo "To test: open dist/ScanScratch.app"
echo "To create DMG: hdiutil create -volname ScanScratch -srcfolder dist/ScanScratch.app -ov -format UDZO dist/ScanScratch.dmg"
