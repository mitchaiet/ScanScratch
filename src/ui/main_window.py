"""Main application window with triple-pane layout."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QLabel,
    QStatusBar,
    QPushButton,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QKeySequence, QGuiApplication, QIcon
from PIL import Image
import numpy as np
import time
import os

from .image_viewer import ImageViewer
from .params_panel import ParamsPanel
from .export_dialog import ExportDialog


class StreamingTransmissionWorker(QThread):
    """Worker that plays audio live and decodes line-by-line with A/B comparison."""

    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)  # Detailed status updates
    line_decoded = pyqtSignal(int, object)  # line_number, numpy rgb array (with effects)
    clean_line_decoded = pyqtSignal(int, object)  # line_number, numpy rgb array (clean)
    encoding_done = pyqtSignal(object)  # crop_box tuple
    audio_ready = pyqtSignal(object, int)  # audio_data, sample_rate
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, source_image: Image.Image, settings: dict):
        super().__init__()
        self.source_image = source_image
        self.settings = settings
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop."""
        self._stop_requested = True

    def run(self):
        """Run streaming transmission with live audio and progressive A/B decode."""
        print("=== WORKER THREAD STARTED ===", flush=True)
        try:
            import sounddevice as sd
            print("✓ sounddevice imported", flush=True)
            from src.sstv import SSTVEncoder
            print("✓ SSTVEncoder imported", flush=True)
            from src.sstv.streaming_decoder import StreamingDecoder
            print("✓ StreamingDecoder imported", flush=True)
            from src.effects import EffectsPipeline
            print("✓ EffectsPipeline imported", flush=True)

            # Emit immediately to show we've started
            print("Emitting progress 1", flush=True)
            self.progress.emit(1)
            self.status_message.emit("Initializing transmission...")

            mode = self.settings.get("sstv_mode", "MartinM1")
            print(f"Mode: {mode}", flush=True)

            # Step 1: Encode image to SSTV audio (with aspect ratio preservation)
            print("Starting encoding...", flush=True)
            self.status_message.emit(f"Encoding image to {mode} SSTV signal...")
            self.progress.emit(5)
            encoder = SSTVEncoder()
            print("Encoder created, calling encode()...", flush=True)
            clean_audio, sample_rate = encoder.encode(self.source_image, mode=mode, preserve_aspect=True)
            print(f"✓ Encoding complete: {len(clean_audio)} samples at {sample_rate} Hz", flush=True)
            crop_box = encoder.get_crop_box()
            self.encoding_done.emit(crop_box)
            self.progress.emit(10)

            # Step 2: Apply audio effects to create affected version
            print("Applying effects...", flush=True)
            self.status_message.emit("Applying audio effects...")
            self.progress.emit(12)
            pipeline = EffectsPipeline(sample_rate)
            pipeline.configure(self.settings)
            affected_audio = pipeline.process(clean_audio)
            print(f"✓ Effects applied", flush=True)
            self.progress.emit(15)

            # Send affected audio to visualizer and playback
            print("Sending audio to visualizer...", flush=True)
            self.status_message.emit("Starting transmission playback...")
            self.audio_ready.emit(affected_audio, sample_rate)
            print("✓ Audio sent to visualizer", flush=True)

            # Step 3: Set up streaming decoder for affected version
            print("Creating StreamingDecoder...", flush=True)
            decoder_affected = StreamingDecoder(sample_rate, mode)
            total_lines = decoder_affected.height
            header_duration = decoder_affected.get_header_duration()
            line_duration = decoder_affected.get_line_duration()
            print(f"✓ Decoder ready: {total_lines} lines, {header_duration:.2f}s header, {line_duration:.3f}s/line", flush=True)

            # Step 4: Start audio playback (only affected audio is played)
            print("Starting audio playback...", flush=True)
            self.status_message.emit(f"Transmitting {total_lines} scanlines...")
            try:
                print(f"  Calling sd.play with {len(affected_audio)} samples at {sample_rate}Hz...", flush=True)
                sd.play(affected_audio, sample_rate)
                print("✓ sd.play() returned successfully", flush=True)
            except Exception as e:
                print(f"!!! ERROR in sd.play: {e}", flush=True)
                import traceback
                traceback.print_exc()
                raise

            # Step 5: Decode affected version live, sync with audio playback
            print("Starting progressive decode...", flush=True)
            import time
            start_time = time.time()

            line_count = 0
            print(f"About to enter decode_progressive loop...", flush=True)

            try:
                for line_num, rgb_line in decoder_affected.decode_progressive(affected_audio):
                    if line_count == 0:
                        print(f"✓ First line decoded! line_num={line_num}, rgb_line.shape={rgb_line.shape}", flush=True)
                    line_count += 1

                    if line_count % 10 == 0:
                        print(f"  Line {line_count}/256 decoded...", flush=True)

                    if self._stop_requested:
                        print("Stop requested, breaking...", flush=True)
                        sd.stop()
                        break

                    # Calculate when this line should appear based on audio timing
                    target_time = header_duration + (line_num + 1) * line_duration
                    elapsed = time.time() - start_time

                    # Wait for audio to catch up
                    if elapsed < target_time:
                        sleep_time = target_time - elapsed
                        while sleep_time > 0 and not self._stop_requested:
                            time.sleep(min(0.05, sleep_time))
                            sleep_time -= 0.05

                    try:
                        # Emit the decoded line
                        self.line_decoded.emit(line_num, rgb_line)
                    except Exception as e:
                        print(f"!!! ERROR emitting line_decoded signal: {e}", flush=True)
                        raise

                    try:
                        # Update progress and status (15% to 85% during affected decode)
                        progress = 15 + int((line_num / total_lines) * 70)
                        self.progress.emit(progress)
                    except Exception as e:
                        print(f"!!! ERROR emitting progress: {e}", flush=True)
                        raise

                    # Update status every 32 lines
                    if line_num % 32 == 0:
                        try:
                            percent_complete = int((line_num / total_lines) * 100)
                            self.status_message.emit(f"Decoding: {percent_complete}% ({line_num}/{total_lines} lines)")
                        except Exception as e:
                            print(f"!!! ERROR emitting status message: {e}", flush=True)
                            raise

                print(f"✓ Affected decode loop complete: {line_count} lines", flush=True)
            except Exception as e:
                print(f"\n!!! EXCEPTION IN DECODE LOOP: {e}", flush=True)
                import traceback
                traceback.print_exc()
                raise

            # Wait for audio to finish
            if not self._stop_requested:
                remaining = decoder_affected.get_total_duration() - (time.time() - start_time)
                if remaining > 0:
                    time.sleep(remaining)

            sd.stop()

            # Step 6: Quickly decode clean version (no audio, just fast image processing)
            if not self._stop_requested:
                self.status_message.emit("Processing clean reference...")
                self.progress.emit(90)
                decoder_clean = StreamingDecoder(sample_rate, mode)
                clean_lines = list(decoder_clean.decode_progressive(clean_audio))
                for line_num, rgb_line in clean_lines:
                    if self._stop_requested:
                        break
                    self.clean_line_decoded.emit(line_num, rgb_line)
                self.progress.emit(98)

            self.status_message.emit("Transmission complete!")
            self.progress.emit(100)
            self.finished.emit()

        except Exception as e:
            print(f"\n=== WORKER THREAD ERROR ===", flush=True)
            print(f"Error type: {type(e).__name__}", flush=True)
            print(f"Error message: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            print("=== END ERROR ===\n", flush=True)
            self.error.emit(str(e))
            self.finished.emit()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanScratch - SSTV Glitch Editor")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)

        self._worker = None
        self._output_image_data = None  # Affected version
        self._clean_image_data = None  # Clean version (no effects)
        self._crop_box = None  # For removing letterbox/pillarbox
        self._showing_clean = False  # A/B toggle state

        # Create central widget with vertical layout
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create menu bar first
        self._create_menu_bar()

        # Create unified top bar
        self._create_unified_header()
        main_layout.addWidget(self.header_widget)

        # Create content area with three panes
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        # Left pane: Source image viewer
        self.source_viewer = ImageViewer(title="SOURCE", accept_drops=True)
        splitter.addWidget(self.source_viewer)

        # Middle pane: Parameters
        self.params_panel = ParamsPanel()
        splitter.addWidget(self.params_panel)

        # Right pane: Output image viewer with A/B toggle
        self.output_viewer = ImageViewer(title="OUTPUT", accept_drops=False, show_ab_toggle=True)
        self.output_viewer.ab_toggled.connect(self._on_ab_toggled)
        splitter.addWidget(self.output_viewer)

        # Set initial sizes (left: 35%, middle: 30%, right: 35%)
        splitter.setSizes([400, 350, 400])

        content_layout.addWidget(splitter)
        main_layout.addLayout(content_layout)

        # Create status bar
        self._create_status_bar()

        # Connect signals
        self._connect_signals()

    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        # Open
        open_action = QAction("&Open Image...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Export
        self.export_action = QAction("&Export Output...", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._on_export)
        file_menu.addAction(self.export_action)

        # Copy to Clipboard
        self.copy_action = QAction("&Copy Output to Clipboard", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setEnabled(False)
        self.copy_action.triggered.connect(self._on_copy_output)
        file_menu.addAction(self.copy_action)

        file_menu.addSeparator()

        # Quit
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        # Reset All Effects
        reset_action = QAction("&Reset All Effects", self)
        reset_action.setShortcut(QKeySequence("Ctrl+R"))
        reset_action.triggered.connect(self._on_reset_effects)
        edit_menu.addAction(reset_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        # Zoom controls would go here
        self.fit_source_action = QAction("Fit Source to Window", self)
        self.fit_source_action.setShortcut(QKeySequence("Ctrl+1"))
        self.fit_source_action.triggered.connect(lambda: self.source_viewer.fit_to_window())
        view_menu.addAction(self.fit_source_action)

        self.fit_output_action = QAction("Fit Output to Window", self)
        self.fit_output_action.setShortcut(QKeySequence("Ctrl+2"))
        self.fit_output_action.triggered.connect(lambda: self.output_viewer.fit_to_window())
        view_menu.addAction(self.fit_output_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        # Keyboard shortcuts
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut(QKeySequence("Ctrl+/"))
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        # About
        about_action = QAction("&About ScanScratch", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_unified_header(self):
        """Create unified header bar with logo and controls."""
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QFrame

        self.header_widget = QFrame()
        self.header_widget.setObjectName("unifiedHeader")
        self.header_widget.setMaximumHeight(24)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(8, 1, 8, 1)
        header_layout.setSpacing(6)

        # Logo section - minimal
        logo_label = QLabel("SCANSCRATCH")
        logo_font = QFont()
        logo_font.setPixelSize(9)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setObjectName("headerLogo")
        header_layout.addWidget(logo_label)

        # Spacer
        header_layout.addStretch()

        # Action buttons - compact, no emoji
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("headerButton")
        self.open_btn.setToolTip("Open Image (Ctrl+O)")
        self.open_btn.clicked.connect(self._on_open_file)
        header_layout.addWidget(self.open_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("headerButton")
        self.export_btn.setToolTip("Export Output (Ctrl+E)")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        header_layout.addWidget(self.export_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("headerButton")
        self.copy_btn.setToolTip("Copy to Clipboard (Ctrl+C)")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._on_copy_output)
        header_layout.addWidget(self.copy_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("headerButton")
        reset_btn.setToolTip("Reset All Effects (Ctrl+R)")
        reset_btn.clicked.connect(self._on_reset_effects)
        header_layout.addWidget(reset_btn)

    def _create_status_bar(self):
        """Create status bar with image info."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        self.image_info_label = QLabel("")
        self.status_bar.addPermanentWidget(self.image_info_label)

    def _connect_signals(self):
        """Connect widget signals."""
        self.source_viewer.image_loaded.connect(self._on_source_loaded)
        self.params_panel.transmit_requested.connect(self._on_transmit)
        self.output_viewer.export_requested.connect(self._on_export_version)

    def _on_open_file(self):
        """Open file dialog to load an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;All Files (*)"
        )
        if file_path:
            self.source_viewer.load_image(file_path)

    def _on_export_version(self, version: str):
        """Export a specific version (affected or clean)."""
        image_data = self._clean_image_data if version == "clean" else self._output_image_data

        if image_data is None:
            QMessageBox.warning(self, "No Output", f"No {version} output image available.")
            return

        # Convert to PIL Image
        img = Image.fromarray(image_data, mode='RGB')

        # Apply crop if available
        if self._crop_box is not None:
            left, top, right, bottom = self._crop_box
            left = max(0, left)
            top = max(0, top)
            right = min(img.width, right)
            bottom = min(img.height, bottom)

            # Only crop if valid
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))

        # Open export dialog
        from .export_dialog import ExportDialog
        dialog = ExportDialog(img, self)
        dialog.exec()

    def _on_export(self):
        """Export the output image (currently displayed version)."""
        # Use currently displayed version (clean or affected)
        image_data = self._clean_image_data if self._showing_clean else self._output_image_data

        if image_data is None:
            QMessageBox.warning(self, "No Output", "There is no output image to export.")
            return

        # Convert to PIL Image
        img = Image.fromarray(image_data, mode='RGB')

        # Apply crop if available
        if self._crop_box is not None:
            left, top, right, bottom = self._crop_box
            left = max(0, left)
            top = max(0, top)
            right = min(img.width, right)
            bottom = min(img.height, bottom)
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))

        # Show export dialog
        dialog = ExportDialog(img, self)
        if dialog.exec():
            export_path = dialog.get_export_path()
            if export_path:
                self.status_label.setText(f"Exported to {os.path.basename(export_path)}")
                QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))

    def _on_copy_output(self):
        """Copy output image to clipboard (currently displayed version)."""
        # Use currently displayed version (clean or affected)
        image_data = self._clean_image_data if self._showing_clean else self._output_image_data

        if image_data is None:
            return

        # Convert to PIL Image
        img = Image.fromarray(image_data, mode='RGB')

        # Apply crop if available
        if self._crop_box is not None:
            left, top, right, bottom = self._crop_box
            left = max(0, left)
            top = max(0, top)
            right = min(img.width, right)
            bottom = min(img.height, bottom)
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))

        # Convert to QImage and copy to clipboard
        from PyQt6.QtGui import QImage
        from io import BytesIO

        # Convert PIL to QImage
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        qimg = QImage()
        qimg.loadFromData(buffer.read())

        clipboard = QGuiApplication.clipboard()
        clipboard.setImage(qimg)

        self.status_label.setText("Output copied to clipboard")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    def _on_reset_effects(self):
        """Reset all effects to clean preset."""
        self.params_panel.preset_combo.setCurrentText("Clean")

    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
