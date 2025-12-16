"""Popup dialog for viewing saved outputs."""

import json
import subprocess
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QPushButton,
    QWidget,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class OutputPopup(QDialog):
    """Dialog for viewing a saved output's images and video."""

    deleted = pyqtSignal(Path)

    def __init__(self, folder: Path, output_manager, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.output_manager = output_manager
        self.setWindowTitle(f"Output: {folder.name}")
        self.setMinimumSize(600, 500)
        self._setup_ui()
        self._load_metadata()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #252525;
                color: #888;
                padding: 8px 16px;
                border: 1px solid #333;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #fff;
            }
        """)

        # Effects tab
        effects_path = self.folder / "effects.png"
        if effects_path.exists():
            effects_tab = self._create_image_tab(effects_path)
            self.tabs.addTab(effects_tab, "Effects")

        # Clean tab
        clean_path = self.folder / "clean.png"
        if clean_path.exists():
            clean_tab = self._create_image_tab(clean_path)
            self.tabs.addTab(clean_tab, "Clean")

        # Video tab
        video_path = self.folder / "video.mp4"
        if video_path.exists():
            video_tab = self._create_video_tab(video_path)
            self.tabs.addTab(video_tab, "Video")

        layout.addWidget(self.tabs, stretch=1)

        # Metadata info
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Buttons
        buttons_layout = QHBoxLayout()

        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.clicked.connect(self._open_folder)
        buttons_layout.addWidget(open_folder_btn)

        buttons_layout.addStretch()

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a3333;
            }
            QPushButton:hover {
                background-color: #6a4444;
            }
        """)
        delete_btn.clicked.connect(self._delete_output)
        buttons_layout.addWidget(delete_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def _create_image_tab(self, image_path: Path) -> QWidget:
        """Create a tab with an image display."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Load and display image
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Scale to fit while maintaining aspect ratio
            image_label.setPixmap(pixmap.scaled(
                550, 400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        layout.addWidget(image_label)
        return tab

    def _create_video_tab(self, video_path: Path) -> QWidget:
        """Create a tab with video playback."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        layout.addWidget(self.video_widget, stretch=1)

        # Media player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Controls
        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._toggle_play)
        controls_layout.addWidget(self.play_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Load video
        from PyQt6.QtCore import QUrl
        self.media_player.setSource(QUrl.fromLocalFile(str(video_path)))

        # Connect signals
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)

        return tab

    def _toggle_play(self):
        """Toggle video playback."""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _on_playback_state_changed(self, state):
        """Update play button text based on state."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("Pause")
        else:
            self.play_btn.setText("Play")

    def _load_metadata(self):
        """Load and display metadata."""
        metadata_path = self.folder / "metadata.json"
        if not metadata_path.exists():
            self.info_label.setText(f"Folder: {self.folder.name}")
            return

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            info_parts = [
                f"Mode: {metadata.get('mode', 'Unknown')}",
                f"Created: {metadata.get('timestamp', 'Unknown')[:19]}",
            ]

            # List enabled effects
            settings = metadata.get("settings", {})
            enabled_effects = []
            for key, value in settings.items():
                if key.endswith("_enabled") and value:
                    effect_name = key.replace("_enabled", "").replace("_", " ").title()
                    enabled_effects.append(effect_name)

            if enabled_effects:
                info_parts.append(f"Effects: {', '.join(enabled_effects)}")

            self.info_label.setText(" | ".join(info_parts))

        except (json.JSONDecodeError, IOError):
            self.info_label.setText(f"Folder: {self.folder.name}")

    def _open_folder(self):
        """Open the output folder in the system file browser."""
        if sys.platform == "darwin":
            subprocess.run(["open", str(self.folder)])
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(self.folder)])
        else:
            subprocess.run(["xdg-open", str(self.folder)])

    def _delete_output(self):
        """Delete this output after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Output",
            f"Are you sure you want to delete this output?\n\n{self.folder.name}\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.output_manager.delete_output(self.folder):
                self.deleted.emit(self.folder)
                self.close()
            else:
                QMessageBox.warning(
                    self,
                    "Delete Failed",
                    "Could not delete the output folder."
                )

    def closeEvent(self, event):
        """Stop video playback when closing."""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        event.accept()
