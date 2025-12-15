"""Sync and timing corruption effects."""

import numpy as np


class SyncWobbleEffect:
    """Corrupt sync signals causing scanline displacement."""

    def __init__(self, amount: float = 0.5, frequency: float = 5.0):
        """
        Initialize sync wobble effect.

        Args:
            amount: Wobble intensity (0.0 to 1.0)
            frequency: Wobble frequency in Hz
        """
        self.amount = amount
        self.frequency = frequency

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply sync wobble by modulating the signal."""
        if self.amount == 0:
            return audio

        # Create time array
        t = np.arange(len(audio)) / sample_rate

        # Generate wobble modulation (LFO)
        wobble = np.sin(2 * np.pi * self.frequency * t)

        # Add random jitter for more chaos
        jitter = np.random.uniform(-0.3, 0.3, len(audio))

        # Combine smooth wobble with jitter
        modulation = wobble * 0.7 + jitter * 0.3

        # Apply as amplitude modulation with offset
        # This creates timing shifts that corrupt SSTV sync
        mod_signal = 1 + (modulation * self.amount * 0.15)

        result = audio * mod_signal

        return result.astype(np.float32)


class SyncDropoutEffect:
    """Randomly drop sync pulses causing line misalignment."""

    def __init__(self, probability: float = 0.1, duration_ms: float = 5.0):
        """
        Initialize sync dropout effect.

        Args:
            probability: Chance of dropout per second (0.0 to 1.0)
            duration_ms: Duration of each dropout in milliseconds
        """
        self.probability = probability
        self.duration_ms = duration_ms

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply random sync dropouts."""
        if self.probability == 0:
            return audio

        result = audio.copy()

        # Calculate dropout parameters
        dropout_samples = int(self.duration_ms * sample_rate / 1000)
        check_interval = int(sample_rate * 0.05)  # Check every 50ms

        # Random dropouts
        for i in range(0, len(audio), check_interval):
            if np.random.random() < self.probability * 0.05:
                # Create a dropout
                end = min(i + dropout_samples, len(audio))

                # Fade out/in for smoother glitch
                fade_len = min(dropout_samples // 4, 20)
                if fade_len > 0 and i + fade_len < len(audio):
                    result[i:i + fade_len] *= np.linspace(1, 0, fade_len)

                # Zero or heavily attenuate
                result[i + fade_len:end - fade_len] *= 0.1

                if end - fade_len > 0 and end - fade_len < len(audio):
                    result[end - fade_len:end] *= np.linspace(0, 1, fade_len)

        return result.astype(np.float32)
