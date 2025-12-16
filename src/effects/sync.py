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
        self._time_offset = 0.0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply sync wobble by modulating the signal."""
        return self._apply_wobble(audio, sample_rate, self.amount, self.frequency)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        amount = live_params.get(("syncwobble", "amount"), self.amount)
        frequency = live_params.get(("syncwobble", "freq"), self.frequency)
        return self._apply_wobble(audio, sample_rate, amount, frequency)

    def _apply_wobble(self, audio: np.ndarray, sample_rate: int, amount: float, frequency: float) -> np.ndarray:
        """Apply sync wobble with given parameters."""
        if amount == 0:
            return audio

        # Create time array with offset for continuity
        t = (np.arange(len(audio)) / sample_rate) + self._time_offset
        self._time_offset += len(audio) / sample_rate

        # Generate wobble modulation (LFO)
        wobble = np.sin(2 * np.pi * frequency * t)

        # Add random jitter for more chaos
        jitter = np.random.uniform(-0.3, 0.3, len(audio))

        # Combine smooth wobble with jitter
        modulation = wobble * 0.7 + jitter * 0.3

        # Apply as amplitude modulation with offset
        mod_signal = 1 + (modulation * amount * 0.15)

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
        return self._apply_dropout(audio, sample_rate, self.probability, self.duration_ms)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        probability = live_params.get(("syncdropout", "prob"), self.probability)
        duration_ms = live_params.get(("syncdropout", "duration"), self.duration_ms)
        return self._apply_dropout(audio, sample_rate, probability, duration_ms)

    def _apply_dropout(self, audio: np.ndarray, sample_rate: int, probability: float, duration_ms: float) -> np.ndarray:
        """Apply sync dropout with given parameters."""
        if probability == 0:
            return audio

        result = audio.copy()

        # Calculate dropout parameters
        dropout_samples = int(duration_ms * sample_rate / 1000)
        check_interval = int(sample_rate * 0.05)  # Check every 50ms

        # Random dropouts
        for i in range(0, len(audio), check_interval):
            if np.random.random() < probability * 0.05:
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
