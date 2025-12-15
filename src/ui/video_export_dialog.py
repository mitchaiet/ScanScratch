"""Video export dialog for SSTV transmission animations."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PIL import Image
import numpy as np
from pathlib import Path


class VideoExportWorker(QThread):
    """Worker thread for video export."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, frames, audio_data, sample_rate, output_path, fps=30):
        super().__init__()
        self.frames = frames  # List of PIL Images (progressive decode frames)
        self.audio_data = audio_data  # numpy array
        self.sample_rate = sample_rate
        self.output_path = output_path
        self.fps = fps

    def run(self):
        """Export video with audio."""
        try:
            import cv2
            import soundfile as sf
            import subprocess
            import tempfile
            import os

            # Create temp files
            temp_video = tempfile.mktemp(suffix='.mp4')
            temp_audio = tempfile.mktemp(suffix='.wav')

            # Write video (frames only)
            height, width = np.array(self.frames[0]).shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_video, fourcc, self.fps, (width, height))

            for i, frame in enumerate(self.frames):
                # Convert PIL to OpenCV format (RGB → BGR)
                frame_array = np.array(frame)
                frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
                video_writer.write(frame_bgr)

                # Update progress
                progress_pct = int((i + 1) / len(self.frames) * 50)  # 0-50%
                self.progress.emit(progress_pct)

            video_writer.release()

            # Write audio
            sf.write(temp_audio, self.audio_data, self.sample_rate)
            self.progress.emit(60)

            # Combine video and audio using ffmpeg
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                has_ffmpeg = True
            except:
                has_ffmpeg = False

            if has_ffmpeg:
                # Use ffmpeg to combine
                cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_video,
                    '-i', temp_audio,
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-shortest',
                    self.output_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                self.progress.emit(100)
            else:
                # No ffmpeg - just save video without audio
                import shutil
                shutil.copy(temp_video, self.output_path)
                self.progress.emit(100)
                self.error.emit("ffmpeg not found - video exported without audio. Install ffmpeg for audio support.")

            # Cleanup
            try:
                os.remove(temp_video)
                os.remove(temp_audio)
            except:
                pass

            self.finished.emit(self.output_path)

        except Exception as e:
            self.error.emit(f"Video export failed: {str(e)}")


class VideoExportDialog(QDialog):
    """Dialog for exporting SSTV transmission as video with audio."""

    def __init__(self, frames, audio_data, sample_rate, parent=None):
        super().__init__(parent)
        self.frames = frames  # List of PIL Images showing progressive decode
        self.audio_data = audio_data  # numpy array of audio
        self.sample_rate = sample_rate
        self.export_path = None
        self.worker = None

        self.setWindowTitle("Export SSTV Video")
        self.setModal(True)
        self.setMinimumWidth(450)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Video info
        info_group = QGroupBox("Video Information")
        info_layout = QVBoxLayout(info_group)

        if self.frames:
            width, height = self.frames[0].size
            num_frames = len(self.frames)
            duration = len(self.audio_data) / self.sample_rate if self.audio_data is not None else 0

            info_layout.addWidget(QLabel(f"Resolution: {width} × {height} px"))
            info_layout.addWidget(QLabel(f"Frames: {num_frames}"))
            info_layout.addWidget(QLabel(f"Duration: {duration:.1f} seconds"))
            info_layout.addWidget(QLabel(f"Audio: {self.sample_rate} Hz, {len(self.audio_data)} samples"))

        layout.addWidget(info_group)

        # Settings
        settings_group = QGroupBox("Export Settings")
        settings_layout = QVBoxLayout(settings_group)

        # FPS selector
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Frame Rate:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24 fps", "30 fps", "60 fps"])
        self.fps_combo.setCurrentText("30 fps")
        fps_row.addWidget(self.fps_combo, stretch=1)
        settings_layout.addLayout(fps_row)

        layout.addWidget(settings_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Note about ffmpeg
        note_label = QLabel("Note: Requires ffmpeg for audio encoding")
        note_label.setStyleSheet("color: #888;")
        layout.addWidget(note_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("Export Video")
        self.export_btn.setDefault(True)
        self.export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

    def _on_export(self):
        """Handle export button click."""
        if not self.frames:
            QMessageBox.warning(self, "No Frames", "No frames to export.")
            return

        # Get FPS
        fps_text = self.fps_combo.currentText()
        fps = int(fps_text.split()[0])

        # Show save dialog
        default_name = "sstv_transmission.mp4"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export SSTV Video",
            str(Path.home() / default_name),
            "MP4 Video (*.mp4);;All Files (*.*)",
        )

        if not file_path:
            return

        # Add extension if missing
        if not file_path.lower().endswith('.mp4'):
            file_path += '.mp4'

        # Start export in background thread
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(False)

        self.worker = VideoExportWorker(
            self.frames,
            self.audio_data,
            self.sample_rate,
            file_path,
            fps
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._on_export_finished)
        self.worker.error.connect(self._on_export_error)
        self.worker.start()

    def _on_export_finished(self, path):
        """Handle successful export."""
        self.export_path = path
        QMessageBox.information(self, "Export Complete", f"Video exported to:\n{path}")
        self.accept()

    def _on_export_error(self, error_msg):
        """Handle export error."""
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Export Warning", error_msg)
        # Don't reject - user might want to try again
