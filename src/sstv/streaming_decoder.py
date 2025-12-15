"""Streaming SSTV decoder for line-by-line progressive decoding."""

import numpy as np
from scipy import signal
from PIL import Image
from typing import Generator


# SSTV frequency constants (must match pysstv)
FREQ_SYNC = 1200
FREQ_BLACK = 1500
FREQ_WHITE = 2300

# Header timing (VIS code) - same for all modes
# 300ms + 10ms + 300ms + 10*30ms = 910ms
HEADER_MS = 910.0

# Mode specifications - must match pysstv exactly
MODE_SPECS = {
    "MartinM1": {
        "width": 320,
        "height": 256,
        "sync_ms": 4.862,
        "scan_ms": 146.432,     # per color channel
        "gap_ms": 0.572,        # INTER_CH_GAP
        "color_order": "GBR",
    },
    "MartinM2": {
        "width": 160,           # Note: M2 is half width!
        "height": 256,
        "sync_ms": 4.862,
        "scan_ms": 73.216,
        "gap_ms": 0.572,
        "color_order": "GBR",
    },
    "ScottieS1": {
        "width": 320,
        "height": 256,
        "sync_ms": 9.0,
        "scan_ms": 136.74,
        "gap_ms": 1.5,
        "color_order": "GBR",
        "sync_at_end": True,    # Scottie has sync after red, not at start
    },
    "ScottieS2": {
        "width": 160,
        "height": 256,
        "sync_ms": 9.0,
        "scan_ms": 86.564,
        "gap_ms": 1.5,
        "color_order": "GBR",
        "sync_at_end": True,
    },
    "Robot36": {
        "width": 320,
        "height": 240,
        "sync_ms": 9.0,
        "scan_ms": 88.0,
        "gap_ms": 4.5,
        "color_order": "YCrCb",
    },
    "PD90": {
        "width": 320,
        "height": 256,
        "sync_ms": 20.0,
        "scan_ms": 170.240,
        "gap_ms": 2.08,
        "color_order": "RGB",
    },
}


