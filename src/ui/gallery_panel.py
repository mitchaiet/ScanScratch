"""Gallery panel showing thumbnails of saved outputs."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image
import numpy as np


class ThumbnailWidget(QWidget):
    """A single thumbnail in the gallery."""

    clicked = pyqtSignal(Path)

    def __init__(self, folder: Path, thumbnail_path: Path, mode: str, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui(thumbnail_path, mode)

    def _setup_ui(self, thumbnail_path: Path, mode: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(80, 80)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)

        # Load and display thumbnail
        if thumbnail_path.exists():
            pixmap = QPixmap(str(thumbnail_path))
            self.image_label.setPixmap(pixmap.scaled(
                76, 76,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        layout.addWidget(self.image_label)

        # Mode label
        mode_label = QLabel(mode[:8] if len(mode) > 8 else mode)
        mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(mode_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.folder)

    def enterEvent(self, event):
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border: 1px solid #5a8a5a;
                border-radius: 4px;
            }
        """)

    def leaveEvent(self, event):
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)


class GalleryPanel(QWidget):
    """Collapsible gallery panel showing saved outputs."""

    output_selected = pyqtSignal(Path)

    def __init__(self, output_manager, parent=None):
        super().__init__(parent)
        self.output_manager = output_manager
        self._collapsed = False
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with collapse toggle
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-top: 1px solid #333;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self.collapse_btn = QPushButton("\u25bc")  # Down arrow
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)

        title = QLabel("GALLERY")
        title.setStyleSheet("color: #888; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Output count
        self.count_label = QLabel("0 outputs")
        self.count_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(self.count_label)

        layout.addWidget(header)

        # Scroll area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(120)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: #1a1a1a;
            }
            QScrollBar::handle:horizontal {
                background: #444;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        # Container for thumbnails
        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QHBoxLayout(self.thumbnails_container)
        self.thumbnails_layout.setContentsMargins(8, 8, 8, 8)
        self.thumbnails_layout.setSpacing(8)
        self.thumbnails_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Placeholder for empty gallery
        self.empty_label = QLabel("No outputs yet. Transmit an image to get started!")
        self.empty_label.setStyleSheet("color: #555; font-style: italic;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnails_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.thumbnails_container)
        layout.addWidget(self.scroll_area)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self.scroll_area.setVisible(not self._collapsed)
        self.collapse_btn.setText("\u25b6" if self._collapsed else "\u25bc")  # Right or down arrow

    def refresh(self):
        """Reload thumbnails from outputs folder."""
        # Clear existing thumbnails
        while self.thumbnails_layout.count() > 0:
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get all outputs
        outputs = self.output_manager.get_all_outputs()

        if not outputs:
            self.empty_label = QLabel("No outputs yet. Transmit an image to get started!")
            self.empty_label.setStyleSheet("color: #555; font-style: italic;")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.thumbnails_layout.addWidget(self.empty_label)
            self.count_label.setText("0 outputs")
            return

        # Add thumbnails
        for output in outputs:
            thumb = ThumbnailWidget(
                output["folder"],
                output["thumbnail_path"],
                output["mode"]
            )
            thumb.clicked.connect(self.output_selected.emit)
            self.thumbnails_layout.addWidget(thumb)

        # Add stretch at end
        self.thumbnails_layout.addStretch()

        # Update count
        self.count_label.setText(f"{len(outputs)} output{'s' if len(outputs) != 1 else ''}")

    def add_output(self, folder: Path):
        """Add a new output to the gallery (at the beginning)."""
        # Get the output info
        outputs = self.output_manager.get_all_outputs()
        new_output = None
        for output in outputs:
            if output["folder"] == folder:
                new_output = output
                break

        if new_output is None:
            return

        # Remove empty label if present
        for i in range(self.thumbnails_layout.count()):
            item = self.thumbnails_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QLabel):
                if "No outputs" in item.widget().text():
                    item.widget().deleteLater()
                    break

        # Remove stretch at end
        for i in range(self.thumbnails_layout.count() - 1, -1, -1):
            item = self.thumbnails_layout.itemAt(i)
            if item.spacerItem():
                self.thumbnails_layout.takeAt(i)
                break

        # Add new thumbnail at the beginning
        thumb = ThumbnailWidget(
            new_output["folder"],
            new_output["thumbnail_path"],
            new_output["mode"]
        )
        thumb.clicked.connect(self.output_selected.emit)
        self.thumbnails_layout.insertWidget(0, thumb)

        # Add stretch at end
        self.thumbnails_layout.addStretch()

        # Update count
        count = sum(1 for i in range(self.thumbnails_layout.count())
                   if self.thumbnails_layout.itemAt(i).widget()
                   and isinstance(self.thumbnails_layout.itemAt(i).widget(), ThumbnailWidget))
        self.count_label.setText(f"{count} output{'s' if count != 1 else ''}")

        # Scroll to show new item
        self.scroll_area.horizontalScrollBar().setValue(0)
