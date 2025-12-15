#!/bin/bash
# Build script for ScanScratch Mac app

set -e

echo "=== Building ScanScratch Mac App ==="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Install py2app if needed
echo "Checking for py2app..."
pip3 install py2app 2>/dev/null || echo "py2app already installed"

# Build the app
echo "Building app bundle..."
python3 setup.py py2app

echo ""
echo "=== Build Complete ==="
echo "Your app is in: dist/ScanScratch.app"
echo ""
echo "To test: open dist/ScanScratch.app"
echo "To create DMG: hdiutil create -volname ScanScratch -srcfolder dist/ScanScratch.app -ov -format UDZO dist/ScanScratch.dmg"
