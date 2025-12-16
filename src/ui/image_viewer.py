"""Image viewer widget with drag-and-drop support."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
from PIL import Image
import numpy as np
from pathlib import Path


class ImageViewer(QWidget):
    """Image viewer with optional drag-drop support and A/B toggle."""

    image_loaded = pyqtSignal()
    ab_toggled = pyqtSignal(bool)  # True = showing clean, False = showing affected

    def __init__(self, title: str = "IMAGE", accept_drops: bool = False, show_ab_toggle: bool = False):
        super().__init__()
        self._image: Image.Image | None = None
        self._accept_drops = accept_drops
        self._show_ab_toggle = show_ab_toggle
        self._is_clean = False

        self._setup_ui(title)

        if accept_drops:
            self.setAcceptDrops(True)

    def _setup_ui(self, title: str):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title row with optional A/B toggle
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_row.addWidget(title_label)

        if self._show_ab_toggle:
            title_row.addStretch()

            # Effects preview toggle
            self.effects_toggle = QCheckBox("Effects")
            self.effects_toggle.setObjectName("effectsToggle")
            self.effects_toggle.setChecked(True)  # Start with effects ON
            self.effects_toggle.setEnabled(False)
            self.effects_toggle.toggled.connect(self._on_effects_toggled)
            self.effects_toggle.setToolTip("Toggle between effects and clean preview")
            title_row.addWidget(self.effects_toggle)

        layout.addLayout(title_row)

        # Image display label
        self.image_label = QLabel()
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.image_label.setMinimumSize(200, 200)

        if self._accept_drops:
            self.image_label.setText("Drop image here\nor click to browse")
            self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.image_label.mousePressEvent = self._on_click
        else:
            self.image_label.setText("Output will appear here")

        layout.addWidget(self.image_label)

    def _on_click(self, event):
        """Handle click to open file dialog."""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
        )

        if file_path:
            self.load_image(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                path = Path(urls[0].toLocalFile())
                if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop."""
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.load_image(urls[0].toLocalFile())
            event.acceptProposedAction()

    def load_image(self, path: str):
        """Load an image from file path."""
        try:
            self._image = Image.open(path).convert("RGB")
            self._display_image(self._image)
            self.image_loaded.emit()
        except Exception as e:
            print(f"Failed to load image: {e}")

    def set_image(self, image: Image.Image):
        """Set the image directly from a PIL Image."""
        self._image = image.convert("RGB") if image.mode != "RGB" else image
        self._display_image(self._image)

    def get_image(self) -> Image.Image | None:
        """Get the current image."""
        return self._image

    def _display_image(self, image: Image.Image):
        """Display a PIL image in the label."""
        # Convert PIL Image to QPixmap
        data = np.array(image)
        height, width, channels = data.shape
        bytes_per_line = channels * width

        qimage = QImage(
            data.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qimage)

        # Scale to fit while maintaining aspect ratio
        label_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)

    def _on_effects_toggled(self, effects_on: bool):
        """Handle effects toggle checkbox change."""
        # When effects checkbox is ON, we're NOT showing clean (effects visible)
        # When effects checkbox is OFF, we ARE showing clean
        self._is_clean = not effects_on
        self.ab_toggled.emit(self._is_clean)

    def enable_ab_toggle(self, enabled: bool):
        """Enable or disable the effects toggle."""
        if self._show_ab_toggle:
            self.effects_toggle.setEnabled(enabled)

    def fit_to_window(self):
        """Trigger image to fit to current window size."""
        if self._image is not None:
            self._display_image(self._image)

    def resizeEvent(self, event):
        """Handle resize to rescale image."""
        super().resizeEvent(event)
        if self._image is not None:
            self._display_image(self._image)
