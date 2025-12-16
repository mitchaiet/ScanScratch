"""Video export for SSTV decode animations."""

import numpy as np
from PIL import Image
from typing import Callable, Optional
import tempfile
import os


class VideoExporter:
    """Export SSTV decode process as MP4 video with audio."""

    def __init__(
        self,
        width: int,
        height: int,
        sample_rate: int = 44100,
        fps: int = 30,
    ):
        """
        Initialize video exporter.

        Args:
            width: Output video width in pixels
            height: Output video height in pixels
            sample_rate: Audio sample rate
            fps: Video frame rate
        """
        self.width = width
        self.height = height
        self.sample_rate = sample_rate
        self.fps = fps
        self.frames = []
        self.audio_data = None

    def set_audio(self, audio: np.ndarray):
        """Set the audio data for the video."""
        self.audio_data = audio.astype(np.float32)

    def add_frame(self, image_data: np.ndarray):
        """
        Add a frame to the video.

        Args:
            image_data: RGB image array (height, width, 3)
        """
        # Ensure correct shape and type
        if image_data.dtype != np.uint8:
            image_data = np.clip(image_data, 0, 255).astype(np.uint8)
        self.frames.append(image_data.copy())

    def export(
        self,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        Export the video to MP4.

        Args:
            output_path: Path to save the MP4 file
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            print(f"[VideoExporter] Importing moviepy...", flush=True)
            from moviepy import ImageSequenceClip, AudioClip
            import scipy.io.wavfile as wavfile
            print(f"[VideoExporter] Imports successful", flush=True)

            if not self.frames:
                print("[VideoExporter] No frames to export")
                return False
            print(f"[VideoExporter] Have {len(self.frames)} frames to export", flush=True)

            if progress_callback:
                progress_callback(0, 100)

            # Create video from frames
            # moviepy expects frames as list of numpy arrays (RGB)
            clip = ImageSequenceClip(self.frames, fps=self.fps)

            if progress_callback:
                progress_callback(30, 100)

            # Add audio if available
            if self.audio_data is not None and len(self.audio_data) > 0:
                # Create audio clip from numpy array using moviepy 2.x API
                audio_duration = len(self.audio_data) / self.sample_rate
                audio_data = self.audio_data  # Capture for closure
                sample_rate = self.sample_rate

                def make_audio_frame(t):
                    """Generate audio frames for given time(s)."""
                    if isinstance(t, np.ndarray):
                        # t is array of times
                        indices = (t * sample_rate).astype(int)
                        indices = np.clip(indices, 0, len(audio_data) - 1)
                        return audio_data[indices].reshape(-1, 1)
                    else:
                        # t is single time
                        idx = int(t * sample_rate)
                        idx = min(idx, len(audio_data) - 1)
                        return audio_data[idx]

                audio_clip = AudioClip(make_audio_frame, duration=audio_duration, fps=sample_rate)

                # Match video duration to audio duration
                video_duration = len(self.frames) / self.fps

                # If video is shorter than audio, extend the last frame
                if video_duration < audio_duration:
                    # Calculate how many extra frames we need
                    extra_frames_needed = int((audio_duration - video_duration) * self.fps) + 1
                    last_frame = self.frames[-1]
                    extended_frames = self.frames + [last_frame] * extra_frames_needed
                    clip = ImageSequenceClip(extended_frames, fps=self.fps)

                # Set audio on clip
                clip = clip.with_audio(audio_clip)

                # Trim to audio duration
                clip = clip.with_duration(audio_duration)

            if progress_callback:
                progress_callback(50, 100)

            # Export to MP4 with QuickTime-compatible settings
            print(f"[VideoExporter] Writing videofile to {output_path}...", flush=True)
            clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=self.fps,
                logger=None,  # Suppress moviepy's verbose output
                ffmpeg_params=[
                    '-pix_fmt', 'yuv420p',  # QuickTime requires yuv420p
                    '-profile:v', 'baseline',  # Most compatible H.264 profile
                    '-level', '3.0',
                    '-movflags', '+faststart',  # Move moov atom to start for streaming
                ],
            )
            print(f"[VideoExporter] write_videofile complete", flush=True)

            # Verify file was created
            import os
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[VideoExporter] File created: {output_path} ({file_size} bytes)", flush=True)
            else:
                print(f"[VideoExporter] WARNING: File not found after export: {output_path}", flush=True)

            if progress_callback:
                progress_callback(100, 100)

            return True

        except Exception as e:
            print(f"[VideoExporter] Video export error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def clear(self):
        """Clear all frames and audio."""
        self.frames = []
        self.audio_data = None


UPSCALE_FACTOR = 4  # Video output at 4x resolution


def create_decode_video_from_image(
    final_image: np.ndarray,
    source_image: Image.Image,
    mode: str,
    effect_settings: dict,
    output_path: str,
    fps: int = 30,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """
    Create a video of the SSTV decode process using the already-decoded image.

    This uses the actual decoded image for perfect visual matching, while
    generating fresh audio for the soundtrack. Output is at 4x resolution.

    Args:
        final_image: The already-decoded RGB image array (height, width, 3)
        source_image: The source image to encode (for audio generation)
        mode: SSTV mode (e.g., 'MartinM1')
        effect_settings: Effect settings dictionary
        output_path: Path to save the MP4
        fps: Video frame rate
        progress_callback: Optional callback(current, total, status) for progress

    Returns:
        True if export succeeded
    """
    from src.sstv.encoder import SSTVEncoder
    from src.sstv.streaming_decoder import MODE_SPECS
    from src.effects.pipeline import EffectsPipeline

    try:
        print(f"[VideoExport] Starting video export from image for mode={mode}", flush=True)
        if progress_callback:
            progress_callback(0, 100, "Encoding SSTV audio...")

        # Get mode specs
        if mode not in MODE_SPECS:
            print(f"[VideoExport] Unknown mode: {mode}", flush=True)
            return False

        spec = MODE_SPECS[mode]
        sample_rate = 44100

        # Skip upscaling for NativeRes mode (already full resolution)
        is_native_res = mode == "NativeRes"
        scale = 1 if is_native_res else UPSCALE_FACTOR

        # For NativeRes, get dimensions from the actual image
        if is_native_res:
            height, width = final_image.shape[:2]
        else:
            width = spec['width']
            height = spec['height']

        # Upscaled dimensions (must be even for H.264/QuickTime compatibility)
        upscaled_width = width * scale
        upscaled_height = height * scale
        # Ensure even dimensions
        if upscaled_width % 2 != 0:
            upscaled_width += 1
        if upscaled_height % 2 != 0:
            upscaled_height += 1

        if is_native_res:
            print(f"[VideoExport] Mode specs: {width}x{height} -> {upscaled_width}x{upscaled_height} (NativeRes, padded to even)", flush=True)
        else:
            print(f"[VideoExport] Mode specs: {width}x{height} -> {upscaled_width}x{upscaled_height} (4x)", flush=True)
        print(f"[VideoExport] Final image shape: {final_image.shape}", flush=True)

        # Upscale/resize the final image (pad to even dimensions if needed)
        final_pil = Image.fromarray(final_image.astype(np.uint8))
        final_upscaled = final_pil.resize((upscaled_width, upscaled_height), Image.Resampling.NEAREST)
        final_upscaled_array = np.array(final_upscaled)

        # Encode the image to SSTV audio (for the soundtrack)
        encoder = SSTVEncoder(sample_rate=sample_rate)
        audio_data, _ = encoder.encode(source_image, mode=mode)
        print(f"[VideoExport] Encoded audio: {len(audio_data)} samples", flush=True)

        if progress_callback:
            progress_callback(10, 100, "Applying effects to audio...")

        # Apply effects to audio
        pipeline = EffectsPipeline(sample_rate)
        pipeline.configure(effect_settings)
        affected_audio = pipeline.process(audio_data)
        print(f"[VideoExport] Affected audio: {len(affected_audio)} samples", flush=True)

        if progress_callback:
            progress_callback(20, 100, "Generating frames...")

        # Calculate timing (based on original line count)
        total_samples = len(affected_audio)
        samples_per_line = total_samples // height
        duration = total_samples / sample_rate
        total_frames = int(duration * fps)
        print(f"[VideoExport] Duration: {duration:.2f}s, Total frames: {total_frames}", flush=True)

        # Create video exporter at upscaled resolution
        exporter = VideoExporter(upscaled_width, upscaled_height, sample_rate, fps)
        exporter.set_audio(affected_audio)

        # Generate frames - progressively reveal the ACTUAL decoded image at 4x
        image_buffer = np.zeros((upscaled_height, upscaled_width, 3), dtype=np.uint8)

        print(f"[VideoExport] Generating {total_frames} frames...", flush=True)
        for frame_idx in range(total_frames):
            frame_time = frame_idx / fps
            current_sample = int(frame_time * sample_rate)
            current_line = min(current_sample // samples_per_line, height - 1)

            # Copy upscaled lines from the final image
            # Each original line becomes `scale` lines in the upscaled version
            upscaled_line_end = (current_line + 1) * scale
            image_buffer[:upscaled_line_end] = final_upscaled_array[:upscaled_line_end]

            exporter.add_frame(image_buffer)

            if progress_callback and frame_idx % 10 == 0:
                pct = 20 + int((frame_idx / total_frames) * 70)
                progress_callback(pct, 100, f"Rendering frame {frame_idx}/{total_frames}...")

        print(f"[VideoExport] Frame generation complete, {len(exporter.frames)} frames created", flush=True)

        if progress_callback:
            progress_callback(90, 100, "Writing video file...")

        # Export the video
        print(f"[VideoExport] Calling exporter.export({output_path})...", flush=True)
        success = exporter.export(output_path)
        print(f"[VideoExport] Export result: {success}", flush=True)

        if progress_callback:
            progress_callback(100, 100, "Done!")

        return success

    except Exception as e:
        print(f"Error creating decode video: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_decode_video(
    source_image: Image.Image,
    mode: str,
    effect_settings: dict,
    output_path: str,
    fps: int = 30,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """
    Create a video of the SSTV decode process (legacy - re-encodes from scratch).

    Args:
        source_image: The source image to encode
        mode: SSTV mode (e.g., 'MartinM1')
        effect_settings: Effect settings dictionary
        output_path: Path to save the MP4
        fps: Video frame rate
        progress_callback: Optional callback(current, total, status) for progress

    Returns:
        True if export succeeded
    """
    from src.sstv.encoder import SSTVEncoder
    from src.sstv.streaming_decoder import StreamingDecoder, MODE_SPECS
    from src.effects.pipeline import EffectsPipeline

    try:
        print(f"[VideoExport] Starting video export for mode={mode}", flush=True)
        if progress_callback:
            progress_callback(0, 100, "Encoding SSTV audio...")

        # Get mode specs
        if mode not in MODE_SPECS:
            print(f"[VideoExport] Unknown mode: {mode}", flush=True)
            return False

        spec = MODE_SPECS[mode]
        width = spec['width']
        height = spec['height']
        sample_rate = 44100
        print(f"[VideoExport] Mode specs: {width}x{height}", flush=True)

        # Encode the image to SSTV audio
        print(f"[VideoExport] Source image: {source_image.size if source_image else None}", flush=True)
        encoder = SSTVEncoder(sample_rate=sample_rate)
        audio_data, _ = encoder.encode(source_image, mode=mode)
        print(f"[VideoExport] Encoded audio: {len(audio_data)} samples", flush=True)

        if progress_callback:
            progress_callback(10, 100, "Configuring effects...")

        # Apply effects if any are enabled
        pipeline = EffectsPipeline(sample_rate)
        pipeline.configure(effect_settings)

        # Process audio through effects (batch mode for export)
        affected_audio = pipeline.process(audio_data)
        print(f"[VideoExport] Affected audio: {len(affected_audio)} samples", flush=True)

        if progress_callback:
            progress_callback(20, 100, "Decoding frames...")

        # Create decoder
        decoder = StreamingDecoder(mode=mode, sample_rate=sample_rate)

        # Pre-decode all lines into a list (decode_progressive is a generator)
        print(f"[VideoExport] Starting decode_progressive...", flush=True)
        decoded_lines = [None] * height
        for line_num, rgb_line in decoder.decode_progressive(affected_audio):
            decoded_lines[line_num] = rgb_line
        print(f"[VideoExport] decode_progressive complete", flush=True)

        # Calculate samples per line for timing
        total_samples = len(affected_audio)
        samples_per_line = total_samples // height

        # Calculate total duration and frames needed
        duration = total_samples / sample_rate
        total_frames = int(duration * fps)
        print(f"[VideoExport] Duration: {duration:.2f}s, Total frames: {total_frames}", flush=True)

        # Create video exporter
        exporter = VideoExporter(width, height, sample_rate, fps)
        exporter.set_audio(affected_audio)

        # Generate frames - each frame shows decode progress up to that point in time
        image_buffer = np.zeros((height, width, 3), dtype=np.uint8)

        # Count decoded lines
        decoded_count = sum(1 for line in decoded_lines if line is not None)
        print(f"[VideoExport] Decoded lines: {decoded_count}/{height}", flush=True)

        print(f"[VideoExport] Generating {total_frames} frames...", flush=True)
        for frame_idx in range(total_frames):
            # Calculate which sample we're at for this frame
            frame_time = frame_idx / fps
            current_sample = int(frame_time * sample_rate)

            # Calculate which line we should have decoded by now
            current_line = min(current_sample // samples_per_line, height - 1)

            # Decode lines up to current position
            for line_num in range(current_line + 1):
                if decoded_lines[line_num] is not None:
                    rgb_line = decoded_lines[line_num]
                    image_buffer[line_num] = rgb_line

            # Add frame to exporter
            exporter.add_frame(image_buffer)

            # Progress update
            if progress_callback and frame_idx % 10 == 0:
                pct = 20 + int((frame_idx / total_frames) * 70)
                progress_callback(pct, 100, f"Rendering frame {frame_idx}/{total_frames}...")

        print(f"[VideoExport] Frame generation complete, {len(exporter.frames)} frames created", flush=True)

        if progress_callback:
            progress_callback(90, 100, "Writing video file...")

        # Export the video
        print(f"[VideoExport] Calling exporter.export({output_path})...", flush=True)
        success = exporter.export(output_path)
        print(f"[VideoExport] Export result: {success}", flush=True)

        if progress_callback:
            progress_callback(100, 100, "Done!")

        return success

    except Exception as e:
        print(f"Error creating decode video: {e}")
        import traceback
        traceback.print_exc()
        return False
