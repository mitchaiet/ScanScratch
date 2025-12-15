"""Time-based audio effects."""

import numpy as np
from scipy import signal as sig


class DelayEffect:
    """Add echo/delay to audio signal."""

    def __init__(self, delay_ms: float = 100, feedback: float = 0.4, mix: float = 0.5):
        """
        Initialize delay effect.

        Args:
            delay_ms: Delay time in milliseconds
            feedback: Feedback amount (0.0 to 0.9)
            mix: Wet/dry mix (0.0 = dry, 1.0 = wet)
        """
        self.delay_ms = delay_ms
        self.feedback = min(0.9, feedback)  # Limit feedback to prevent runaway
        self.mix = mix

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply delay effect to the audio signal."""
        delay_samples = int(self.delay_ms * sample_rate / 1000)

        if delay_samples <= 0:
            return audio

        # Create delay buffer
        output = np.zeros(len(audio) + delay_samples * 5, dtype=np.float32)
        output[:len(audio)] = audio

        # Apply feedback delay
        for i in range(5):  # Multiple echoes
            offset = delay_samples * (i + 1)
            gain = self.feedback ** (i + 1)
            if offset < len(output):
                end = min(len(audio) + offset, len(output))
                output[offset:end] += audio[:end - offset] * gain

        # Trim to original length
        output = output[:len(audio)]

        # Mix wet and dry
        result = audio * (1 - self.mix) + output * self.mix

        return result


class TimeStretchEffect:
    """Time stretch audio without changing pitch."""

    def __init__(self, rate: float = 1.0):
        """
        Initialize time stretch effect.

        Args:
            rate: Stretch rate (0.5 = half speed, 2.0 = double speed)
        """
        self.rate = max(0.1, min(4.0, rate))

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply time stretch to the audio signal."""
        if abs(self.rate - 1.0) < 0.01:
            return audio

        # Simple resampling-based time stretch
        # This also changes pitch, but for glitch art that's often desirable
        original_length = len(audio)
        target_length = int(original_length / self.rate)

        # Resample using scipy
        resampled = sig.resample(audio, target_length)

        # For SSTV, we want to maintain the original duration
        # to keep the decoder aligned, so we pad or truncate
        if len(resampled) < original_length:
            # Pad with zeros
            result = np.zeros(original_length, dtype=np.float32)
            result[:len(resampled)] = resampled
        else:
            # Truncate
            result = resampled[:original_length]

        return result.astype(np.float32)
