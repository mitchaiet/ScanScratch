#!/bin/bash
# Build script for ScanScratch Mac app using PyInstaller

set -e

echo "=== Building ScanScratch Mac App ==="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Patch scipy to fix PyInstaller compatibility issue
# scipy.stats._distn_infrastructure.py has a 'del obj' that fails when packaged
echo "Patching scipy for PyInstaller compatibility..."
SCIPY_FILE=$(python3 -c "import scipy.stats._distn_infrastructure as m; print(m.__file__)")
if [ -f "$SCIPY_FILE" ]; then
    # Backup if not already backed up
    if [ ! -f "${SCIPY_FILE}.backup" ]; then
        cp "$SCIPY_FILE" "${SCIPY_FILE}.backup"
    fi
    # Apply patch
    sed -i '' 's/^del obj$/# del obj  # Patched for PyInstaller/' "$SCIPY_FILE" 2>/dev/null || true
    echo "✓ scipy patched"
fi

# Generate icon if it doesn't exist
if [ ! -f "assets/icon.icns" ]; then
    echo "Generating app icon..."
    python3 generate_icon.py
    mkdir -p assets/icon.iconset
    cp assets/icon_16.png assets/icon.iconset/icon_16x16.png
    cp assets/icon_32.png assets/icon.iconset/icon_16x16@2x.png
    cp assets/icon_32.png assets/icon.iconset/icon_32x32.png
    cp assets/icon_64.png assets/icon.iconset/icon_32x32@2x.png
    cp assets/icon_128.png assets/icon.iconset/icon_128x128.png
    cp assets/icon_256.png assets/icon.iconset/icon_128x128@2x.png
    cp assets/icon_256.png assets/icon.iconset/icon_256x256.png
    cp assets/icon_512.png assets/icon.iconset/icon_256x256@2x.png
    cp assets/icon_512.png assets/icon.iconset/icon_512x512.png
    cp assets/icon_1024.png assets/icon.iconset/icon_512x512@2x.png
    iconutil -c icns assets/icon.iconset -o assets/icon.icns
fi

# Install PyInstaller if needed
echo "Checking for PyInstaller..."
pip3 install pyinstaller 2>/dev/null || echo "PyInstaller already installed"

# Build the app using spec file
echo "Building app bundle..."
pyinstaller ScanScratch.spec --noconfirm

echo ""
echo "=== Build Complete ==="
echo "Your app is in: dist/ScanScratch.app"
echo ""
echo "To test: open dist/ScanScratch.app"
echo ""

# Optionally create DMG
read -p "Create DMG? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating DMG..."
    mkdir -p dist/dmg
    cp -R dist/ScanScratch.app dist/dmg/
    ln -sf /Applications dist/dmg/Applications
    hdiutil create -volname "ScanScratch" -srcfolder dist/dmg -ov -format UDZO dist/ScanScratch.dmg
    rm -rf dist/dmg
    echo "DMG created: dist/ScanScratch.dmg"
fi
