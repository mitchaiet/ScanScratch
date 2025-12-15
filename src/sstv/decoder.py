"""SSTV decoder implementation using scipy signal processing."""

import numpy as np
from scipy import signal
from scipy.ndimage import median_filter
from PIL import Image


# SSTV frequency constants
FREQ_SYNC = 1200      # Sync pulse frequency (Hz)
FREQ_BLACK = 1500     # Black level frequency (Hz)
FREQ_WHITE = 2300     # White level frequency (Hz)
FREQ_VIS_START = 1900 # VIS code start
FREQ_VIS_BIT1 = 1100  # VIS bit 1
FREQ_VIS_BIT0 = 1300  # VIS bit 0

# Mode timing specifications (in seconds)
MODE_SPECS = {
    "MartinM1": {
        "width": 320,
        "height": 256,
        "scan_time": 0.146432,      # Time per color channel scan
        "sync_pulse": 0.004862,     # Sync pulse duration
        "sync_porch": 0.000572,     # Sync porch duration
        "separator": 0.000572,      # Separator between color channels
        "color_order": "GBR",       # Green, Blue, Red
    },
    "MartinM2": {
        "width": 320,
        "height": 256,
        "scan_time": 0.073216,
        "sync_pulse": 0.004862,
        "sync_porch": 0.000572,
        "separator": 0.000572,
        "color_order": "GBR",
    },
    "ScottieS1": {
        "width": 320,
        "height": 256,
        "scan_time": 0.138240,
        "sync_pulse": 0.009000,
        "sync_porch": 0.001500,
        "separator": 0.001500,
        "color_order": "GBR",
    },
    "ScottieS2": {
        "width": 320,
        "height": 256,
        "scan_time": 0.088064,
        "sync_pulse": 0.009000,
        "sync_porch": 0.001500,
        "separator": 0.001500,
        "color_order": "GBR",
    },
    "Robot36": {
        "width": 320,
        "height": 240,
        "scan_time": 0.088000,
        "sync_pulse": 0.009000,
        "sync_porch": 0.003000,
        "separator": 0.004500,
        "color_order": "YCrCb",  # Different color space
    },
    "PD90": {
        "width": 320,
        "height": 256,
        "scan_time": 0.170240,
        "sync_pulse": 0.020000,
        "sync_porch": 0.002080,
        "separator": 0.000000,
        "color_order": "RGB",
    },
}


