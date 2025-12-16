"""Output manager for auto-saving transmission results."""

import json
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image


class OutputManager:
    """Manages saving and loading of transmission outputs."""

    THUMBNAIL_SIZE = (80, 80)
    UPSCALE_FACTOR = 4  # Save images at 4x resolution

    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def _generate_id(self, length: int = 6) -> str:
        """Generate a random alphanumeric ID."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))

    def create_output_folder(self, mode: str) -> Path:
        """Create uniquely-named folder for new output.

        Args:
            mode: SSTV mode name (e.g., "MartinM1")

        Returns:
            Path to the created folder
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        unique_id = self._generate_id()
        folder = self.base_dir / f"{timestamp}_{unique_id}_{mode}"
        folder.mkdir(exist_ok=True)
        return folder

    def save_image(
        self,
        folder: Path,
        name: str,
        image_data: np.ndarray,
        crop_box: Optional[tuple] = None,
        skip_upscale: bool = False,
    ) -> Path:
        """Save numpy array as PNG at upscaled resolution.

        Args:
            folder: Output folder path
            name: Filename without extension (e.g., "effects", "clean")
            image_data: RGB numpy array (H, W, 3)
            crop_box: Optional (left, top, right, bottom) to crop letterboxing
            skip_upscale: If True, don't upscale (for NativeRes mode)

        Returns:
            Path to saved file
        """
        # Convert to PIL Image
        image = Image.fromarray(image_data.astype(np.uint8))

        # Apply crop if specified
        if crop_box is not None:
            left, top, right, bottom = crop_box
            image = image.crop((left, top, right, bottom))

        # Upscale using nearest neighbor to preserve pixel art look (unless skipped)
        if not skip_upscale:
            new_size = (image.width * self.UPSCALE_FACTOR, image.height * self.UPSCALE_FACTOR)
            image = image.resize(new_size, Image.Resampling.NEAREST)

        # Save as PNG
        file_path = folder / f"{name}.png"
        image.save(file_path, "PNG")
        return file_path

    def save_thumbnail(self, folder: Path, image_data: np.ndarray) -> Path:
        """Save small thumbnail for gallery.

        Args:
            folder: Output folder path
            image_data: RGB numpy array (H, W, 3)

        Returns:
            Path to saved thumbnail
        """
        # Convert to PIL Image
        image = Image.fromarray(image_data.astype(np.uint8))

        # Resize to thumbnail size, maintaining aspect ratio
        image.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # Create square canvas and paste image centered
        thumb = Image.new("RGB", self.THUMBNAIL_SIZE, (30, 30, 30))
        x = (self.THUMBNAIL_SIZE[0] - image.width) // 2
        y = (self.THUMBNAIL_SIZE[1] - image.height) // 2
        thumb.paste(image, (x, y))

        # Save
        file_path = folder / "thumbnail.png"
        thumb.save(file_path, "PNG")
        return file_path

    def save_metadata(
        self,
        folder: Path,
        settings: dict,
        source_path: Optional[str] = None,
        mode: str = "",
    ) -> Path:
        """Save effect settings and info as JSON.

        Args:
            folder: Output folder path
            settings: Effect settings dictionary
            source_path: Optional path to source image
            mode: SSTV mode name

        Returns:
            Path to saved metadata file
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "source_path": source_path,
            "settings": settings,
        }

        file_path = folder / "metadata.json"
        with open(file_path, "w") as f:
            json.dump(metadata, f, indent=2)
        return file_path

    def get_all_outputs(self) -> list[dict]:
        """Return list of all output folders with metadata for gallery.

        Returns:
            List of dicts with folder info, sorted by timestamp (newest first)
        """
        outputs = []

        for folder in self.base_dir.iterdir():
            if not folder.is_dir():
                continue

            # Check for required files
            thumbnail_path = folder / "thumbnail.png"
            metadata_path = folder / "metadata.json"

            if not thumbnail_path.exists():
                continue

            # Load metadata if available
            metadata = {}
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass

            # Parse folder name for timestamp and mode
            # Format: YYYY-MM-DD_HHMMSS_uniqueid_mode
            parts = folder.name.split("_")
            if len(parts) >= 4:
                date_str = parts[0]
                time_str = parts[1]
                unique_id = parts[2]
                mode = "_".join(parts[3:])  # mode may contain underscores
            elif len(parts) >= 3:
                # Legacy format without unique_id
                date_str = parts[0]
                time_str = parts[1]
                mode = "_".join(parts[2:])
            else:
                date_str = ""
                time_str = ""
                mode = folder.name

            outputs.append({
                "folder": folder,
                "thumbnail_path": thumbnail_path,
                "date": date_str,
                "time": time_str,
                "mode": mode,
                "metadata": metadata,
                "has_video": (folder / "video.mp4").exists(),
                "has_effects": (folder / "effects.png").exists(),
                "has_clean": (folder / "clean.png").exists(),
            })

        # Sort by folder name (which includes timestamp) in reverse order
        outputs.sort(key=lambda x: x["folder"].name, reverse=True)
        return outputs

    def delete_output(self, folder: Path) -> bool:
        """Delete an output folder and all its contents.

        Args:
            folder: Path to folder to delete

        Returns:
            True if deleted successfully
        """
        try:
            import shutil
            shutil.rmtree(folder)
            return True
        except Exception:
            return False

    def get_output_path(self, folder: Path, file_type: str) -> Optional[Path]:
        """Get path to a specific output file.

        Args:
            folder: Output folder path
            file_type: One of "effects", "clean", "video", "thumbnail", "metadata"

        Returns:
            Path to file if it exists, None otherwise
        """
        file_map = {
            "effects": "effects.png",
            "clean": "clean.png",
            "video": "video.mp4",
            "thumbnail": "thumbnail.png",
            "metadata": "metadata.json",
        }

        filename = file_map.get(file_type)
        if filename is None:
            return None

        file_path = folder / filename
        return file_path if file_path.exists() else None
