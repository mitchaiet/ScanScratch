"""Export dialog for saving SSTV output images and videos."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSlider,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PIL import Image
import os
from pathlib import Path


class ExportDialog(QDialog):
    """Simple export dialog for SSTV images at native resolution."""

    def __init__(self, output_image: Image.Image, parent=None):
        super().__init__(parent)
        self.output_image = output_image
        self.export_path = None

        self.setWindowTitle("Export SSTV Image")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Image info
        info_group = QGroupBox("SSTV Image Information")
        info_layout = QVBoxLayout(info_group)

        if self.output_image:
            width, height = self.output_image.size
            mode = self.output_image.mode
            info_layout.addWidget(QLabel(f"Resolution: {width} × {height} px (native SSTV)"))
            info_layout.addWidget(QLabel(f"Color Mode: {mode}"))

        layout.addWidget(info_group)

        # Format settings
        format_group = QGroupBox("Export Settings")
        format_layout = QVBoxLayout(format_group)

        # Format selector
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "TIFF", "WebP", "BMP"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_row.addWidget(self.format_combo, stretch=1)
        format_layout.addLayout(format_row)

        # Quality slider (for JPEG/WebP)
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality:"))
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        self.quality_slider.valueChanged.connect(self._update_quality_label)
        quality_row.addWidget(self.quality_slider, stretch=1)
        self.quality_label = QLabel("95")
        self.quality_label.setFixedWidth(40)
        self.quality_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        quality_row.addWidget(self.quality_label)
        format_layout.addLayout(quality_row)
        self.quality_row_widgets = [quality_row.itemAt(i).widget() for i in range(quality_row.count())]

        layout.addWidget(format_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        export_btn = QPushButton("Export Image")
        export_btn.setDefault(True)
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        # Set defaults
        self._on_format_changed("PNG")

    def _on_format_changed(self, format_name):
        """Update UI based on selected format."""
        # Show quality slider only for JPEG and WebP
        show_quality = format_name in ["JPEG", "WebP"]
        for widget in self.quality_row_widgets:
            if widget:
                widget.setVisible(show_quality)

    def _update_quality_label(self, value):
        """Update quality label."""
        self.quality_label.setText(str(value))

    def _on_export(self):
        """Handle export button click."""
        if not self.output_image:
            QMessageBox.warning(self, "No Image", "No image to export.")
            return

        # Get format
        format_name = self.format_combo.currentText()
        ext = format_name.lower()
        if ext == "jpeg":
            ext = "jpg"

        # Show save dialog
        default_name = f"sstv_output.{ext}"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export SSTV Image",
            str(Path.home() / default_name),
            f"{format_name} Files (*.{ext});;All Files (*.*)",
        )

        if not file_path:
            return

        # Add extension if missing
        if not file_path.lower().endswith(f".{ext}"):
            file_path += f".{ext}"

        # Save image at native resolution
        try:
            if format_name in ["JPEG", "WebP"]:
                quality = self.quality_slider.value()
                self.output_image.save(file_path, format=format_name, quality=quality, optimize=True)
            else:
                self.output_image.save(file_path, format=format_name)

            self.export_path = file_path
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export image:\n{str(e)}")
