"""SSTV encoder using pysstv library."""

import numpy as np
from PIL import Image
from io import BytesIO
import wave
import struct

# pysstv imports
from pysstv.color import (
    MartinM1,
    MartinM2,
    ScottieS1,
    ScottieS2,
    Robot36,
    PD90,
    PD120,
    PD180,
    PD290,
)


# Mode specifications - width/height must match pysstv's actual encoding dimensions
MODE_SPECS = {
    "MartinM1": {"class": MartinM1, "width": 320, "height": 256},
    "MartinM2": {"class": MartinM2, "width": 160, "height": 256},   # M2 is half width
    "ScottieS1": {"class": ScottieS1, "width": 320, "height": 256},
    "ScottieS2": {"class": ScottieS2, "width": 160, "height": 256}, # S2 is half width
    "Robot36": {"class": Robot36, "width": 320, "height": 240},
    "PD90": {"class": PD90, "width": 320, "height": 256},
    "PD120": {"class": PD120, "width": 640, "height": 496},
    "PD180": {"class": PD180, "width": 640, "height": 496},
    "PD290": {"class": PD290, "width": 800, "height": 616},
    # Experimental custom mode - matches input image resolution
    "NativeRes": {"class": None, "width": None, "height": None},
}


def generate_continuous_audio(freq_time_pairs, sample_rate):
    """
    Generate phase-continuous audio from (frequency, duration_ms) tuples.

    This maintains phase continuity across all frequency segments, preventing
    clicks and pops that would otherwise occur at segment boundaries.

    Args:
        freq_time_pairs: List of (frequency_hz, duration_ms) tuples
        sample_rate: Audio sample rate in Hz

    Returns:
        numpy array of audio samples with continuous phase
    """
    audio_chunks = []
    phase_offset = 0.0

    for freq, duration_ms in freq_time_pairs:
        num_samples = int(duration_ms * sample_rate / 1000.0)
        if num_samples == 0:
            continue

        t = np.arange(num_samples) / sample_rate
        audio = np.sin(2 * np.pi * freq * t + phase_offset)
        audio_chunks.append(audio)

        # Accumulate phase for continuity into next segment
        phase_offset = (phase_offset + 2 * np.pi * freq * num_samples / sample_rate) % (2 * np.pi)

    return np.concatenate(audio_chunks) if audio_chunks else np.array([])


def encode_custom_mode(image: Image.Image, mode: str, sample_rate: int, spec: dict) -> np.ndarray:
    """
    Custom SSTV encoder for experimental high-resolution modes.
    Generates SSTV audio directly without using pysstv, using phase-continuous
    sine wave generation to avoid artifacts.

    Args:
        image: PIL Image to encode
        mode: SSTV mode name
        sample_rate: Audio sample rate
        spec: Complete mode spec with width, height, sync_ms, scan_ms, gap_ms, color_order
    """
    # Get dimensions from spec
    width = spec["width"]
    height = spec["height"]

    # SSTV frequency constants
    FREQ_SYNC = 1200
    FREQ_BLACK = 1500
    FREQ_WHITE = 2300

    # Calculate sample counts for precise timing
    ms_to_samples = sample_rate / 1000.0
    sync_samples = int(round(spec["sync_ms"] * ms_to_samples))
    scan_samples = int(round(spec["scan_ms"] * ms_to_samples))
    gap_samples = int(round(spec["gap_ms"] * ms_to_samples))
    header_samples = int(round(910.0 * ms_to_samples))

    # Get pixel data
    pixels = np.array(image)

    # Build audio with continuous phase
    audio_chunks = []
    phase = 0.0

    def add_tone(freq, num_samples):
        """Add a tone segment maintaining phase continuity."""
        nonlocal phase
        if num_samples <= 0:
            return
        t = np.arange(num_samples) / sample_rate
        chunk = np.sin(2 * np.pi * freq * t + phase)
        audio_chunks.append(chunk)
        phase = (phase + 2 * np.pi * freq * num_samples / sample_rate) % (2 * np.pi)

    def add_channel(channel_data):
        """Encode a color channel with interpolated frequencies."""
        nonlocal phase
        if scan_samples <= 0:
            return

        # Map pixel values to frequencies
        pixel_freqs = FREQ_BLACK + (channel_data.astype(np.float64) / 255.0) * (FREQ_WHITE - FREQ_BLACK)

        # Interpolate frequencies across scan_samples
        pixel_positions = np.linspace(0, width - 1, scan_samples)
        interpolated_freqs = np.interp(pixel_positions, np.arange(width), pixel_freqs)

        # Generate audio sample-by-sample with continuous phase
        t = np.arange(scan_samples) / sample_rate
        # Use instantaneous frequency: each sample uses its interpolated frequency
        # Phase accumulates: phase[n] = phase[n-1] + 2*pi*freq[n-1]/sample_rate
        phase_increments = 2 * np.pi * interpolated_freqs / sample_rate
        phases = phase + np.cumsum(phase_increments)
        phases = np.insert(phases[:-1], 0, phase)  # Shift so first sample uses initial phase

        chunk = np.sin(phases)
        audio_chunks.append(chunk)
        phase = phases[-1] + phase_increments[-1]
        phase = phase % (2 * np.pi)

    # 1. Header (simplified VIS code)
    add_tone(FREQ_SYNC, header_samples)

    # 2. Encode each scanline
    for y in range(height):
        line_pixels = pixels[y]

        # Sync pulse
        add_tone(FREQ_SYNC, sync_samples)

        # Gap after sync
        add_tone(FREQ_BLACK, gap_samples)

        # Encode R, G, B channels
        for channel_idx in [0, 1, 2]:
            channel_data = line_pixels[:, channel_idx]
            add_channel(channel_data)

            # Gap after channel
            add_tone(FREQ_BLACK, gap_samples)

    # Concatenate all audio
    audio = np.concatenate(audio_chunks)

    # Normalize to float32 [-1, 1]
    audio = audio.astype(np.float32)
    audio = np.clip(audio, -1.0, 1.0)

    return audio


