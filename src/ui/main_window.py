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
from PyQt6.QtGui import QAction, QKeySequence, QGuiApplication, QIcon, QImage
from PIL import Image
import numpy as np
import time
import os

from .image_viewer import ImageViewer
from .params_panel import ParamsPanel
from .export_dialog import ExportDialog
from .gallery_panel import GalleryPanel
from .output_popup import OutputPopup
from ..output_manager import OutputManager


class RealTimeAudioPlayer:
    """Real-time audio player with callback-based streaming and live effects."""

    def __init__(self, clean_audio: np.ndarray, pipeline, sample_rate: int):
        """
        Initialize real-time audio player.

        Args:
            clean_audio: The clean (unprocessed) audio data
            pipeline: EffectsPipeline instance for live processing
            sample_rate: Audio sample rate
        """
        import sounddevice as sd
        import threading

        self.clean_audio = clean_audio
        self.pipeline = pipeline
        self.sample_rate = sample_rate
        self.position = 0
        self._stream = None
        self._stop_requested = False

        # Buffer size affects latency: smaller = more responsive, larger = more stable
        self.blocksize = 1024  # ~23ms at 44100Hz

        # Buffer to accumulate processed audio for decoding
        self.processed_buffer = np.zeros(len(clean_audio), dtype=np.float32)
        self.processed_position = 0
        self._buffer_lock = threading.Lock()

    def _audio_callback(self, outdata, frames, time_info, status):
        """Audio callback - processes chunks in real-time."""
        import sounddevice as sd

        if status:
            print(f"Audio callback status: {status}", flush=True)

        # Get chunk from clean audio
        end_pos = min(self.position + frames, len(self.clean_audio))
        chunk = self.clean_audio[self.position:end_pos].copy()

        # Pad if needed (end of audio)
        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)), mode='constant')

        # Apply effects in real-time with current knob values
        if self.pipeline is not None:
            try:
                processed = self.pipeline.process_chunk(chunk)
            except Exception as e:
                print(f"Effect processing error: {e}", flush=True)
                processed = chunk
        else:
            processed = chunk

        # Store processed audio in buffer for decoding
        with self._buffer_lock:
            write_end = min(self.processed_position + len(processed), len(self.processed_buffer))
            write_len = write_end - self.processed_position
            if write_len > 0:
                self.processed_buffer[self.processed_position:write_end] = processed[:write_len]
                self.processed_position = write_end

        # Output as mono (reshape to (frames, 1))
        outdata[:] = processed.reshape(-1, 1)

        # Advance position
        self.position += frames

        # Signal end of playback
        if self.position >= len(self.clean_audio):
            raise sd.CallbackStop()

    def start(self):
        """Start audio playback."""
        import sounddevice as sd
        self.position = 0
        self.processed_position = 0
        self._stop_requested = False
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=self.blocksize,
            callback=self._audio_callback
        )
        self._stream.start()

    def stop(self):
        """Stop audio playback."""
        self._stop_requested = True
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def pause(self):
        """Pause audio playback."""
        if self._stream is not None and self._stream.active:
            self._stream.stop()
            self._paused = True

    def resume(self):
        """Resume audio playback."""
        if self._stream is not None and hasattr(self, '_paused') and self._paused:
            self._stream.start()
            self._paused = False

    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return hasattr(self, '_paused') and self._paused

    def is_active(self) -> bool:
        """Check if playback is still active."""
        return self._stream is not None and (self._stream.active or self.is_paused())

    def get_position(self) -> int:
        """Get current sample position."""
        return self.position

    def get_processed_position(self) -> int:
        """Get position of processed audio in buffer."""
        with self._buffer_lock:
            return self.processed_position

    def get_processed_audio(self, start: int, end: int) -> np.ndarray:
        """Get a slice of the processed audio buffer."""
        with self._buffer_lock:
            end = min(end, self.processed_position)
            if start >= end:
                return np.array([], dtype=np.float32)
            return self.processed_buffer[start:end].copy()

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)."""
        if len(self.clean_audio) == 0:
            return 1.0
        return self.position / len(self.clean_audio)


class StreamingTransmissionWorker(QThread):
    """Worker that plays audio live and decodes line-by-line with A/B comparison."""

    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)  # Detailed status updates
    line_decoded = pyqtSignal(int, object)  # line_number, numpy rgb array (with effects)
    clean_line_decoded = pyqtSignal(int, object)  # line_number, numpy rgb array (clean)
    encoding_done = pyqtSignal(object)  # crop_box tuple
    audio_ready = pyqtSignal(object, int)  # audio_data, sample_rate
    pipeline_ready = pyqtSignal(object)  # pipeline for live control
    audio_player_ready = pyqtSignal(object)  # audio player for pause/resume control
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
        audio_player = None
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

            # Step 2: Configure effects pipeline (but don't apply yet - real-time processing)
            print("Configuring effects pipeline...", flush=True)
            self.status_message.emit("Configuring audio effects...")
            self.progress.emit(12)
            pipeline = EffectsPipeline(sample_rate)
            pipeline.configure(self.settings)

            # Emit pipeline reference so UI can connect knobs
            self.pipeline_ready.emit(pipeline)
            print(f"✓ Pipeline configured and emitted", flush=True)
            self.progress.emit(15)

            # Step 3: Set up streaming decoder
            print("Creating StreamingDecoder...", flush=True)
            # For NativeRes mode, pass image dimensions
            if mode == "NativeRes":
                width, height = self.source_image.size
                decoder_affected = StreamingDecoder(sample_rate, mode, width=width, height=height)
            else:
                decoder_affected = StreamingDecoder(sample_rate, mode)
            total_lines = decoder_affected.height
            header_samples = decoder_affected.header_samples
            line_samples = decoder_affected.line_samples
            print(f"✓ Decoder ready: {total_lines} lines", flush=True)

            # Step 4: Create real-time audio player with pipeline
            print("Creating real-time audio player...", flush=True)
            self.status_message.emit(f"Transmitting {total_lines} scanlines (real-time effects)...")

            audio_player = RealTimeAudioPlayer(clean_audio, pipeline, sample_rate)

            # Send audio player reference for pause/resume control
            self.audio_player_ready.emit(audio_player)

            # Send clean audio to visualizer (it will show the waveform)
            self.audio_ready.emit(clean_audio, sample_rate)

            try:
                audio_player.start()
                print("✓ Real-time audio player started", flush=True)
            except Exception as e:
                print(f"!!! ERROR starting audio player: {e}", flush=True)
                import traceback
                traceback.print_exc()
                raise

            # Step 5: Decode lines in real-time from processed audio buffer
            print("Starting real-time decode from processed audio...", flush=True)

            # Create a line decoder that works with the streaming decoder's parameters
            from src.sstv.streaming_decoder import FREQ_BLACK, FREQ_WHITE
            from scipy import signal as sig

            # Pre-compute filter for FM demodulation
            nyq = sample_rate / 2
            low = 1000 / nyq
            high = 2500 / nyq
            filter_b, filter_a = sig.butter(4, [low, high], btype='band')

            def decode_line_from_audio(audio_segment, width):
                """Decode a single line from processed audio segment."""
                if len(audio_segment) < 100:
                    return np.zeros((width, 3), dtype=np.uint8)

                # FM demodulate this segment
                try:
                    filtered = sig.lfilter(filter_b, filter_a, audio_segment)
                    analytic = sig.hilbert(filtered)
                    phase = np.unwrap(np.angle(analytic))
                    freq = np.diff(phase) * sample_rate / (2 * np.pi)
                    freq = np.append(freq, freq[-1])
                except Exception:
                    return np.zeros((width, 3), dtype=np.uint8)

                # Extract RGB channels from line
                # Line structure: [sync][gap][CH1][gap][CH2][gap][CH3][gap]
                sync_samples = decoder_affected.sync_samples
                gap_samples = decoder_affected.gap_samples
                scan_samples = decoder_affected.scan_samples

                ch1_start = sync_samples + gap_samples
                ch2_start = ch1_start + scan_samples + gap_samples
                ch3_start = ch2_start + scan_samples + gap_samples

                rgb = np.zeros((width, 3), dtype=np.uint8)

                def extract_channel(start, length):
                    end = start + length
                    if end > len(freq):
                        return np.zeros(width, dtype=np.uint8)
                    segment = freq[start:end]
                    indices = np.linspace(0, len(segment) - 1, width).astype(int)
                    resampled = segment[indices]
                    intensity = (resampled - FREQ_BLACK) / (FREQ_WHITE - FREQ_BLACK)
                    return np.clip(intensity * 255, 0, 255).astype(np.uint8)

                # For RGB order (PD modes and NativeRes)
                if decoder_affected.spec.get("color_order") == "RGB":
                    rgb[:, 0] = extract_channel(ch1_start, scan_samples)
                    rgb[:, 1] = extract_channel(ch2_start, scan_samples)
                    rgb[:, 2] = extract_channel(ch3_start, scan_samples)
                else:  # GBR order (Martin, Scottie)
                    rgb[:, 1] = extract_channel(ch1_start, scan_samples)  # G
                    rgb[:, 2] = extract_channel(ch2_start, scan_samples)  # B
                    rgb[:, 0] = extract_channel(ch3_start, scan_samples)  # R

                return rgb

            # Step 6: Sync line display with audio playback, decode from live buffer
            print("Syncing display with live processed audio...", flush=True)
            last_decoded_line = -1
            width = decoder_affected.width

            while audio_player.is_active() and not self._stop_requested:
                # Get current processed position
                processed_pos = audio_player.get_processed_position()

                # Calculate which line we can decode based on processed audio
                if processed_pos < header_samples:
                    decodable_line = -1
                else:
                    # We can decode a line when we have all samples for it
                    decodable_line = (processed_pos - header_samples) // line_samples - 1

                # Decode any new lines that have enough audio
                while last_decoded_line < decodable_line and last_decoded_line < total_lines - 1:
                    last_decoded_line += 1
                    line_num = last_decoded_line

                    # Get audio segment for this line
                    line_start = header_samples + line_num * line_samples
                    line_end = line_start + line_samples
                    line_audio = audio_player.get_processed_audio(line_start, line_end)

                    if len(line_audio) >= line_samples:
                        rgb_line = decode_line_from_audio(line_audio, width)
                        self.line_decoded.emit(line_num, rgb_line)

                        # Update progress (15% to 85% during decode)
                        progress = 15 + int((line_num / total_lines) * 70)
                        self.progress.emit(progress)

                        # Update status every 32 lines
                        if line_num % 32 == 0:
                            percent_complete = int((line_num / total_lines) * 100)
                            self.status_message.emit(f"Live decode: {percent_complete}% ({line_num}/{total_lines} lines)")

                # Small sleep to avoid busy-waiting
                time.sleep(0.01)

            # Decode any remaining lines after playback ends
            while last_decoded_line < total_lines - 1:
                last_decoded_line += 1
                line_num = last_decoded_line
                line_start = header_samples + line_num * line_samples
                line_end = line_start + line_samples
                line_audio = audio_player.get_processed_audio(line_start, line_end)

                if len(line_audio) >= line_samples:
                    rgb_line = decode_line_from_audio(line_audio, width)
                    self.line_decoded.emit(line_num, rgb_line)

            print(f"✓ Live decode complete", flush=True)

            # Stop audio player
            if audio_player is not None:
                audio_player.stop()

            # Step 7: Quickly decode clean version (no audio, just fast image processing)
            if not self._stop_requested:
                self.status_message.emit("Processing clean reference...")
                self.progress.emit(90)
                # For NativeRes mode, pass image dimensions
                if mode == "NativeRes":
                    width, height = self.source_image.size
                    decoder_clean = StreamingDecoder(sample_rate, mode, width=width, height=height)
                else:
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
            if audio_player is not None:
                audio_player.stop()
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
        self._audio_player = None  # For pause/resume control
        self._output_image_data = None  # Affected version
        self._clean_image_data = None  # Clean version (no effects)
        self._crop_box = None  # For removing letterbox/pillarbox
        self._showing_clean = False  # A/B toggle state
        self._current_mode = None  # Current SSTV mode for auto-save
        self._current_settings = None  # Current effect settings for auto-save
        self._output_manager = OutputManager()  # Manages saving outputs

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

        # Create gallery panel
        self.gallery_panel = GalleryPanel(self._output_manager)
        self.gallery_panel.output_selected.connect(self._on_gallery_output_selected)
        main_layout.addWidget(self.gallery_panel)

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
        self.header_widget.setMaximumHeight(32)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 4, 12, 4)
        header_layout.setSpacing(8)

        # Logo section
        logo_label = QLabel("SCANSCRATCH")
        logo_font = QFont()
        logo_font.setPixelSize(11)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setObjectName("headerLogo")
        header_layout.addWidget(logo_label)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #444;")
        header_layout.addWidget(sep1)

        # File operations
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("headerButton")
        self.open_btn.setToolTip("Open Image (Ctrl+O)")
        self.open_btn.clicked.connect(self._on_open_file)
        header_layout.addWidget(self.open_btn)

        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("headerButton")
        paste_btn.setToolTip("Paste Image from Clipboard (Ctrl+V)")
        paste_btn.clicked.connect(self._on_paste_image)
        header_layout.addWidget(paste_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("headerButton")
        self.copy_btn.setToolTip("Copy Output to Clipboard (Ctrl+C)")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._on_copy_output)
        header_layout.addWidget(self.copy_btn)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #444;")
        header_layout.addWidget(sep2)

        # Effects operations
        randomize_btn = QPushButton("Randomize")
        randomize_btn.setObjectName("headerButton")
        randomize_btn.setToolTip("Randomize Effect Parameters")
        randomize_btn.clicked.connect(self._on_randomize_effects)
        header_layout.addWidget(randomize_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("headerButton")
        reset_btn.setToolTip("Reset All Effects (Ctrl+R)")
        reset_btn.clicked.connect(self._on_reset_effects)
        header_layout.addWidget(reset_btn)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #444;")
        header_layout.addWidget(sep3)

        # Playback controls
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("headerButton")
        self.pause_btn.setToolTip("Pause/Resume Transmission Playback")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_toggle_pause)
        header_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("headerButton")
        self.stop_btn.setToolTip("Stop Transmission")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_transmission)
        header_layout.addWidget(self.stop_btn)

        # Spacer
        header_layout.addStretch()

        # Outputs folder button
        outputs_btn = QPushButton("Outputs")
        outputs_btn.setObjectName("headerButton")
        outputs_btn.setToolTip("Open Outputs Folder")
        outputs_btn.clicked.connect(self._on_open_outputs_folder)
        header_layout.addWidget(outputs_btn)

    def _create_status_bar(self):
        """Create status bar with progress and info."""
        from PyQt6.QtWidgets import QProgressBar

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1a1a1a;
                border-top: 1px solid #333;
                padding: 2px 8px;
            }
            QStatusBar QLabel {
                color: #888;
                padding: 0 8px;
            }
            QStatusBar QProgressBar {
                border: 1px solid #333;
                border-radius: 3px;
                background-color: #252525;
                text-align: center;
                color: #888;
                max-height: 12px;
                min-width: 150px;
            }
            QStatusBar QProgressBar::chunk {
                background-color: #4a7c4a;
                border-radius: 2px;
            }
        """)
        self.setStatusBar(self.status_bar)

        # Status text
        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(200)
        self.status_bar.addWidget(self.status_label, 1)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)

        # Mode indicator
        self.mode_label = QLabel("")
        self.status_bar.addPermanentWidget(self.mode_label)

        # Image info
        self.image_info_label = QLabel("")
        self.status_bar.addPermanentWidget(self.image_info_label)

        # Output count
        self.output_count_label = QLabel("")
        self.status_bar.addPermanentWidget(self.output_count_label)
        self._update_output_count()

    def _connect_signals(self):
        """Connect widget signals."""
        self.source_viewer.image_loaded.connect(self._on_source_loaded)
        self.params_panel.transmit_requested.connect(self._on_transmit)

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

    def _on_paste_image(self):
        """Paste image from clipboard."""
        clipboard = QGuiApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            qimg = clipboard.image()
            if not qimg.isNull():
                # Convert QImage to PIL Image
                qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
                width = qimg.width()
                height = qimg.height()
                ptr = qimg.bits()
                ptr.setsize(height * width * 3)
                arr = np.array(ptr).reshape(height, width, 3)
                pil_image = Image.fromarray(arr)

                # Load into source viewer
                self.source_viewer.set_image(pil_image)
                self.status_label.setText("Image pasted from clipboard")
                return

        self.status_label.setText("No image in clipboard")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    def _on_randomize_effects(self):
        """Randomize effect parameters."""
        import random
        self.params_panel.preset_combo.setCurrentText("Random")
        self.status_label.setText("Effects randomized")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    def _on_open_outputs_folder(self):
        """Open the outputs folder in file explorer."""
        import subprocess
        import platform
        outputs_path = os.path.abspath("outputs")
        os.makedirs(outputs_path, exist_ok=True)

        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", outputs_path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", outputs_path])
        else:  # Linux
            subprocess.run(["xdg-open", outputs_path])

    def _update_output_count(self):
        """Update the output count in status bar."""
        try:
            outputs = self._output_manager.get_all_outputs()
            count = len(outputs)
            self.output_count_label.setText(f"{count} outputs")
        except Exception:
            self.output_count_label.setText("")

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
<p style="text-align: center;"><b>Version 1.1.0</b></p>
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

            # Store for auto-save
            self._current_mode = mode
            self._current_settings = effect_settings

            # Get dimensions for this mode
            print("Getting mode dimensions...", flush=True)
            if mode == "NativeRes":
                # For Native Resolution mode, use source image dimensions
                width, height = source_image.size
            else:
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
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.mode_label.setText(f"Mode: {mode}")
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
            self._worker.pipeline_ready.connect(self._on_pipeline_ready)
            self._worker.audio_player_ready.connect(self._on_audio_player_ready)
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
        self.progress_bar.setValue(value)

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

    def _on_pipeline_ready(self, pipeline):
        """Connect pipeline to params panel for live effect control."""
        try:
            print(f">>> _on_pipeline_ready CALLED: pipeline={pipeline}", flush=True)
            self.params_panel.set_active_pipeline(pipeline)
            print(f"✓ Pipeline connected to params panel", flush=True)
        except Exception as e:
            print(f"!!! ERROR in _on_pipeline_ready: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise

    def _on_audio_player_ready(self, audio_player):
        """Store audio player reference for pause/resume control."""
        self._audio_player = audio_player
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("Pause")

    def _on_toggle_pause(self):
        """Toggle pause/resume of transmission playback."""
        if self._audio_player is None:
            return

        if self._audio_player.is_paused():
            self._audio_player.resume()
            self.pause_btn.setText("Pause")
            self.status_label.setText("Resumed playback")
        else:
            self._audio_player.pause()
            self.pause_btn.setText("Resume")
            self.status_label.setText("Paused - press Resume to continue")

    def _on_stop_transmission(self):
        """Stop the current transmission."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            if self._audio_player is not None:
                self._audio_player.stop()
            self.status_label.setText("Transmission stopped")
            # Disable buttons
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

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
        self.params_panel.clear_active_pipeline()  # Disconnect knobs from pipeline
        self.copy_action.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.output_viewer.enable_ab_toggle(True)
        self.progress_bar.setVisible(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._audio_player = None

        # Start auto-save in background
        self._start_auto_save()

        # Status will be updated by auto-save
        QTimer.singleShot(1000, lambda: self.params_panel.set_progress(0))

    def _start_auto_save(self):
        """Start auto-saving outputs in background."""
        if self._output_image_data is None or self._current_mode is None:
            return

        self.status_label.setText("Saving outputs...")

        # Create auto-save worker
        class AutoSaveWorker(QThread):
            finished = pyqtSignal(str)  # folder path
            progress = pyqtSignal(str)  # status message
            error = pyqtSignal(str)

            def __init__(self, output_manager, mode, settings, affected_data, clean_data, crop_box, source_image):
                super().__init__()
                self.output_manager = output_manager
                self.mode = mode
                self.settings = settings
                self.affected_data = affected_data.copy() if affected_data is not None else None
                self.clean_data = clean_data.copy() if clean_data is not None else None
                self.crop_box = crop_box
                self.source_image = source_image

            def run(self):
                try:
                    # Create output folder
                    folder = self.output_manager.create_output_folder(self.mode)
                    self.progress.emit("Saving images...")

                    # Skip upscaling for NativeRes mode (already full resolution)
                    is_native_res = self.mode == "NativeRes"

                    # Save effects version
                    if self.affected_data is not None:
                        self.output_manager.save_image(folder, "effects", self.affected_data, self.crop_box, skip_upscale=is_native_res)

                    # Save clean version
                    if self.clean_data is not None:
                        self.output_manager.save_image(folder, "clean", self.clean_data, self.crop_box, skip_upscale=is_native_res)

                    # Save thumbnail (use effects version)
                    if self.affected_data is not None:
                        self.output_manager.save_thumbnail(folder, self.affected_data)

                    # Save metadata
                    self.output_manager.save_metadata(folder, self.settings, mode=self.mode)

                    # Generate video using the actual decoded image
                    self.progress.emit("Generating video...")
                    try:
                        from src.export.video_export import create_decode_video_from_image
                        video_path = str(folder / "video.mp4")
                        print(f"[AutoSave] Starting video export to: {video_path}", flush=True)
                        print(f"[AutoSave] Affected image shape: {self.affected_data.shape}", flush=True)
                        print(f"[AutoSave] Mode: {self.mode}", flush=True)
                        success = create_decode_video_from_image(
                            self.affected_data,  # Use the actual decoded image
                            self.source_image,
                            self.mode,
                            self.settings,
                            video_path,
                            fps=30,
                        )
                        print(f"[AutoSave] Video export returned: {success}", flush=True)
                        if success:
                            print(f"[AutoSave] Video saved successfully to {video_path}", flush=True)
                        else:
                            print(f"[AutoSave] Video export failed", flush=True)
                    except Exception as e:
                        print(f"[AutoSave] Video export error (non-fatal): {e}", flush=True)
                        import traceback
                        traceback.print_exc()

                    self.finished.emit(str(folder))
                except Exception as e:
                    self.error.emit(str(e))

        self._auto_save_worker = AutoSaveWorker(
            self._output_manager,
            self._current_mode,
            self._current_settings,
            self._output_image_data,
            self._clean_image_data,
            self._crop_box,
            self.source_viewer.get_image(),
        )

        def on_progress(status):
            self.status_label.setText(status)

        def on_finished(folder_path):
            from pathlib import Path
            self.gallery_panel.add_output(Path(folder_path))
            self._update_output_count()
            self.status_label.setText(f"Saved to {os.path.basename(folder_path)}")
            QTimer.singleShot(5000, lambda: self.status_label.setText("Ready"))

        def on_error(error_msg):
            self.status_label.setText(f"Save error: {error_msg}")
            QTimer.singleShot(5000, lambda: self.status_label.setText("Ready"))

        self._auto_save_worker.progress.connect(on_progress)
        self._auto_save_worker.finished.connect(on_finished)
        self._auto_save_worker.error.connect(on_error)
        self._auto_save_worker.start()

    def _on_gallery_output_selected(self, folder):
        """Handle gallery thumbnail click."""
        popup = OutputPopup(folder, self._output_manager, self)
        popup.deleted.connect(lambda: self.gallery_panel.refresh())
        popup.exec()

    def _on_transmission_error(self, error_msg: str):
        """Handle transmission error."""
        print(f"Transmission error: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        self.params_panel.set_transmit_enabled(True)
        self.progress_bar.setVisible(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self._audio_player = None
        self.status_label.setText(f"Error: {error_msg}")

    def closeEvent(self, event):
        """Handle window close - stop any running transmission."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait()
        event.accept()
