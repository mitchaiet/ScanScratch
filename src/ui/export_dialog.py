"""Export dialog for saving SSTV output images as PNG."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QMessageBox,
    QComboBox,
)
from PIL import Image
from pathlib import Path


class ExportDialog(QDialog):
    """Simple export dialog for SSTV images - PNG only with optional upscaling."""

    def __init__(self, output_image: Image.Image, parent=None):
        super().__init__(parent)
        self.output_image = output_image
        self.export_path = None

        self.setWindowTitle("Export PNG")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Image info
        info_group = QGroupBox("SSTV Image")
        info_layout = QVBoxLayout(info_group)

        if self.output_image:
            width, height = self.output_image.size
            info_layout.addWidget(QLabel(f"Native Resolution: {width} × {height} px"))
            info_layout.addWidget(QLabel(f"Format: PNG (lossless)"))

        layout.addWidget(info_group)

        # Scale options
        scale_group = QGroupBox("Export Size")
        scale_layout = QVBoxLayout(scale_group)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        if self.output_image:
            width, height = self.output_image.size
            self.scale_combo.addItem(f"1× ({width} × {height} px)", 1)
            self.scale_combo.addItem(f"2× ({width*2} × {height*2} px)", 2)
            self.scale_combo.addItem(f"4× ({width*4} × {height*4} px)", 4)
        self.scale_combo.setCurrentIndex(0)
        scale_row.addWidget(self.scale_combo, stretch=1)
        scale_layout.addLayout(scale_row)

        layout.addWidget(scale_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        export_btn = QPushButton("Export PNG")
        export_btn.setDefault(True)
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

    def _on_export(self):
        """Handle export button click."""
        if not self.output_image:
            QMessageBox.warning(self, "No Image", "No image to export.")
            return

        # Get scale factor
        scale = self.scale_combo.currentData()

        # Show save dialog
        default_name = "sstv_output.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PNG",
            str(Path.home() / default_name),
            "PNG Files (*.png);;All Files (*.*)",
        )

        if not file_path:
            return

        # Add extension if missing
        if not file_path.lower().endswith('.png'):
            file_path += '.png'

        # Save as PNG with optional upscaling
        try:
            if scale > 1:
                # Upscale using nearest-neighbor (preserves pixel art look)
                width, height = self.output_image.size
                scaled_image = self.output_image.resize(
                    (width * scale, height * scale),
                    Image.Resampling.NEAREST
                )
                scaled_image.save(file_path, format='PNG')
            else:
                # Save at native resolution
                self.output_image.save(file_path, format='PNG')

            self.export_path = file_path
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PNG:\n{str(e)}")
