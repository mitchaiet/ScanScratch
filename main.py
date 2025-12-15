#!/usr/bin/env python3
"""ScanScratch - SSTV Glitch Editor"""

import sys
from src.app import create_app

if __name__ == "__main__":
    app = create_app()
    sys.exit(app.exec())
