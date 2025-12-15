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
}


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

        spec = MODE_SPECS[mode]
        sstv_class = spec["class"]
        frame_width = spec["width"]
        frame_height = spec["height"]

        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        if preserve_aspect:
            # Fit image to frame while preserving aspect ratio
            fitted, self.last_crop_box = fit_image_to_frame(image, frame_width, frame_height)
        else:
            # Stretch to fit (old behavior)
            fitted = image.resize((frame_width, frame_height), Image.Resampling.LANCZOS)
            self.last_crop_box = (0, 0, frame_width, frame_height)

        # Create SSTV encoder
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
