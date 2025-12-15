"""Audio waveform visualizer widget with integrated progress."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont
import numpy as np


class AudioVisualizer(QWidget):
    """Displays an animated audio spectrum with smooth animations, focused on SSTV frequencies."""

    # SSTV frequency range
    FREQ_SYNC = 1200   # Sync pulse
    FREQ_BLACK = 1500  # Black level
    FREQ_WHITE = 2300  # White level

    # Visualizer range (slightly wider for context)
    VIZ_FREQ_LOW = 1100
    VIZ_FREQ_HIGH = 2400

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)

        self._audio_data = None
        self._sample_rate = 44100
        self._is_playing = False
        self._progress = 0

        # Smoothing for fluid animation
        self._num_bars = 40  # More bars for better frequency resolution
        self._current_heights = np.zeros(self._num_bars)
        self._target_heights = np.zeros(self._num_bars)
        self._smoothing = 0.3  # Lower = smoother, higher = more responsive

        # Real-time tracking
        self._elapsed_timer = QElapsedTimer()
        self._start_offset = 0

        # Animation timer - 60 FPS for fluid animation
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)

        # Colors
        self._bg_color = QColor(35, 35, 35)
        self._inactive_color = QColor(50, 50, 50)
        self._sync_marker_color = QColor(180, 100, 100, 120)
        self._range_marker_color = QColor(100, 180, 100, 120)

    def set_audio(self, audio_data: np.ndarray, sample_rate: int):
        """Set the audio data to visualize."""
        self._audio_data = audio_data
        self._sample_rate = sample_rate
        self._current_heights = np.zeros(self._num_bars)
        self._target_heights = np.zeros(self._num_bars)
        self.update()

    def start_playback(self):
        """Start the visualization animation."""
        self._is_playing = True
        self._elapsed_timer.start()
        self._start_offset = 0
        self._timer.start(16)  # ~60 FPS
        self.update()

    def stop_playback(self):
        """Stop the visualization."""
        self._is_playing = False
        self._timer.stop()
        self._current_heights = np.zeros(self._num_bars)
        self._target_heights = np.zeros(self._num_bars)
        self._progress = 0
        self.update()

    def set_progress(self, value: int):
        """Set progress value (0-100)."""
        self._progress = value
        self.update()

    def _get_current_position(self) -> int:
        """Get current playback position in samples based on real time."""
        if self._audio_data is None or not self._is_playing:
            return 0

        elapsed_ms = self._elapsed_timer.elapsed()
        elapsed_samples = int((elapsed_ms / 1000.0) * self._sample_rate)
        return min(elapsed_samples, len(self._audio_data) - 1)

    def _animate(self):
        """Animation tick - update bar heights smoothly."""
        if self._audio_data is None or not self._is_playing:
            return

        # Get current position based on real elapsed time
        pos = self._get_current_position()

        # Calculate target heights from FFT
        self._calculate_spectrum(pos)

        # Smooth interpolation toward target
        self._current_heights += (self._target_heights - self._current_heights) * self._smoothing

        self.update()

    def _calculate_spectrum(self, position: int):
        """Calculate frequency spectrum at current position, focused on SSTV range."""
        if self._audio_data is None:
            return

        # Get a window of audio around current position
        window_size = 1024  # Larger window for better frequency resolution
        start = max(0, position - window_size // 2)
        end = min(len(self._audio_data), start + window_size)

        if end - start < 256:
            self._target_heights = np.zeros(self._num_bars)
            return

        window = self._audio_data[start:end]

        try:
            # Apply Hanning window and compute FFT
            n = len(window)
            windowed = window * np.hanning(n)
            fft = np.abs(np.fft.rfft(windowed))

            # Focus on SSTV frequency range (1100-2400 Hz)
            freq_per_bin = self._sample_rate / n
            low_bin = int(self.VIZ_FREQ_LOW / freq_per_bin)
            high_bin = min(int(self.VIZ_FREQ_HIGH / freq_per_bin), len(fft))

            if high_bin <= low_bin:
                self._target_heights = np.zeros(self._num_bars)
                return

            # Map FFT bins to display bars
            fft_range = fft[low_bin:high_bin]
            bins_per_bar = max(1, len(fft_range) // self._num_bars)

            for i in range(self._num_bars):
                start_bin = i * bins_per_bar
                end_bin = min(start_bin + bins_per_bar, len(fft_range))
                if start_bin < end_bin:
                    self._target_heights[i] = np.mean(fft_range[start_bin:end_bin])

            # Normalize with slight boost for visibility
            max_val = np.max(self._target_heights)
            if max_val > 0:
                self._target_heights = (self._target_heights / max_val) * 1.2
                self._target_heights = np.clip(self._target_heights, 0, 1)

        except Exception:
            self._target_heights = np.zeros(self._num_bars)

    def paintEvent(self, event):
        """Draw the visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(0, 0, width, height, 6, 6)

        # Draw frequency markers (behind bars)
        self._draw_frequency_markers(painter, width, height)

        # Draw spectrum bars
        self._draw_bars(painter, width, height)

        # Draw frequency labels
        self._draw_frequency_labels(painter, width, height)

        # Draw progress bar
        self._draw_progress_bar(painter, width, height)

    def _draw_bars(self, painter, width, height):
        """Draw the frequency bars."""
        bar_width = (width - 20) // self._num_bars
        bar_spacing = 2
        max_bar_height = height - 20

        heights = self._current_heights if self._is_playing else np.zeros(self._num_bars)

        for i in range(self._num_bars):
            mag = heights[i] if i < len(heights) else 0

            # Minimum bar height for visual feedback
            bar_height = max(4, int(mag * max_bar_height * 0.9))

            if not self._is_playing:
                # Idle state - small static bars
                bar_height = 4 + (i * 3) % 8

            x = 10 + i * bar_width
            y = height - 12 - bar_height

            # Color based on magnitude
            if self._is_playing and mag > 0:
                r = int(70 + mag * 100)
                g = int(140 + mag * 80)
                b = int(70 + mag * 60)
                color = QColor(r, g, b)
            else:
                color = self._inactive_color

            painter.fillRect(
                x, y,
                bar_width - bar_spacing, bar_height,
                color
            )

    def _freq_to_x(self, freq: float, width: int) -> int:
        """Convert frequency to X position in the visualizer."""
        freq_range = self.VIZ_FREQ_HIGH - self.VIZ_FREQ_LOW
        freq_ratio = (freq - self.VIZ_FREQ_LOW) / freq_range
        return int(10 + freq_ratio * (width - 20))

    def _draw_frequency_markers(self, painter, width, height):
        """Draw vertical markers for key SSTV frequencies."""
        painter.setPen(Qt.PenStyle.NoPen)

        # Sync frequency marker (red)
        sync_x = self._freq_to_x(self.FREQ_SYNC, width)
        painter.fillRect(sync_x - 1, 10, 2, height - 26, self._sync_marker_color)

        # Black-White range markers (green)
        black_x = self._freq_to_x(self.FREQ_BLACK, width)
        white_x = self._freq_to_x(self.FREQ_WHITE, width)
        painter.fillRect(black_x - 1, 10, 2, height - 26, self._range_marker_color)
        painter.fillRect(white_x - 1, 10, 2, height - 26, self._range_marker_color)

    def _draw_frequency_labels(self, painter, width, height):
        """Draw frequency labels."""
        painter.setPen(QColor(120, 120, 120))
        font = QFont()
        font.setPixelSize(9)
        painter.setFont(font)

        # Sync label
        sync_x = self._freq_to_x(self.FREQ_SYNC, width)
        painter.drawText(sync_x - 12, height - 10, "SY")

        # Black/White labels
        black_x = self._freq_to_x(self.FREQ_BLACK, width)
        white_x = self._freq_to_x(self.FREQ_WHITE, width)
        painter.drawText(black_x - 8, height - 10, "BL")
        painter.drawText(white_x - 8, height - 10, "WH")

    def _draw_progress_bar(self, painter, width, height):
        """Draw progress bar at bottom."""
        bar_height = 2
        bar_y = height - 4
        bar_margin = 10
        bar_width = width - 2 * bar_margin

        # Background
        painter.fillRect(bar_margin, bar_y, bar_width, bar_height, QColor(25, 25, 25))

        # Progress fill
        if self._progress > 0:
            progress_width = int(bar_width * self._progress / 100)
            gradient = QLinearGradient(bar_margin, bar_y, bar_margin + progress_width, bar_y)
            gradient.setColorAt(0, QColor(70, 130, 70))
            gradient.setColorAt(1, QColor(110, 180, 110))
            painter.fillRect(bar_margin, bar_y, progress_width, bar_height, gradient)
