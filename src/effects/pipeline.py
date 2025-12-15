"""Audio effects pipeline for processing SSTV signals."""

import numpy as np
from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioEffect(Protocol):
    """Protocol for audio effects."""

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process audio and return modified audio."""
        ...


class EffectsPipeline:
    """Chain of audio effects to process SSTV signals."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.effects: list[AudioEffect] = []
        self._settings: dict = {}

    def configure(self, settings: dict):
        """Configure the pipeline from settings dictionary."""
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

        # Add enabled effects in order
        # Phase/amplitude modulation first for base corruption
        if settings.get("phasemod_enabled", False):
            self.effects.append(PhaseModulationEffect(
                depth=settings.get("phasemod_depth", 0.5),
                rate=settings.get("phasemod_rate", 8.0),
            ))

        if settings.get("ampmod_enabled", False):
            self.effects.append(AmplitudeModulationEffect(
                depth=settings.get("ampmod_depth", 0.5),
                rate=settings.get("ampmod_rate", 12.0),
            ))

        # Sync effects for scanline corruption
        if settings.get("syncwobble_enabled", False):
            self.effects.append(SyncWobbleEffect(
                amount=settings.get("syncwobble_amount", 0.5),
                frequency=settings.get("syncwobble_freq", 5.0),
            ))

        if settings.get("syncdropout_enabled", False):
            self.effects.append(SyncDropoutEffect(
                probability=settings.get("syncdropout_prob", 0.1),
                duration_ms=settings.get("syncdropout_duration", 5.0),
            ))

        if settings.get("scanline_enabled", False):
            self.effects.append(ScanlineCorruptionEffect(
                frequency=settings.get("scanline_freq", 0.15),
                intensity=settings.get("scanline_intensity", 0.7),
            ))

        if settings.get("noise_enabled", False):
            self.effects.append(NoiseEffect(
                amount=settings.get("noise_amount", 0.2),
                noise_type=settings.get("noise_type", "white"),
            ))

        if settings.get("distortion_enabled", False):
            self.effects.append(DistortionEffect(
                drive=settings.get("distortion_drive", 0.3),
                clip=settings.get("distortion_clip", 0.8),
            ))

        if settings.get("harmonic_enabled", False):
            self.effects.append(HarmonicDistortionEffect(
                amount=settings.get("harmonic_amount", 0.5),
                harmonics=settings.get("harmonic_count", 3),
            ))

        if settings.get("bitcrush_enabled", False):
            self.effects.append(BitcrushEffect(
                bits=settings.get("bitcrush_bits", 8),
                target_rate=settings.get("bitcrush_rate", 22050),
            ))

        if settings.get("freqshift_enabled", False):
            self.effects.append(FrequencyShiftEffect(
                shift_hz=settings.get("freqshift_hz", 0),
            ))

        if settings.get("bandpass_enabled", False):
            self.effects.append(BandpassEffect(
                low_cut=settings.get("bandpass_low", 300),
                high_cut=settings.get("bandpass_high", 3000),
            ))

        if settings.get("delay_enabled", False):
            self.effects.append(DelayEffect(
                delay_ms=settings.get("delay_time_ms", 100),
                feedback=settings.get("delay_feedback", 0.4),
                mix=settings.get("delay_mix", 0.5),
            ))

        if settings.get("timestretch_enabled", False):
            self.effects.append(TimeStretchEffect(
                rate=settings.get("timestretch_rate", 1.0),
            ))

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
