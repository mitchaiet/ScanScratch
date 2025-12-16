"""Audio effects pipeline for processing SSTV signals."""

import numpy as np
from typing import Protocol, runtime_checkable
import queue


@runtime_checkable
class AudioEffect(Protocol):
    """Protocol for audio effects."""

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process audio and return modified audio."""
        ...


class EffectsPipeline:
    """Chain of audio effects to process SSTV signals.

    Supports both batch processing (process()) and real-time chunk processing
    (process_chunk()) with live parameter updates via update_param().
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.effects: list[AudioEffect] = []
        self.effects_by_name: dict = {}  # name -> effect instance for live updates
        self._settings: dict = {}

        # Live parameters for real-time control
        # Keys are (effect_name, param_name) tuples
        self.live_params: dict = {}

        # Thread-safe queue for parameter updates from UI thread
        self._param_queue = queue.Queue()

    def configure(self, settings: dict):
        """Configure the pipeline from settings dictionary.

        All effects are added to the pipeline regardless of enabled state,
        allowing them to be toggled on/off during real-time playback.
        The 'enabled' parameter in live_params controls whether each effect is active.
        """
        from .noise import NoiseEffect
        from .distortion import DistortionEffect, BitcrushEffect
        from .frequency import FrequencyShiftEffect, BandpassEffect
        from .time import DelayEffect, TimeStretchEffect
        from .sync import SyncWobbleEffect, SyncDropoutEffect
        from .modulation import (
            PhaseModulationEffect,
            AmplitudeModulationEffect,
            HarmonicDistortionEffect,
            ScanlineCorruptionEffect,
        )

        self._settings = settings
        self.effects = []
        self.effects_by_name = {}
        self.live_params = {}  # Reset live params

        # Add ALL effects to pipeline (enabled state is checked in process_chunk)
        # Phase/amplitude modulation first for base corruption
        effect = PhaseModulationEffect(
            depth=settings.get("phasemod_depth", 0.5),
            rate=settings.get("phasemod_rate", 8.0),
        )
        self.effects.append(effect)
        self.effects_by_name["phasemod"] = effect
        self.live_params[("phasemod", "enabled")] = settings.get("phasemod_enabled", False)
        self.live_params[("phasemod", "depth")] = settings.get("phasemod_depth", 0.5)
        self.live_params[("phasemod", "rate")] = settings.get("phasemod_rate", 8.0)

        effect = AmplitudeModulationEffect(
            depth=settings.get("ampmod_depth", 0.5),
            rate=settings.get("ampmod_rate", 12.0),
        )
        self.effects.append(effect)
        self.effects_by_name["ampmod"] = effect
        self.live_params[("ampmod", "enabled")] = settings.get("ampmod_enabled", False)
        self.live_params[("ampmod", "depth")] = settings.get("ampmod_depth", 0.5)
        self.live_params[("ampmod", "rate")] = settings.get("ampmod_rate", 12.0)

        # Sync effects for scanline corruption
        effect = SyncWobbleEffect(
            amount=settings.get("syncwobble_amount", 0.5),
            frequency=settings.get("syncwobble_freq", 5.0),
        )
        self.effects.append(effect)
        self.effects_by_name["syncwobble"] = effect
        self.live_params[("syncwobble", "enabled")] = settings.get("syncwobble_enabled", False)
        self.live_params[("syncwobble", "amount")] = settings.get("syncwobble_amount", 0.5)
        self.live_params[("syncwobble", "freq")] = settings.get("syncwobble_freq", 5.0)

        effect = SyncDropoutEffect(
            probability=settings.get("syncdropout_prob", 0.1),
            duration_ms=settings.get("syncdropout_duration", 5.0),
        )
        self.effects.append(effect)
        self.effects_by_name["syncdropout"] = effect
        self.live_params[("syncdropout", "enabled")] = settings.get("syncdropout_enabled", False)
        self.live_params[("syncdropout", "prob")] = settings.get("syncdropout_prob", 0.1)
        self.live_params[("syncdropout", "duration")] = settings.get("syncdropout_duration", 5.0)

        effect = ScanlineCorruptionEffect(
            frequency=settings.get("scanline_freq", 0.15),
            intensity=settings.get("scanline_intensity", 0.7),
        )
        self.effects.append(effect)
        self.effects_by_name["scanline"] = effect
        self.live_params[("scanline", "enabled")] = settings.get("scanline_enabled", False)
        self.live_params[("scanline", "freq")] = settings.get("scanline_freq", 0.15)
        self.live_params[("scanline", "intensity")] = settings.get("scanline_intensity", 0.7)

        effect = NoiseEffect(
            amount=settings.get("noise_amount", 0.2),
            noise_type=settings.get("noise_type", "white"),
        )
        self.effects.append(effect)
        self.effects_by_name["noise"] = effect
        self.live_params[("noise", "enabled")] = settings.get("noise_enabled", False)
        self.live_params[("noise", "amount")] = settings.get("noise_amount", 0.2)

        effect = DistortionEffect(
            drive=settings.get("distortion_drive", 0.3),
            clip=settings.get("distortion_clip", 0.8),
        )
        self.effects.append(effect)
        self.effects_by_name["distortion"] = effect
        self.live_params[("distortion", "enabled")] = settings.get("distortion_enabled", False)
        self.live_params[("distortion", "drive")] = settings.get("distortion_drive", 0.3)
        self.live_params[("distortion", "clip")] = settings.get("distortion_clip", 0.8)

        effect = HarmonicDistortionEffect(
            amount=settings.get("harmonic_amount", 0.5),
            harmonics=settings.get("harmonic_count", 3),
        )
        self.effects.append(effect)
        self.effects_by_name["harmonic"] = effect
        self.live_params[("harmonic", "enabled")] = settings.get("harmonic_enabled", False)
        self.live_params[("harmonic", "amount")] = settings.get("harmonic_amount", 0.5)

        effect = BitcrushEffect(
            bits=settings.get("bitcrush_bits", 8),
            target_rate=settings.get("bitcrush_rate", 22050),
        )
        self.effects.append(effect)
        self.effects_by_name["bitcrush"] = effect
        self.live_params[("bitcrush", "enabled")] = settings.get("bitcrush_enabled", False)
        self.live_params[("bitcrush", "bits")] = settings.get("bitcrush_bits", 8)
        self.live_params[("bitcrush", "rate")] = settings.get("bitcrush_rate", 22050)

        effect = FrequencyShiftEffect(
            shift_hz=settings.get("freqshift_hz", 0),
        )
        self.effects.append(effect)
        self.effects_by_name["freqshift"] = effect
        self.live_params[("freqshift", "enabled")] = settings.get("freqshift_enabled", False)
        self.live_params[("freqshift", "hz")] = settings.get("freqshift_hz", 0)

        effect = BandpassEffect(
            low_cut=settings.get("bandpass_low", 300),
            high_cut=settings.get("bandpass_high", 3000),
        )
        self.effects.append(effect)
        self.effects_by_name["bandpass"] = effect
        self.live_params[("bandpass", "enabled")] = settings.get("bandpass_enabled", False)
        self.live_params[("bandpass", "low")] = settings.get("bandpass_low", 300)
        self.live_params[("bandpass", "high")] = settings.get("bandpass_high", 3000)

        effect = DelayEffect(
            delay_ms=settings.get("delay_time_ms", 100),
            feedback=settings.get("delay_feedback", 0.4),
            mix=settings.get("delay_mix", 0.5),
        )
        self.effects.append(effect)
        self.effects_by_name["delay"] = effect
        self.live_params[("delay", "enabled")] = settings.get("delay_enabled", False)
        self.live_params[("delay", "time_ms")] = settings.get("delay_time_ms", 100)
        self.live_params[("delay", "feedback")] = settings.get("delay_feedback", 0.4)
        self.live_params[("delay", "mix")] = settings.get("delay_mix", 0.5)

        effect = TimeStretchEffect(
            rate=settings.get("timestretch_rate", 1.0),
        )
        self.effects.append(effect)
        self.effects_by_name["timestretch"] = effect
        self.live_params[("timestretch", "enabled")] = settings.get("timestretch_enabled", False)
        self.live_params[("timestretch", "rate")] = settings.get("timestretch_rate", 1.0)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through all effects in the chain."""
        result = audio.copy()

        for effect in self.effects:
            result = effect.process(result, self.sample_rate)

        # Normalize to prevent clipping
        max_val = np.abs(result).max()
        if max_val > 1.0:
            result = result / max_val

        return result

    def add_effect(self, effect: AudioEffect):
        """Add an effect to the pipeline."""
        self.effects.append(effect)

    def clear(self):
        """Remove all effects."""
        self.effects = []
        self.effects_by_name = {}

    def update_param(self, effect_name: str, param_name: str, value: float):
        """Update a live parameter (thread-safe, called from UI thread)."""
        self._param_queue.put((effect_name, param_name, value))

    def _drain_param_queue(self):
        """Apply any pending parameter updates from the queue."""
        while not self._param_queue.empty():
            try:
                effect_name, param_name, value = self._param_queue.get_nowait()
                self.live_params[(effect_name, param_name)] = value
            except queue.Empty:
                break

    def process_chunk(self, audio: np.ndarray) -> np.ndarray:
        """Process a chunk of audio with current live parameters.

        This is called from the audio callback thread for real-time processing.
        Each effect checks its 'enabled' parameter in live_params before processing.
        """
        # Apply any pending parameter updates
        self._drain_param_queue()

        result = audio.copy()

        # Process each effect by name so we can check enabled state
        for effect_name, effect in self.effects_by_name.items():
            # Check if effect is enabled via live_params
            if not self.live_params.get((effect_name, "enabled"), False):
                continue

            # Check if effect supports chunk processing
            if hasattr(effect, 'process_chunk'):
                result = effect.process_chunk(result, self.sample_rate, self.live_params)
            else:
                # Fallback to regular process for effects not yet updated
                result = effect.process(result, self.sample_rate)

        # Normalize to prevent clipping
        max_val = np.abs(result).max()
        if max_val > 1.0:
            result = result / max_val

        return result
