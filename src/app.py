"""Main application setup."""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from .ui import MainWindow
from .ui.styles import STYLESHEET


def create_app() -> QApplication:
    """Create and configure the application."""
    app = QApplication([])
    app.setApplicationName("ScanScratch")
    app.setApplicationDisplayName("ScanScratch - SSTV Glitch Editor")

    # Apply stylesheet
    app.setStyleSheet(STYLESHEET)

    # Create and show main window
    # Store reference on app to prevent garbage collection
    app.main_window = MainWindow()
    app.main_window.show()

    return app
