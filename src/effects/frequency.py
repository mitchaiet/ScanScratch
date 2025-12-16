"""Frequency-based audio effects."""

import numpy as np
from scipy import signal as sig


class FrequencyShiftEffect:
    """Shift all frequencies by a fixed amount."""

    def __init__(self, shift_hz: float = 0):
        """
        Initialize frequency shift effect.

        Args:
            shift_hz: Amount to shift frequencies in Hz (can be negative)
        """
        self.shift_hz = shift_hz
        self._phase = 0.0  # Track phase for chunk processing

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply frequency shift to the audio signal."""
        return self._apply_shift(audio, sample_rate, self.shift_hz)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        shift_hz = live_params.get(("freqshift", "hz"), self.shift_hz)
        return self._apply_shift(audio, sample_rate, shift_hz)

    def _apply_shift(self, audio: np.ndarray, sample_rate: int, shift_hz: float) -> np.ndarray:
        """Apply frequency shift with given parameters."""
        if shift_hz == 0:
            return audio

        # Use single-sideband modulation for frequency shifting
        # Create analytic signal using Hilbert transform
        analytic = sig.hilbert(audio)

        # Create complex exponential for frequency shift
        t = np.arange(len(audio)) / sample_rate
        shift = np.exp(2j * np.pi * shift_hz * t + 1j * self._phase)

        # Update phase for next chunk
        self._phase = (self._phase + 2 * np.pi * shift_hz * len(audio) / sample_rate) % (2 * np.pi)

        # Apply shift and take real part
        shifted = np.real(analytic * shift)

        return shifted.astype(np.float32)


class BandpassEffect:
    """Apply bandpass filter to audio."""

    def __init__(self, low_cut: float = 300, high_cut: float = 3000):
        """
        Initialize bandpass filter effect.

        Args:
            low_cut: Low frequency cutoff in Hz
            high_cut: High frequency cutoff in Hz
        """
        self.low_cut = low_cut
        self.high_cut = high_cut
        self._zi = None  # Filter state for chunk processing
        self._last_b = None
        self._last_a = None

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply bandpass filter to the audio signal."""
        return self._apply_bandpass(audio, sample_rate, self.low_cut, self.high_cut)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        low_cut = live_params.get(("bandpass", "low"), self.low_cut)
        high_cut = live_params.get(("bandpass", "high"), self.high_cut)
        return self._apply_bandpass_streaming(audio, sample_rate, low_cut, high_cut)

    def _apply_bandpass(self, audio: np.ndarray, sample_rate: int, low_cut: float, high_cut: float) -> np.ndarray:
        """Apply bandpass filter with given parameters (batch mode)."""
        nyq = sample_rate / 2

        # Clamp frequencies to valid range
        low = max(20, min(low_cut, nyq - 100)) / nyq
        high = max(low + 0.01, min(high_cut, nyq - 10)) / nyq

        # Ensure low < high
        if low >= high:
            high = min(low + 0.1, 0.99)

        # Design butterworth bandpass filter
        try:
            b, a = sig.butter(4, [low, high], btype='band')
            filtered = sig.filtfilt(b, a, audio)
            return filtered.astype(np.float32)
        except Exception:
            return audio

    def _apply_bandpass_streaming(self, audio: np.ndarray, sample_rate: int, low_cut: float, high_cut: float) -> np.ndarray:
        """Apply bandpass filter for streaming (maintains state between chunks)."""
        nyq = sample_rate / 2

        # Clamp frequencies to valid range
        low = max(20, min(low_cut, nyq - 100)) / nyq
        high = max(low + 0.01, min(high_cut, nyq - 10)) / nyq

        if low >= high:
            high = min(low + 0.1, 0.99)

        try:
            b, a = sig.butter(4, [low, high], btype='band')

            # Reset filter state if coefficients changed
            if self._last_b is None or not np.array_equal(b, self._last_b):
                self._zi = sig.lfilter_zi(b, a) * audio[0]
                self._last_b = b
                self._last_a = a

            # Apply filter with state
            filtered, self._zi = sig.lfilter(b, a, audio, zi=self._zi)
            return filtered.astype(np.float32)
        except Exception:
            return audio
