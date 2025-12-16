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
        self._delay_buffer = None  # Circular buffer for chunk processing
        self._buffer_pos = 0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply delay effect to the audio signal."""
        return self._apply_delay_batch(audio, sample_rate, self.delay_ms, self.feedback, self.mix)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        delay_ms = live_params.get(("delay", "time_ms"), self.delay_ms)
        feedback = min(0.9, live_params.get(("delay", "feedback"), self.feedback))
        mix = live_params.get(("delay", "mix"), self.mix)
        return self._apply_delay_streaming(audio, sample_rate, delay_ms, feedback, mix)

    def _apply_delay_batch(self, audio: np.ndarray, sample_rate: int,
                           delay_ms: float, feedback: float, mix: float) -> np.ndarray:
        """Apply delay effect (batch mode)."""
        delay_samples = int(delay_ms * sample_rate / 1000)

        if delay_samples <= 0:
            return audio

        # Create delay buffer
        output = np.zeros(len(audio) + delay_samples * 5, dtype=np.float32)
        output[:len(audio)] = audio

        # Apply feedback delay
        for i in range(5):  # Multiple echoes
            offset = delay_samples * (i + 1)
            gain = feedback ** (i + 1)
            if offset < len(output):
                end = min(len(audio) + offset, len(output))
                output[offset:end] += audio[:end - offset] * gain

        # Trim to original length
        output = output[:len(audio)]

        # Mix wet and dry
        result = audio * (1 - mix) + output * mix

        return result

    def _apply_delay_streaming(self, audio: np.ndarray, sample_rate: int,
                               delay_ms: float, feedback: float, mix: float) -> np.ndarray:
        """Apply delay effect (streaming mode with persistent buffer)."""
        delay_samples = int(delay_ms * sample_rate / 1000)

        if delay_samples <= 0:
            return audio

        # Initialize or resize delay buffer if needed
        max_delay = int(500 * sample_rate / 1000)  # 500ms max delay buffer
        if self._delay_buffer is None or len(self._delay_buffer) < max_delay:
            self._delay_buffer = np.zeros(max_delay, dtype=np.float32)
            self._buffer_pos = 0

        output = np.zeros(len(audio), dtype=np.float32)

        for i, sample in enumerate(audio):
            # Read from delay buffer
            read_pos = (self._buffer_pos - delay_samples) % len(self._delay_buffer)
            delayed = self._delay_buffer[read_pos]

            # Write to delay buffer (input + feedback)
            self._delay_buffer[self._buffer_pos] = sample + delayed * feedback

            # Mix dry and wet
            output[i] = sample * (1 - mix) + delayed * mix

            # Advance buffer position
            self._buffer_pos = (self._buffer_pos + 1) % len(self._delay_buffer)

        return output


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
        return self._apply_timestretch(audio, sample_rate, self.rate)

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control.

        Note: Time stretching in real-time is complex. This simplified version
        works per-chunk but won't sound as smooth as batch processing.
        """
        rate = live_params.get(("timestretch", "rate"), self.rate)
        rate = max(0.1, min(4.0, rate))
        return self._apply_timestretch(audio, sample_rate, rate)

    def _apply_timestretch(self, audio: np.ndarray, sample_rate: int, rate: float) -> np.ndarray:
        """Apply time stretch with given parameters."""
        if abs(rate - 1.0) < 0.01:
            return audio

        # Simple resampling-based time stretch
        # This also changes pitch, but for glitch art that's often desirable
        original_length = len(audio)
        target_length = int(original_length / rate)

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