class StreamingDecoder:
    """Decodes SSTV audio progressively, yielding each line as it's decoded."""

    def __init__(self, sample_rate: int, mode: str = "MartinM1"):
        if mode not in MODE_SPECS:
            raise ValueError(f"Unknown SSTV mode: {mode}")

        self.sample_rate = sample_rate
        self.mode = mode
        self.spec = MODE_SPECS[mode]
        self.width = self.spec["width"]
        self.height = self.spec["height"]

        # Calculate timing in samples (keep as float for precision)
        ms_to_samples = sample_rate / 1000.0

        self.sync_samples = self.spec["sync_ms"] * ms_to_samples
        self.scan_samples = self.spec["scan_ms"] * ms_to_samples
        self.gap_samples = self.spec["gap_ms"] * ms_to_samples
        self.header_samples = HEADER_MS * ms_to_samples

        # Line structure for Martin: sync + gap + G + gap + B + gap + R + gap
        # Total: sync + 4*gap + 3*scan
        # Keep as float to avoid accumulation of rounding errors
        self.line_samples = (
            self.sync_samples +
            4 * self.gap_samples +
            3 * self.scan_samples
        )

        # Pre-compute filter coefficients for FM demodulation
        nyq = sample_rate / 2
        low = 1000 / nyq
        high = 2500 / nyq
        self.filter_b, self.filter_a = signal.butter(4, [low, high], btype='band')

    def get_line_duration(self) -> float:
        """Get duration of one scanline in seconds."""
        return self.line_samples / self.sample_rate

    def get_header_duration(self) -> float:
        """Get duration of header in seconds."""
        return self.header_samples / self.sample_rate

    def get_total_duration(self) -> float:
        """Get total transmission duration in seconds."""
        return self.get_header_duration() + self.height * self.get_line_duration()

    def decode_progressive(
        self,
        audio: np.ndarray
    ) -> Generator[tuple[int, np.ndarray], None, None]:
        """
        Decode audio progressively, yielding (line_number, rgb_line) tuples.

        Each rgb_line is shape (width, 3) with uint8 RGB values.
        """
        # Demodulate entire signal first (needed for filtering)
        freq = self._demodulate_fm(audio)

        # Process each line
        for line_num in range(self.height):
            # Use float arithmetic and round only when indexing
            line_start = int(round(self.header_samples + line_num * self.line_samples))

            if line_start + int(round(self.line_samples)) > len(freq):
                yield line_num, np.zeros((self.width, 3), dtype=np.uint8)
                continue

            rgb_line = self._decode_line(freq, line_start)
            yield line_num, rgb_line

    def _demodulate_fm(self, audio: np.ndarray) -> np.ndarray:
        """Demodulate FM to get instantaneous frequency."""
        # Bandpass filter
        filtered = signal.filtfilt(self.filter_b, self.filter_a, audio)

        # Hilbert transform for analytic signal
        analytic = signal.hilbert(filtered)

        # Instantaneous phase and frequency
        phase = np.unwrap(np.angle(analytic))
        freq = np.diff(phase) * self.sample_rate / (2 * np.pi)
        freq = np.append(freq, freq[-1])

        # Light smoothing
        window_size = max(1, int(self.sample_rate / 8000))
        if window_size > 1:
            freq = np.convolve(freq, np.ones(window_size)/window_size, mode='same')

        return freq

    def _decode_line(self, freq: np.ndarray, line_start: int) -> np.ndarray:
        """Decode a single scanline to RGB."""
        rgb = np.zeros((self.width, 3), dtype=np.uint8)

        # Line structure for Martin modes:
        # [sync][gap][GREEN][gap][BLUE][gap][RED][gap]
        #
        # Offsets from line_start:
        # sync starts at: 0
        # gap1 starts at: sync_samples
        # green starts at: sync_samples + gap_samples
        # gap2 starts at: sync_samples + gap_samples + scan_samples
        # blue starts at: sync_samples + 2*gap_samples + scan_samples
        # gap3 starts at: sync_samples + 2*gap_samples + 2*scan_samples
        # red starts at: sync_samples + 3*gap_samples + 2*scan_samples

        # Use precise float arithmetic and round only when indexing
        green_start = int(round(line_start + self.sync_samples + self.gap_samples))
        blue_start = int(round(green_start + self.scan_samples + self.gap_samples))
        red_start = int(round(blue_start + self.scan_samples + self.gap_samples))
        scan_length = int(round(self.scan_samples))

        if self.spec["color_order"] == "GBR":
            green = self._extract_channel(freq[green_start:green_start + scan_length])
            blue = self._extract_channel(freq[blue_start:blue_start + scan_length])
            red = self._extract_channel(freq[red_start:red_start + scan_length])

            rgb[:, 0] = red
            rgb[:, 1] = green
            rgb[:, 2] = blue

        elif self.spec["color_order"] == "RGB":
            # For PD modes: R, G, B order
            red = self._extract_channel(freq[green_start:green_start + scan_length])
            green = self._extract_channel(freq[blue_start:blue_start + scan_length])
            blue = self._extract_channel(freq[red_start:red_start + scan_length])

            rgb[:, 0] = red
            rgb[:, 1] = green
            rgb[:, 2] = blue

        else:
            # YCrCb - simplified as grayscale
            luma = self._extract_channel(freq[green_start:green_start + scan_length])
            rgb[:, 0] = rgb[:, 1] = rgb[:, 2] = luma

        return rgb

    def _extract_channel(self, freq_segment: np.ndarray) -> np.ndarray:
        """Extract color channel from frequency data."""
        if len(freq_segment) == 0:
            return np.zeros(self.width, dtype=np.uint8)

        # Resample to image width
        indices = np.linspace(0, len(freq_segment) - 1, self.width).astype(int)
        resampled = freq_segment[indices]

        # Map frequency to intensity: 1500 Hz = 0 (black), 2300 Hz = 255 (white)
        intensity = (resampled - FREQ_BLACK) / (FREQ_WHITE - FREQ_BLACK)
        intensity = np.clip(intensity * 255, 0, 255).astype(np.uint8)

        return intensity
