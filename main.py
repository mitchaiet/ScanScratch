#!/usr/bin/env python3
"""ScanScratch - SSTV Glitch Editor"""

import sys

# Pre-import scipy modules to avoid lazy loading issues with PyInstaller
# This must happen before any other imports that might trigger scipy
try:
    # Import the specific scipy submodules we need directly
    # This bypasses the problematic scipy.stats import chain
    import scipy.signal
    import scipy.ndimage
    import scipy.fft
except Exception:
    pass

from src.app import create_app

if __name__ == "__main__":
    app = create_app()
    sys.exit(app.exec())