def fit_image_to_frame(image: Image.Image, frame_width: int, frame_height: int) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """
    Fit an image into a frame while preserving aspect ratio.

    Returns:
        Tuple of (fitted_image, crop_box) where crop_box is (left, top, right, bottom)
        that can be used to extract the image area from the decoded output.
    """
    img_width, img_height = image.size
    img_ratio = img_width / img_height
    frame_ratio = frame_width / frame_height

    if img_ratio > frame_ratio:
        # Image is wider than frame - fit to width, letterbox top/bottom
        new_width = frame_width
        new_height = int(frame_width / img_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center vertically
        top_pad = (frame_height - new_height) // 2

        # Create frame with black background
        frame = Image.new('RGB', (frame_width, frame_height), (0, 0, 0))
        frame.paste(resized, (0, top_pad))

        crop_box = (0, top_pad, new_width, top_pad + new_height)

    else:
        # Image is taller than frame - fit to height, pillarbox left/right
        new_height = frame_height
        new_width = int(frame_height * img_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center horizontally
        left_pad = (frame_width - new_width) // 2

        # Create frame with black background
        frame = Image.new('RGB', (frame_width, frame_height), (0, 0, 0))
        frame.paste(resized, (left_pad, 0))

        crop_box = (left_pad, 0, left_pad + new_width, new_height)

    return frame, crop_box


class SSTVEncoder:
    """Encodes images to SSTV audio signals."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.last_crop_box = None  # Store for decoder to use

    def encode(
        self,
        image: Image.Image,
        mode: str = "MartinM1",
        preserve_aspect: bool = True
    ) -> tuple[np.ndarray, int]:
        """
        Encode an image to SSTV audio.

        Args:
            image: PIL Image to encode
            mode: SSTV mode name (MartinM1, ScottieS1, etc.)
            preserve_aspect: If True, letterbox/pillarbox to preserve aspect ratio

        Returns:
            Tuple of (audio_data as numpy array, sample_rate)
        """
        if mode not in MODE_SPECS:
            raise ValueError(f"Unknown SSTV mode: {mode}")

        # For NativeRes, use decoder's spec as base (has timing info)
        if mode == "NativeRes":
            from .streaming_decoder import MODE_SPECS as DECODER_SPECS
            spec = DECODER_SPECS[mode].copy()
            sstv_class = None  # NativeRes uses custom encoder
        else:
            spec = MODE_SPECS[mode].copy()
            sstv_class = spec["class"]

        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # For NativeRes mode, use the actual image dimensions
        if mode == "NativeRes":
            frame_width, frame_height = image.size
            spec["width"] = frame_width
            spec["height"] = frame_height
            # Use MartinM1 pixel rate as reference (146.432ms / 320px = 0.4576ms/px)
            # This ensures consistent pixel timing across all resolutions
            REFERENCE_MS_PER_PIXEL = 146.432 / 320.0
            spec["scan_ms"] = frame_width * REFERENCE_MS_PER_PIXEL
        else:
            frame_width = spec["width"]
            frame_height = spec["height"]

        if preserve_aspect and mode != "NativeRes":
            # Fit image to frame while preserving aspect ratio
            fitted, self.last_crop_box = fit_image_to_frame(image, frame_width, frame_height)
        else:
            # For NativeRes, use image as-is; for others, stretch to fit
            if mode == "NativeRes":
                fitted = image
                self.last_crop_box = (0, 0, frame_width, frame_height)
            else:
                fitted = image.resize((frame_width, frame_height), Image.Resampling.LANCZOS)
                self.last_crop_box = (0, 0, frame_width, frame_height)

        # Check if this is a custom mode or standard pysstv mode
        if sstv_class is None:
            # Use custom encoder for experimental modes
            audio = encode_custom_mode(fitted, mode, self.sample_rate, spec)
        else:
            # Use pysstv for standard modes
            sstv = sstv_class(fitted, self.sample_rate, bits=16)

            # Generate audio samples
            samples = list(sstv.gen_samples())

            # Convert to numpy array and normalize to float32 [-1, 1]
            audio = np.array(samples, dtype=np.float32)
            audio = audio / 32768.0  # Normalize 16-bit to float

        return audio, self.sample_rate

    def get_crop_box(self) -> tuple[int, int, int, int] | None:
        """Get the crop box from the last encode operation."""
        return self.last_crop_box

    def encode_to_wav(
        self,
        image: Image.Image,
        output_path: str,
        mode: str = "MartinM1"
    ):
        """Encode image and save directly to WAV file."""
        audio, sample_rate = self.encode(image, mode)

        # Convert back to 16-bit integers
        audio_int = (audio * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(output_path, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_int.tobytes())