<h3>Keyboard Shortcuts</h3>
<table cellpadding="8">
<tr><td><b>Ctrl+O</b></td><td>Open Image</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Export Output</td></tr>
<tr><td><b>Ctrl+C</b></td><td>Copy Output to Clipboard</td></tr>
<tr><td><b>Ctrl+R</b></td><td>Reset All Effects</td></tr>
<tr><td><b>Ctrl+1</b></td><td>Fit Source to Window</td></tr>
<tr><td><b>Ctrl+2</b></td><td>Fit Output to Window</td></tr>
<tr><td><b>Ctrl+/</b></td><td>Show Shortcuts</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Quit Application</td></tr>
<tr><td><b>Space</b></td><td>Transmit (when focused)</td></tr>
</table>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)

    def _show_about(self):
        """Show about dialog."""
        about_text = """
<pre style="font-family: monospace; font-size: 9px; line-height: 1.2;">
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ███████╗ ██████╗ █████╗ ███╗   ██╗                     ║
  ║   ██╔════╝██╔════╝██╔══██╗████╗  ██║                     ║
  ║   ███████╗██║     ███████║██╔██╗ ██║                     ║
  ║   ╚════██║██║     ██╔══██║██║╚██╗██║                     ║
  ║   ███████║╚██████╗██║  ██║██║ ╚████║                     ║
  ║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝                     ║
  ║                                                           ║
  ║   ███████╗ ██████╗██████╗  █████╗ ████████╗ ██████╗██╗  ║
  ║   ██╔════╝██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██║  ║
  ║   ███████╗██║     ██████╔╝███████║   ██║   ██║     ██║  ║
  ║   ╚════██║██║     ██╔══██╗██╔══██║   ██║   ██║     ██║  ║
  ║   ███████║╚██████╗██║  ██║██║  ██║   ██║   ╚██████╗██║  ║
  ║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ║
  ║                                                           ║
  ║          ▓▒░  SSTV Glitch Art Generator  ░▒▓            ║
  ╚═══════════════════════════════════════════════════════════╝
</pre>
<p style="text-align: center;"><b>Version 1.0</b></p>
<br>
<p style="text-align: center;">A creative tool for generating glitch art through<br>
SSTV (Slow Scan Television) signal corruption.</p>
<br>
<p style="text-align: center;">Encode images to audio, apply effects, and decode<br>
to create unique visual artifacts.</p>
<br>
<p style="text-align: center; font-size: 10px;">Built with PyQt6 • pysstv • numpy • scipy</p>
        """
        QMessageBox.about(self, "About ScanScratch", about_text)

    def _update_status_bar(self):
        """Update status bar with current image information."""
        source_img = self.source_viewer.get_image()
        if source_img:
            w, h = source_img.size
            self.image_info_label.setText(f"Source: {w}×{h}px")
        else:
            self.image_info_label.setText("")

    def _on_source_loaded(self):
        """Handle source image loaded."""
        self.params_panel.set_transmit_enabled(True)
        self._update_status_bar()
        self.status_label.setText("Image loaded - ready to transmit")

    def _on_transmit(self):
        """Handle transmit button click."""
        print("\n=== TRANSMIT BUTTON CLICKED ===", flush=True)
        try:
            source_image = self.source_viewer.get_image()
            if source_image is None:
                print("No source image loaded", flush=True)
                return

            print(f"Source image: {source_image.size}", flush=True)

            # Stop any existing transmission
            if self._worker is not None and self._worker.isRunning():
                print("Stopping existing worker...", flush=True)
                self._worker.stop()
                self._worker.wait()

            # Get settings and determine output size
            print("Getting effect settings...", flush=True)
            effect_settings = self.params_panel.get_effect_settings()
            mode = effect_settings.get("sstv_mode", "MartinM1")
            print(f"Mode: {mode}", flush=True)

            # Get dimensions for this mode
            print("Getting mode dimensions...", flush=True)
            from src.sstv.streaming_decoder import MODE_SPECS
            spec = MODE_SPECS.get(mode, MODE_SPECS["MartinM1"])
            width, height = spec["width"], spec["height"]
            print(f"Output dimensions: {width}x{height}", flush=True)

            # Initialize blank output images (full frame) for both versions
            print("Initializing output buffers...", flush=True)
            self._output_image_data = np.zeros((height, width, 3), dtype=np.uint8)
            self._clean_image_data = np.zeros((height, width, 3), dtype=np.uint8)
            self._crop_box = None
            self._showing_clean = False
            self._update_output_display()
            print("✓ Output buffers initialized", flush=True)

            # Disable transmit during processing
            print("Disabling UI controls...", flush=True)
            self.params_panel.set_transmit_enabled(False)
            self.params_panel.set_progress(0)
            self.status_label.setText("Transmitting...")
            self.export_action.setEnabled(False)
            self.copy_action.setEnabled(False)
            print("✓ UI controls disabled", flush=True)
        except Exception as e:
            print(f"\n!!! ERROR IN _on_transmit SETUP: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return

        # Create and start worker
        try:
            print("Creating worker thread...", flush=True)
            self._worker = StreamingTransmissionWorker(source_image, effect_settings)
            print("Connecting worker signals...", flush=True)
            self._worker.progress.connect(self._on_progress)
            self._worker.status_message.connect(self._on_status_message)
            self._worker.encoding_done.connect(self._on_encoding_done)
            self._worker.audio_ready.connect(self._on_audio_ready)
            self._worker.line_decoded.connect(self._on_line_decoded)
            self._worker.clean_line_decoded.connect(self._on_clean_line_decoded)
            self._worker.finished.connect(self._on_transmission_finished)
            self._worker.error.connect(self._on_transmission_error)
            print("Starting worker thread...", flush=True)
            self._worker.start()
            print("✓ Worker thread started successfully", flush=True)
        except Exception as e:
            print(f"\n!!! ERROR CREATING/STARTING WORKER: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.params_panel.set_transmit_enabled(True)
            self.status_label.setText(f"Error: {e}")

    def _on_progress(self, value: int):
        """Handle progress update."""
        self.params_panel.set_progress(value)

    def _on_status_message(self, message: str):
        """Handle detailed status message updates."""
        self.status_label.setText(message)

    def _on_encoding_done(self, crop_box):
        """Store crop box for output cropping."""
        self._crop_box = crop_box

    def _on_audio_ready(self, audio_data, sample_rate):
        """Set up audio visualizer with the processed audio."""
        try:
            print(f">>> _on_audio_ready CALLED: audio_data.shape={audio_data.shape}, sample_rate={sample_rate}", flush=True)
            self.params_panel.set_audio_data(audio_data, sample_rate)
            print(f"✓ Audio data sent to params panel", flush=True)
        except Exception as e:
            print(f"!!! ERROR in _on_audio_ready: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise

    def _on_line_decoded(self, line_num: int, rgb_line: np.ndarray):
        """Handle a decoded line from affected stream - update the output image."""
        try:
            if line_num == 0:
                print(f">>> _on_line_decoded HANDLER CALLED: line_num={line_num}, rgb_line.shape={rgb_line.shape}", flush=True)
                print(f"    _output_image_data.shape={self._output_image_data.shape if self._output_image_data is not None else None}", flush=True)
                print(f"    _showing_clean={self._showing_clean}", flush=True)

            if self._output_image_data is not None and line_num < len(self._output_image_data):
                try:
                    self._output_image_data[line_num] = rgb_line
                    if line_num == 0:
                        print(f"    Line {line_num} written to buffer", flush=True)
                except Exception as e:
                    print(f"!!! ERROR writing line to buffer: {e}", flush=True)
                    raise

                if not self._showing_clean:
                    if line_num == 0:
                        print(f"    About to call _update_output_display()...", flush=True)
                        print("Calling _update_output_display()...", flush=True)
                    self._update_output_display()
                    if line_num == 0:
                        print("✓ _update_output_display() completed", flush=True)
        except Exception as e:
            print(f"!!! CRASH in _on_line_decoded at line {line_num}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise

    def _on_clean_line_decoded(self, line_num: int, rgb_line: np.ndarray):
        """Handle a decoded line from clean stream - update the clean image."""
        try:
            if self._clean_image_data is not None and line_num < len(self._clean_image_data):
                self._clean_image_data[line_num] = rgb_line
        except Exception as e:
            print(f"!!! CRASH in _on_clean_line_decoded: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
            if self._showing_clean:
                self._update_output_display()

    def _on_ab_toggled(self, showing_clean: bool):
        """Handle A/B toggle - switch between clean and affected versions."""
        self._showing_clean = showing_clean
        self._update_output_display()

    def _update_output_display(self):
        """Update the output viewer with current image data (clean or affected)."""
        try:
            # Choose which version to display based on A/B toggle state
            image_data = self._clean_image_data if self._showing_clean else self._output_image_data

            if image_data is not None:
                try:
                    img = Image.fromarray(image_data, mode='RGB')
                except Exception as e:
                    print(f"!!! ERROR in Image.fromarray: {e}", flush=True)
                    print(f"    image_data.shape={image_data.shape}, dtype={image_data.dtype}", flush=True)
                    raise

                # Crop to remove letterbox/pillarbox if we have crop info
                if self._crop_box is not None:
                    try:
                        left, top, right, bottom = self._crop_box
                        # Make sure crop box is within bounds
                        left = max(0, left)
                        top = max(0, top)
                        right = min(img.width, right)
                        bottom = min(img.height, bottom)
                        if right > left and bottom > top:
                            img = img.crop((left, top, right, bottom))
                    except Exception as e:
                        print(f"!!! ERROR in cropping: {e}", flush=True)
                        raise

                try:
                    self.output_viewer.set_image(img)
                except Exception as e:
                    print(f"!!! ERROR in output_viewer.set_image: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    raise
        except Exception as e:
            print(f"!!! CRASH in _update_output_display: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise

    def _on_transmission_finished(self):
        """Handle transmission complete."""
        self.params_panel.set_transmit_enabled(True)
        self.params_panel.stop_audio_visualization()
        self.export_action.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.copy_action.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.output_viewer.enable_ab_toggle(True)
        # Status message already set by worker ("Transmission complete!")
        # Add A/B toggle hint
        QTimer.singleShot(500, lambda: self.status_label.setText("Transmission complete - toggle A/B to compare versions"))
        QTimer.singleShot(1000, lambda: self.params_panel.set_progress(0))
        QTimer.singleShot(8000, lambda: self.status_label.setText("Ready"))

    def _on_transmission_error(self, error_msg: str):
        """Handle transmission error."""
        print(f"Transmission error: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        self.params_panel.set_transmit_enabled(True)
        self.status_label.setText(f"Error: {error_msg}")

    def closeEvent(self, event):
        """Handle window close - stop any running transmission."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait()
        event.accept()
