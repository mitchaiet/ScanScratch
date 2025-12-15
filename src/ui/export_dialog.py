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
    QSpinBox,
)
from PyQt6.QtCore import Qt
from PIL import Image
import os
from pathlib import Path


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

        # Scaling options
        scale_group = QGroupBox("Resize/Scale")
        scale_layout = QVBoxLayout(scale_group)

        scale_row = QHBoxLayout()
        self.scale_check = QCheckBox("Resize image")
        self.scale_check.toggled.connect(self._on_scale_toggled)
        scale_row.addWidget(self.scale_check)
        scale_layout.addLayout(scale_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(self.output_image.width if self.output_image else 320)
        self.width_spin.setEnabled(False)
        size_row.addWidget(self.width_spin)

        size_row.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(self.output_image.height if self.output_image else 256)
        self.height_spin.setEnabled(False)
        size_row.addWidget(self.height_spin)

        self.aspect_check = QCheckBox("Keep aspect")
        self.aspect_check.setChecked(True)
        self.aspect_check.setEnabled(False)
        size_row.addWidget(self.aspect_check)
        scale_layout.addLayout(size_row)

        layout.addWidget(scale_group)

        # Size presets
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QHBoxLayout(preset_group)

        preset_label = QLabel("Resize to:")
        preset_layout.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Custom",
            "Original Size",
            "Square 1080x1080",
            "Square 2048x2048",
            "HD 1920x1080",
            "4K 3840x2160",
            "Instagram Story 1080x1920",
            "Half Size",
            "Double Size"
        ])
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo, stretch=1)

        layout.addWidget(preset_group)

        # Filename customization
        filename_group = QGroupBox("Filename Options")
        filename_layout = QVBoxLayout(filename_group)

        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g., glitch_")
        prefix_row.addWidget(self.prefix_input)
        filename_layout.addLayout(prefix_row)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g., _final")
        suffix_row.addWidget(self.suffix_input)
        filename_layout.addLayout(suffix_row)

        self.auto_number_check = QCheckBox("Auto-increment filename if exists")
        self.auto_number_check.setChecked(True)
        filename_layout.addWidget(self.auto_number_check)

        layout.addWidget(filename_group)

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

    def _on_scale_toggled(self, checked: bool):
        """Enable/disable scaling controls."""
        self.width_spin.setEnabled(checked)
        self.height_spin.setEnabled(checked)
        self.aspect_check.setEnabled(checked)

    def _on_preset_changed(self, preset_name: str):
        """Apply size preset."""
        if not self.output_image:
            return

        orig_width, orig_height = self.output_image.size

        if preset_name == "Custom":
            # Keep current values
            return
        elif preset_name == "Original Size":
            self.width_spin.setValue(orig_width)
            self.height_spin.setValue(orig_height)
            self.scale_check.setChecked(False)
        elif preset_name == "Square 1080x1080":
            self.width_spin.setValue(1080)
            self.height_spin.setValue(1080)
            self.scale_check.setChecked(True)
        elif preset_name == "Square 2048x2048":
            self.width_spin.setValue(2048)
            self.height_spin.setValue(2048)
            self.scale_check.setChecked(True)
        elif preset_name == "HD 1920x1080":
            self.width_spin.setValue(1920)
            self.height_spin.setValue(1080)
            self.scale_check.setChecked(True)
        elif preset_name == "4K 3840x2160":
            self.width_spin.setValue(3840)
            self.height_spin.setValue(2160)
            self.scale_check.setChecked(True)
        elif preset_name == "Instagram Story 1080x1920":
            self.width_spin.setValue(1080)
            self.height_spin.setValue(1920)
            self.scale_check.setChecked(True)
        elif preset_name == "Half Size":
            self.width_spin.setValue(orig_width // 2)
            self.height_spin.setValue(orig_height // 2)
            self.scale_check.setChecked(True)
        elif preset_name == "Double Size":
            self.width_spin.setValue(orig_width * 2)
            self.height_spin.setValue(orig_height * 2)
            self.scale_check.setChecked(True)

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

        # Build default filename with prefix/suffix
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()
        default_filename = f"{prefix}untitled{suffix}{default_ext}"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            default_filename,
            filter_str
        )

        if file_path:
            # Handle auto-increment if enabled
            if self.auto_number_check.isChecked():
                file_path = self._get_unique_filename(file_path)

            self._save_image(file_path, format_name)
            self.export_path = file_path
            self.accept()

    def _get_unique_filename(self, file_path: str) -> str:
        """Get a unique filename by adding a number if file exists."""
        path = Path(file_path)

        if not path.exists():
            return file_path

        # Split into stem and suffix
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        # Try adding numbers until we find a unique name
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return str(new_path)
            counter += 1

    def _save_image(self, file_path: str, format_name: str):
        """Save the image with the specified settings."""
        img = self.output_image

        # Apply scaling if enabled
        if self.scale_check.isChecked():
            new_width = self.width_spin.value()
            new_height = self.height_spin.value()

            if self.aspect_check.isChecked():
                # Maintain aspect ratio
                img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                # Resize to exact dimensions
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Prepare save options
        save_kwargs = {}

        if format_name == "JPEG":
            # Convert to RGB if needed (JPEG doesn't support transparency)
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
            img.save(file_path, format_name, **save_kwargs)

        elif format_name == "PNG":
            save_kwargs["optimize"] = self.optimize_check.isChecked()
            img.save(file_path, format_name, **save_kwargs)

        else:
            # TIFF, BMP
            img.save(file_path, format_name, **save_kwargs)

    def get_export_path(self) -> str:
        """Get the path where the image was exported."""
        return self.export_path
