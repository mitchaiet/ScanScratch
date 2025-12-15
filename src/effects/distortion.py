"""Distortion and bitcrushing effects."""

import numpy as np
from scipy import signal as sig


class DistortionEffect:
    """Apply distortion/overdrive to audio signal."""

    def __init__(self, drive: float = 0.3, clip: float = 0.8):
        """
        Initialize distortion effect.

        Args:
            drive: Amount of gain/drive (0.0 to 1.0)
            clip: Clipping threshold (0.0 to 1.0)
        """
        self.drive = drive
        self.clip = clip

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply distortion to the audio signal."""
        # Apply gain
        gain = 1 + self.drive * 10
        driven = audio * gain

        # Soft clipping using tanh
        threshold = 0.1 + self.clip * 0.9
        clipped = np.tanh(driven / threshold) * threshold

        # Mix between clean and distorted based on drive
        result = audio * (1 - self.drive) + clipped * self.drive

        return result


class BitcrushEffect:
    """Reduce bit depth and sample rate for lo-fi effect."""

    def __init__(self, bits: int = 8, target_rate: int = 22050):
        """
        Initialize bitcrush effect.

        Args:
            bits: Target bit depth (1 to 16)
            target_rate: Target sample rate in Hz
        """
        self.bits = max(1, min(16, bits))
        self.target_rate = target_rate

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply bit crushing to the audio signal."""
        result = audio.copy()

        # Sample rate reduction
        if self.target_rate < sample_rate:
            # Calculate decimation factor
            factor = sample_rate / self.target_rate
            factor = max(1, int(factor))

            # Downsample and upsample (creates stepping effect)
            downsampled = result[::factor]
            result = np.repeat(downsampled, factor)[:len(audio)]

            # Pad if needed
            if len(result) < len(audio):
                result = np.pad(result, (0, len(audio) - len(result)), mode='edge')

        # Bit depth reduction
        levels = 2 ** self.bits
        # Quantize to discrete levels
        result = np.round(result * (levels / 2)) / (levels / 2)

        return result