class SSTVDecoder:
    """Decodes SSTV audio signals back to images."""

    def __init__(self):
        pass

    def decode(
        self,
        audio: np.ndarray,
        sample_rate: int,
        mode: str = "MartinM1"
    ) -> Image.Image:
        """
        Decode SSTV audio to an image.

        Args:
            audio: Audio data as numpy float array (-1 to 1)
            sample_rate: Sample rate of the audio
            mode: SSTV mode name

        Returns:
            Decoded PIL Image
        """
        if mode not in MODE_SPECS:
            raise ValueError(f"Unknown SSTV mode: {mode}")

        spec = MODE_SPECS[mode]
        width = spec["width"]
        height = spec["height"]

        # Demodulate FM to get instantaneous frequency
        freq = self._demodulate_fm(audio, sample_rate)

        # Find sync pulses to locate scanlines
        sync_positions = self._find_sync_pulses(freq, sample_rate, spec)

        # If we can't find syncs, try a simpler approach
        if len(sync_positions) < height // 2:
            return self._decode_simple(freq, sample_rate, spec)

        # Extract and decode each scanline
        image = self._extract_scanlines(freq, sample_rate, spec, sync_positions)

        return image

    def _demodulate_fm(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Demodulate FM signal to get instantaneous frequency.

        Uses the analytic signal (Hilbert transform) approach.
        """
        # Apply bandpass filter to isolate SSTV frequencies (1100-2500 Hz)
        nyq = sample_rate / 2
        low = 1000 / nyq
        high = 2500 / nyq

        # Design butterworth bandpass filter
        b, a = signal.butter(4, [low, high], btype='band')
        filtered = signal.filtfilt(b, a, audio)

        # Compute analytic signal using Hilbert transform
        analytic = signal.hilbert(filtered)

        # Instantaneous phase
        phase = np.unwrap(np.angle(analytic))

        # Instantaneous frequency (derivative of phase)
        freq = np.diff(phase) * sample_rate / (2 * np.pi)

        # Pad to maintain length
        freq = np.append(freq, freq[-1])

        # Apply light smoothing
        window_size = max(1, int(sample_rate / 8000))
        if window_size > 1:
            freq = np.convolve(freq, np.ones(window_size)/window_size, mode='same')

        return freq

    def _find_sync_pulses(
        self,
        freq: np.ndarray,
        sample_rate: int,
        spec: dict
    ) -> np.ndarray:
        """Find sync pulse positions in the frequency data."""
        # Sync pulses are at ~1200 Hz
        sync_freq = FREQ_SYNC
        tolerance = 100  # Hz

        # Create a mask for sync-frequency samples
        sync_mask = np.abs(freq - sync_freq) < tolerance

        # Expected sync pulse length in samples
        sync_samples = int(spec["sync_pulse"] * sample_rate)

        # Find runs of sync frequency
        # Use morphological operations to find sustained sync pulses
        kernel_size = max(1, sync_samples // 2)
        sync_filtered = signal.medfilt(sync_mask.astype(float), kernel_size)

        # Find rising edges (start of sync pulses)
        sync_diff = np.diff(sync_filtered)
        sync_starts = np.where(sync_diff > 0.5)[0]

        return sync_starts

    def _decode_simple(
        self,
        freq: np.ndarray,
        sample_rate: int,
        spec: dict
    ) -> Image.Image:
        """
        Simple decoding without sync detection.

        Assumes the audio starts at the beginning of image data
        and extracts based on timing alone.
        """
        width = spec["width"]
        height = spec["height"]

        # Calculate line timing
        scan_time = spec["scan_time"]
        sync_time = spec["sync_pulse"] + spec["sync_porch"]
        sep_time = spec["separator"]

        # Line time depends on mode
        if spec["color_order"] in ("GBR", "RGB"):
            # Martin/Scottie/PD: sync + 3 color channels with separators
            line_time = sync_time + 3 * scan_time + 2 * sep_time
        else:
            # Robot: different structure
            line_time = sync_time + scan_time * 2

        line_samples = int(line_time * sample_rate)
        scan_samples = int(scan_time * sample_rate)
        sync_samples = int(sync_time * sample_rate)
        sep_samples = int(sep_time * sample_rate)

        # Skip header/VIS code - look for start of image data
        # Find first significant sync-like pulse
        start_offset = self._find_image_start(freq, sample_rate)

        # Create output image
        image_data = np.zeros((height, width, 3), dtype=np.uint8)

        for line in range(height):
            line_start = start_offset + line * line_samples

            if line_start + line_samples > len(freq):
                break

            # Extract color channels based on mode
            if spec["color_order"] == "GBR":
                # Green channel first
                g_start = line_start + sync_samples
                g_end = g_start + scan_samples
                green = self._extract_channel(freq[g_start:g_end], width)

                # Blue channel
                b_start = g_end + sep_samples
                b_end = b_start + scan_samples
                blue = self._extract_channel(freq[b_start:b_end], width)

                # Red channel
                r_start = b_end + sep_samples
                r_end = r_start + scan_samples
                red = self._extract_channel(freq[r_start:r_end], width)

                image_data[line, :, 0] = red
                image_data[line, :, 1] = green
                image_data[line, :, 2] = blue

            elif spec["color_order"] == "RGB":
                # Red channel first (PD modes)
                r_start = line_start + sync_samples
                r_end = r_start + scan_samples
                red = self._extract_channel(freq[r_start:r_end], width)

                # Green channel
                g_start = r_end + sep_samples
                g_end = g_start + scan_samples
                green = self._extract_channel(freq[g_start:g_end], width)

                # Blue channel
                b_start = g_end + sep_samples
                b_end = b_start + scan_samples
                blue = self._extract_channel(freq[b_start:b_end], width)

                image_data[line, :, 0] = red
                image_data[line, :, 1] = green
                image_data[line, :, 2] = blue

            else:
                # Robot mode (YCrCb) - simplified handling
                y_start = line_start + sync_samples
                y_end = y_start + scan_samples
                luma = self._extract_channel(freq[y_start:y_end], width)

                # Use luma as grayscale for now
                image_data[line, :, 0] = luma
                image_data[line, :, 1] = luma
                image_data[line, :, 2] = luma

        return Image.fromarray(image_data, mode='RGB')

    def _find_image_start(self, freq: np.ndarray, sample_rate: int) -> int:
        """Find the start of image data after header/VIS code."""
        # Look for the characteristic pattern: header tone followed by VIS code
        # Then image data starts

        # VIS code is about 300ms, header is about 300ms
        # Skip first ~1 second to be safe
        skip_samples = int(0.5 * sample_rate)

        # Find first sync pulse after skip
        sync_mask = np.abs(freq[skip_samples:] - FREQ_SYNC) < 150
        sync_indices = np.where(sync_mask)[0]

        if len(sync_indices) > 0:
            return skip_samples + sync_indices[0]

        return skip_samples

    def _extract_channel(self, freq_segment: np.ndarray, width: int) -> np.ndarray:
        """Extract a color channel from frequency data."""
        if len(freq_segment) == 0:
            return np.zeros(width, dtype=np.uint8)

        # Resample to image width
        indices = np.linspace(0, len(freq_segment) - 1, width).astype(int)
        resampled = freq_segment[indices]

        # Map frequency to intensity
        # 1500 Hz = black (0), 2300 Hz = white (255)
        intensity = (resampled - FREQ_BLACK) / (FREQ_WHITE - FREQ_BLACK)
        intensity = np.clip(intensity * 255, 0, 255).astype(np.uint8)

        return intensity

    def _extract_scanlines(
        self,
        freq: np.ndarray,
        sample_rate: int,
        spec: dict,
        sync_positions: np.ndarray
    ) -> Image.Image:
        """Extract scanlines using detected sync positions."""
        width = spec["width"]
        height = spec["height"]
        scan_samples = int(spec["scan_time"] * sample_rate)
        sync_samples = int((spec["sync_pulse"] + spec["sync_porch"]) * sample_rate)
        sep_samples = int(spec["separator"] * sample_rate)

        image_data = np.zeros((height, width, 3), dtype=np.uint8)

        for i, sync_pos in enumerate(sync_positions[:height]):
            if spec["color_order"] == "GBR":
                # Green channel first
                g_start = sync_pos + sync_samples
                g_end = g_start + scan_samples
                if g_end <= len(freq):
                    green = self._extract_channel(freq[g_start:g_end], width)
                else:
                    green = np.zeros(width, dtype=np.uint8)

                # Blue channel
                b_start = g_end + sep_samples
                b_end = b_start + scan_samples
                if b_end <= len(freq):
                    blue = self._extract_channel(freq[b_start:b_end], width)
                else:
                    blue = np.zeros(width, dtype=np.uint8)

                # Red channel
                r_start = b_end + sep_samples
                r_end = r_start + scan_samples
                if r_end <= len(freq):
                    red = self._extract_channel(freq[r_start:r_end], width)
                else:
                    red = np.zeros(width, dtype=np.uint8)

                image_data[i, :, 0] = red
                image_data[i, :, 1] = green
                image_data[i, :, 2] = blue

            elif spec["color_order"] == "RGB":
                # Red channel first (PD modes)
                r_start = sync_pos + sync_samples
                r_end = r_start + scan_samples
                if r_end <= len(freq):
                    red = self._extract_channel(freq[r_start:r_end], width)
                else:
                    red = np.zeros(width, dtype=np.uint8)

                # Green channel
                g_start = r_end + sep_samples
                g_end = g_start + scan_samples
                if g_end <= len(freq):
                    green = self._extract_channel(freq[g_start:g_end], width)
                else:
                    green = np.zeros(width, dtype=np.uint8)

                # Blue channel
                b_start = g_end + sep_samples
                b_end = b_start + scan_samples
                if b_end <= len(freq):
                    blue = self._extract_channel(freq[b_start:b_end], width)
                else:
                    blue = np.zeros(width, dtype=np.uint8)

                image_data[i, :, 0] = red
                image_data[i, :, 1] = green
                image_data[i, :, 2] = blue

            else:
                # Robot YCrCb - simplified
                y_start = sync_pos + sync_samples
                y_end = y_start + scan_samples
                if y_end <= len(freq):
                    luma = self._extract_channel(freq[y_start:y_end], width)
                else:
                    luma = np.zeros(width, dtype=np.uint8)

                image_data[i, :, 0] = luma
                image_data[i, :, 1] = luma
                image_data[i, :, 2] = luma

        return Image.fromarray(image_data, mode='RGB')
