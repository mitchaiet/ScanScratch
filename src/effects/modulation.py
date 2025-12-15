"""Modulation effects for dramatic visual corruption."""

import numpy as np


class PhaseModulationEffect:
    """Phase modulation creates horizontal scanline displacement."""

    def __init__(self, depth: float = 0.5, rate: float = 8.0):
        """
        Initialize phase modulation effect.

        Args:
            depth: Modulation depth (0.0 to 1.0) - how far to shift
            rate: Modulation rate in Hz - how fast to modulate
        """
        self.depth = depth
        self.rate = rate

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply phase modulation to the audio signal."""
        if self.depth == 0:
            return audio

        # Create modulation signal (sine wave LFO)
        t = np.arange(len(audio)) / sample_rate
        modulation = np.sin(2 * np.pi * self.rate * t)

        # Add random chaos for more interesting patterns
        chaos = np.random.uniform(-0.3, 0.3, len(audio))
        smoothed_chaos = np.convolve(chaos, np.ones(100)/100, mode='same')

        # Combine smooth and chaotic modulation
        combined_mod = modulation * 0.7 + smoothed_chaos * 0.3

        # Create time-varying delay (phase shift)
        # This shifts samples left/right creating horizontal scanline displacement
        max_shift_samples = int(sample_rate * 0.01 * self.depth)  # Up to 10ms shift

        result = audio.copy()
        shift = (combined_mod * max_shift_samples).astype(int)

        for i in range(len(audio)):
            source_idx = i - shift[i]
            if 0 <= source_idx < len(audio):
                result[i] = audio[source_idx]

        return result.astype(np.float32)


class AmplitudeModulationEffect:
    """Amplitude modulation creates brightness/color intensity chaos."""

    def __init__(self, depth: float = 0.5, rate: float = 12.0):
        """
        Initialize amplitude modulation effect.

        Args:
            depth: Modulation depth (0.0 to 1.0)
            rate: Modulation rate in Hz
        """
        self.depth = depth
        self.rate = rate

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply amplitude modulation to the audio signal."""
        if self.depth == 0:
            return audio

        # Create complex modulation pattern
        t = np.arange(len(audio)) / sample_rate

        # Multiple sine waves at different rates for complexity
        mod1 = np.sin(2 * np.pi * self.rate * t)
        mod2 = np.sin(2 * np.pi * (self.rate * 1.618) * t)  # Golden ratio for inharmonic
        mod3 = np.sin(2 * np.pi * (self.rate * 0.5) * t)

        # Combine modulations
        modulation = (mod1 * 0.5 + mod2 * 0.3 + mod3 * 0.2)

        # Scale modulation depth (keep some base level to avoid complete silence)
        amplitude = 1.0 + modulation * self.depth

        # Apply amplitude modulation
        result = audio * amplitude

        return result.astype(np.float32)


class HarmonicDistortionEffect:
    """Add harmonic overtones that corrupt SSTV color decoding."""

    def __init__(self, amount: float = 0.5, harmonics: int = 3):
        """
        Initialize harmonic distortion effect.

        Args:
            amount: Amount of harmonics to add (0.0 to 1.0)
            harmonics: Number of harmonic overtones to generate (1-5)
        """
        self.amount = amount
        self.harmonics = min(5, max(1, harmonics))

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply harmonic distortion to the audio signal."""
        if self.amount == 0:
            return audio

        # Start with original signal
        result = audio.copy()

        # Add harmonic overtones
        # This creates frequency components that corrupt the SSTV decoder
        for h in range(1, self.harmonics + 1):
            # Create harmonic by ring modulation
            t = np.arange(len(audio)) / sample_rate

            # Use a frequency that creates visible artifacts in SSTV
            # SSTV uses 1500-2300 Hz, so harmonics around 3-7 kHz will corrupt it
            carrier_freq = 1800 * (h + 1)  # 3600, 5400, 7200, etc.
            carrier = np.sin(2 * np.pi * carrier_freq * t)

            # Ring modulate
            harmonic = audio * carrier

            # Add with decreasing amplitude
            harmonic_amount = self.amount / (h + 1)
            result += harmonic * harmonic_amount

        return result.astype(np.float32)


class ScanlineCorruptionEffect:
    """Corrupt specific scanlines with various artifacts."""

    def __init__(self, frequency: float = 0.15, intensity: float = 0.7):
        """
        Initialize scanline corruption effect.

        Args:
            frequency: How often to corrupt (0.0 to 1.0)
            intensity: How severe the corruption (0.0 to 1.0)
        """
        self.frequency = frequency
        self.intensity = intensity

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply random scanline corruption."""
        if self.frequency == 0:
            return audio

        result = audio.copy()

        # Estimate scanline duration (rough approximation)
        # Martin M1 has ~446ms per line, so ~20 lines per second
        estimated_lines_per_sec = 20
        samples_per_line = int(sample_rate / estimated_lines_per_sec)

        # Randomly corrupt scanlines
        for i in range(0, len(audio), samples_per_line):
            if np.random.random() < self.frequency:
                end = min(i + samples_per_line, len(audio))

                # Choose a random corruption type
                corruption_type = np.random.randint(0, 4)

                if corruption_type == 0:
                    # Invert phase
                    result[i:end] *= -1 * self.intensity

                elif corruption_type == 1:
                    # Add frequency spike
                    t = np.arange(end - i) / sample_rate
                    spike_freq = np.random.uniform(1800, 2200)
                    spike = np.sin(2 * np.pi * spike_freq * t) * self.intensity
                    result[i:end] += spike

                elif corruption_type == 2:
                    # Reduce to near-silence (creates black bars)
                    result[i:end] *= (1 - self.intensity * 0.9)

                else:
                    # Add random noise burst
                    noise = np.random.uniform(-1, 1, end - i) * self.intensity * 0.5
                    result[i:end] += noise

        return result.astype(np.float32)
