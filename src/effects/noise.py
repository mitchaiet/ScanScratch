"""Noise injection effects."""

import numpy as np
from scipy import signal as sig


class NoiseEffect:
    """Add noise to audio signal."""

    def __init__(self, amount: float = 0.2, noise_type: str = "white"):
        """
        Initialize noise effect.

        Args:
            amount: Noise level (0.0 to 1.0)
            noise_type: Type of noise ("white", "pink", "gaussian", "crackle")
        """
        self.amount = amount
        self.noise_type = noise_type

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Add noise to the audio signal."""
        noise = self._generate_noise(len(audio), sample_rate)
        return audio + noise * self.amount

    def process_chunk(self, audio: np.ndarray, sample_rate: int, live_params: dict) -> np.ndarray:
        """Process a chunk with live parameters for real-time control."""
        amount = live_params.get(("noise", "amount"), self.amount)
        noise = self._generate_noise(len(audio), sample_rate)
        return audio + noise * amount

    def _generate_noise(self, length: int, sample_rate: int) -> np.ndarray:
        """Generate noise of the specified type."""
        if self.noise_type == "white":
            return self._white_noise(length)
        elif self.noise_type == "pink":
            return self._pink_noise(length)
        elif self.noise_type == "gaussian":
            return self._gaussian_noise(length)
        elif self.noise_type == "crackle":
            return self._crackle_noise(length, sample_rate)
        else:
            return self._white_noise(length)

    def _white_noise(self, length: int) -> np.ndarray:
        """Generate white noise."""
        return np.random.uniform(-1, 1, length).astype(np.float32)

    def _pink_noise(self, length: int) -> np.ndarray:
        """Generate pink (1/f) noise using the Voss-McCartney algorithm."""
        # Number of octaves
        num_octaves = 16

        # Initialize random generators for each octave
        values = np.zeros((num_octaves, length), dtype=np.float32)

        for i in range(num_octaves):
            # Each octave updates at half the rate of the previous
            step = 2 ** i
            for j in range(0, length, step):
                value = np.random.uniform(-1, 1)
                end = min(j + step, length)
                values[i, j:end] = value

        # Sum all octaves
        pink = values.sum(axis=0)

        # Normalize
        pink = pink / np.abs(pink).max()

        return pink

    def _gaussian_noise(self, length: int) -> np.ndarray:
        """Generate Gaussian (normal) noise."""
        noise = np.random.normal(0, 0.3, length).astype(np.float32)
        return np.clip(noise, -1, 1)

    def _crackle_noise(self, length: int, sample_rate: int) -> np.ndarray:
        """Generate crackle/pop noise like vinyl records."""
        noise = np.zeros(length, dtype=np.float32)

        # Random pops
        num_pops = int(length / sample_rate * 50)  # ~50 pops per second
        pop_positions = np.random.randint(0, length, num_pops)

        for pos in pop_positions:
            # Short decay envelope
            pop_length = np.random.randint(10, 100)
            if pos + pop_length < length:
                amplitude = np.random.uniform(0.3, 1.0)
                decay = np.exp(-np.linspace(0, 5, pop_length))
                noise[pos:pos + pop_length] += amplitude * decay * np.random.choice([-1, 1])

        # Add some underlying hiss
        noise += np.random.uniform(-0.05, 0.05, length)

        return np.clip(noise, -1, 1)
