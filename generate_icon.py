#!/usr/bin/env python3
"""Generate app icon for ScanScratch.

Creates a stylized icon representing SSTV/glitch art:
- Retro TV screen shape
- Scan lines
- Glitch effect
"""

from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

def create_icon(size=1024):
    """Create the ScanScratch icon."""
    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate dimensions
    margin = size // 8
    corner_radius = size // 6

    # Background - rounded rectangle (retro TV shape)
    # Dark background
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner_radius,
        fill=(30, 30, 35, 255)
    )

    # Inner screen area
    screen_margin = margin + size // 16
    draw.rounded_rectangle(
        [screen_margin, screen_margin, size - screen_margin, size - screen_margin],
        radius=corner_radius // 2,
        fill=(20, 25, 30, 255)
    )

    # Create glitch/gradient effect on the screen
    screen_left = screen_margin + 10
    screen_top = screen_margin + 10
    screen_right = size - screen_margin - 10
    screen_bottom = size - screen_margin - 10
    screen_width = screen_right - screen_left
    screen_height = screen_bottom - screen_top

    # Draw colored bands (like SSTV transmission)
    colors = [
        (80, 180, 80),   # Green
        (80, 130, 180),  # Blue
        (180, 80, 80),   # Red
        (180, 180, 80),  # Yellow
        (80, 180, 180),  # Cyan
        (180, 80, 180),  # Magenta
    ]

    band_height = screen_height // len(colors)
    for i, color in enumerate(colors):
        y_start = screen_top + i * band_height
        y_end = y_start + band_height

        # Add some horizontal offset for glitch effect
        offset = np.sin(i * 0.8) * 15

        draw.rectangle(
            [screen_left + offset, y_start, screen_right + offset, y_end],
            fill=(*color, 200)
        )

    # Add scan lines
    for y in range(screen_top, screen_bottom, 4):
        draw.line(
            [(screen_left, y), (screen_right, y)],
            fill=(0, 0, 0, 60),
            width=1
        )

    # Add some "glitch" rectangles
    np.random.seed(42)  # Consistent glitch pattern
    for _ in range(8):
        glitch_y = np.random.randint(screen_top, screen_bottom - 20)
        glitch_height = np.random.randint(5, 25)
        glitch_offset = np.random.randint(-30, 30)
        glitch_color = colors[np.random.randint(0, len(colors))]

        draw.rectangle(
            [screen_left + glitch_offset, glitch_y,
             screen_right + glitch_offset, glitch_y + glitch_height],
            fill=(*glitch_color, 150)
        )

    # Add "SS" text stylized
    # Draw a simple stylized "S" shape twice
    center_x = size // 2
    center_y = size // 2
    s_size = size // 5

    # First S
    s1_x = center_x - s_size // 2
    draw.arc(
        [s1_x - s_size//2, center_y - s_size, s1_x + s_size//2, center_y],
        start=270, end=180,
        fill=(200, 220, 200, 255),
        width=size // 30
    )
    draw.arc(
        [s1_x - s_size//2, center_y, s1_x + s_size//2, center_y + s_size],
        start=90, end=0,
        fill=(200, 220, 200, 255),
        width=size // 30
    )

    # Second S
    s2_x = center_x + s_size // 2
    draw.arc(
        [s2_x - s_size//2, center_y - s_size, s2_x + s_size//2, center_y],
        start=270, end=180,
        fill=(200, 220, 200, 255),
        width=size // 30
    )
    draw.arc(
        [s2_x - s_size//2, center_y, s2_x + s_size//2, center_y + s_size],
        start=90, end=0,
        fill=(200, 220, 200, 255),
        width=size // 30
    )

    # Add outer glow/border
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner_radius,
        outline=(90, 138, 90, 255),
        width=size // 50
    )

    return img


def save_icon_formats(img, output_dir='assets'):
    """Save icon in various formats for Mac and Windows."""
    os.makedirs(output_dir, exist_ok=True)

    # Save PNG at various sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(output_dir, f'icon_{size}.png'))

    # Save main PNG
    img.save(os.path.join(output_dir, 'icon.png'))

    # Create ICO for Windows (multiple sizes embedded)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [img.resize(size, Image.Resampling.LANCZOS) for size in ico_sizes]
    ico_images[0].save(
        os.path.join(output_dir, 'icon.ico'),
        format='ICO',
        sizes=ico_sizes
    )

    print(f"Icons saved to {output_dir}/")
    print("  - icon.png (1024x1024)")
    print("  - icon.ico (Windows)")
    print("  - icon_*.png (various sizes)")
    print("")
    print("To create macOS .icns file, run:")
    print("  mkdir -p assets/icon.iconset")
    print("  cp assets/icon_16.png assets/icon.iconset/icon_16x16.png")
    print("  cp assets/icon_32.png assets/icon.iconset/icon_16x16@2x.png")
    print("  cp assets/icon_32.png assets/icon.iconset/icon_32x32.png")
    print("  cp assets/icon_64.png assets/icon.iconset/icon_32x32@2x.png")
    print("  cp assets/icon_128.png assets/icon.iconset/icon_128x128.png")
    print("  cp assets/icon_256.png assets/icon.iconset/icon_128x128@2x.png")
    print("  cp assets/icon_256.png assets/icon.iconset/icon_256x256.png")
    print("  cp assets/icon_512.png assets/icon.iconset/icon_256x256@2x.png")
    print("  cp assets/icon_512.png assets/icon.iconset/icon_512x512.png")
    print("  cp assets/icon_1024.png assets/icon.iconset/icon_512x512@2x.png")
    print("  iconutil -c icns assets/icon.iconset -o assets/icon.icns")


if __name__ == '__main__':
    print("Generating ScanScratch icon...")
    icon = create_icon(1024)
    save_icon_formats(icon)
