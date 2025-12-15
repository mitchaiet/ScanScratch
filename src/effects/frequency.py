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

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply frequency shift to the audio signal."""
        if self.shift_hz == 0:
            return audio

        # Use single-sideband modulation for frequency shifting
        # Create analytic signal using Hilbert transform
        analytic = sig.hilbert(audio)

        # Create complex exponential for frequency shift
        t = np.arange(len(audio)) / sample_rate
        shift = np.exp(2j * np.pi * self.shift_hz * t)

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

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply bandpass filter to the audio signal."""
        nyq = sample_rate / 2

        # Clamp frequencies to valid range
        low = max(20, min(self.low_cut, nyq - 100)) / nyq
        high = max(low + 0.01, min(self.high_cut, nyq - 10)) / nyq

        # Ensure low < high
        if low >= high:
            high = min(low + 0.1, 0.99)

        # Design butterworth bandpass filter
        try:
            b, a = sig.butter(4, [low, high], btype='band')
            filtered = sig.filtfilt(b, a, audio)
            return filtered.astype(np.float32)
        except Exception:
            # If filter design fails, return unmodified audio
            return audio
