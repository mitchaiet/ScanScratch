# Building ScanScratch as a Mac App

## Quick Start

### Option 1: py2app (Recommended for Mac)
```bash
./build_mac_app.sh
```

### Option 2: PyInstaller (Cross-platform)
```bash
./build_pyinstaller.sh
```

Both will create `dist/ScanScratch.app` that you can double-click to run.

## Distribution

### Create a DMG for sharing:
```bash
hdiutil create -volname ScanScratch -srcfolder dist/ScanScratch.app -ov -format UDZO dist/ScanScratch.dmg
```

This creates a compressed disk image that users can download and drag to Applications.

## Adding an App Icon (Optional)

1. Create a 1024×1024 PNG icon
2. Convert to .icns format:
   ```bash
   # Using iconutil (built into macOS)
   mkdir icon.iconset
   sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
   sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
   sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
   sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
   sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
   sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
   sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
   sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
   sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
   sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
   iconutil -c icns icon.iconset
   rm -rf icon.iconset
   ```

3. Place `icon.icns` in the project root
4. Rebuild the app

## Code Signing & Notarization (For Public Distribution)

If you want to distribute outside of App Store:

1. **Get an Apple Developer account** ($99/year)

2. **Sign the app:**
   ```bash
   codesign --deep --force --sign "Developer ID Application: Your Name" dist/ScanScratch.app
   ```

3. **Notarize with Apple:**
   ```bash
   # Create a zip
   ditto -c -k --keepParent dist/ScanScratch.app ScanScratch.zip

   # Submit for notarization
   xcrun notarytool submit ScanScratch.zip \
     --apple-id your@email.com \
     --team-id TEAMID \
     --password app-specific-password \
     --wait

   # Staple the ticket
   xcrun stapler staple dist/ScanScratch.app
   ```

Without code signing, users will see "unidentified developer" warnings (but can still open via right-click → Open).

## Testing the App

```bash
# Run the built app
open dist/ScanScratch.app

# Check for issues
/usr/bin/codesign --verify --verbose dist/ScanScratch.app
```

## Troubleshooting

### "App is damaged and can't be opened"
This happens with unsigned apps on recent macOS. Users can fix with:
```bash
xattr -cr /path/to/ScanScratch.app
```

### Missing dependencies
If the app crashes, check Console.app for errors. You may need to add hidden imports:
- For py2app: Add to `packages` list in setup.py
- For PyInstaller: Add `--hidden-import module_name` to build script

### Large app size
Both bundlers include the entire Python runtime. Typical size: 100-200MB. This is normal for Python apps.

## Comparison

**py2app:**
- ✅ More Mac-native
- ✅ Better .app bundle structure
- ✅ Smaller file size
- ❌ Mac only

**PyInstaller:**
- ✅ Cross-platform (can build for Windows/Linux too)
- ✅ More actively maintained
- ✅ Better documentation
- ❌ Slightly larger bundles

Both work great for ScanScratch. Try py2app first, fall back to PyInstaller if you have issues.
