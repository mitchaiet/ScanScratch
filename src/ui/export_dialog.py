"""Export dialog for saving output images."""

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
    QCheckBox,
    QLineEdit,
)
from PyQt6.QtCore import Qt
from PIL import Image
import os


class ExportDialog(QDialog):
    """Dialog for exporting output images with format and quality options."""

    def __init__(self, output_image: Image.Image, parent=None):
        super().__init__(parent)
        self.output_image = output_image
        self.export_path = None

        self.setWindowTitle("Export Image")
        self.setModal(True)
        self.setMinimumWidth(450)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # File settings
        file_group = QGroupBox("File Settings")
        file_layout = QVBoxLayout(file_group)

        # Format selector
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "TIFF", "WebP", "BMP"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_row.addWidget(self.format_combo, stretch=1)
        file_layout.addLayout(format_row)

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
        file_layout.addLayout(quality_row)
        self.quality_row_widgets = [quality_row.itemAt(i).widget() for i in range(quality_row.count())]

        layout.addWidget(file_group)

        # Image info
        info_group = QGroupBox("Image Information")
        info_layout = QVBoxLayout(info_group)

        if self.output_image:
            width, height = self.output_image.size
            mode = self.output_image.mode
            info_layout.addWidget(QLabel(f"Dimensions: {width} × {height} px"))
            info_layout.addWidget(QLabel(f"Color Mode: {mode}"))

        layout.addWidget(info_group)

        # Options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)

        self.optimize_check = QCheckBox("Optimize file size")
        self.optimize_check.setChecked(True)
        options_layout.addWidget(self.optimize_check)

        self.metadata_check = QCheckBox("Preserve metadata")
        self.metadata_check.setChecked(False)
        options_layout.addWidget(self.metadata_check)

        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        export_btn = QPushButton("Export")
        export_btn.setObjectName("transmitButton")
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        self._on_format_changed("PNG")

    def _on_format_changed(self, format_name: str):
        """Update UI based on selected format."""
        # Show quality slider only for JPEG and WebP
        show_quality = format_name in ["JPEG", "WebP"]
        for widget in self.quality_row_widgets:
            if widget:
                widget.setVisible(show_quality)

    def _update_quality_label(self, value: int):
        """Update quality label."""
        self.quality_label.setText(str(value))

    def _on_export(self):
        """Show save dialog and export the image."""
        if not self.output_image:
            return

        format_name = self.format_combo.currentText()

        # Map format to extension
        ext_map = {
            "PNG": ".png",
            "JPEG": ".jpg",
            "TIFF": ".tif",
            "WebP": ".webp",
            "BMP": ".bmp",
        }

        default_ext = ext_map.get(format_name, ".png")
        filter_str = f"{format_name} Files (*{default_ext})"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            f"untitled{default_ext}",
            filter_str
        )

        if file_path:
            self._save_image(file_path, format_name)
            self.export_path = file_path
            self.accept()

    def _save_image(self, file_path: str, format_name: str):
        """Save the image with the specified settings."""
        # Prepare save options
        save_kwargs = {}

        if format_name == "JPEG":
            # Convert to RGB if needed (JPEG doesn't support transparency)
            img = self.output_image
            if img.mode in ("RGBA", "LA", "P"):
                # Create white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = background

            save_kwargs["quality"] = self.quality_slider.value()
            save_kwargs["optimize"] = self.optimize_check.isChecked()
            img.save(file_path, format_name, **save_kwargs)

        elif format_name == "WebP":
            save_kwargs["quality"] = self.quality_slider.value()
            save_kwargs["method"] = 6 if self.optimize_check.isChecked() else 4
            self.output_image.save(file_path, format_name, **save_kwargs)

        elif format_name == "PNG":
            save_kwargs["optimize"] = self.optimize_check.isChecked()
            self.output_image.save(file_path, format_name, **save_kwargs)

        else:
            # TIFF, BMP
            self.output_image.save(file_path, format_name, **save_kwargs)

    def get_export_path(self) -> str:
        """Get the path where the image was exported."""
        return self.export_path
