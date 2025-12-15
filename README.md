```
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ███████╗ ██████╗ █████╗ ███╗   ██╗                     ║
  ║   ██╔════╝██╔════╝██╔══██╗████╗  ██║                     ║
  ║   ███████╗██║     ███████║██╔██╗ ██║                     ║
  ║   ╚════██║██║     ██╔══██║██║╚██╗██║                     ║
  ║   ███████║╚██████╗██║  ██║██║ ╚████║                     ║
  ║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝                     ║
  ║                                                           ║
  ║   ███████╗ ██████╗██████╗  █████╗ ████████╗ ██████╗██╗  ║
  ║   ██╔════╝██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██║  ║
  ║   ███████╗██║     ██████╔╝███████║   ██║   ██║     ██║  ║
  ║   ╚════██║██║     ██╔══██╗██╔══██║   ██║   ██║     ██║  ║
  ║   ███████║╚██████╗██║  ██║██║  ██║   ██║   ╚██████╗██║  ║
  ║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ║
  ║                                                           ║
  ║          ▓▒░  SSTV Glitch Art Generator  ░▒▓            ║
  ╚═══════════════════════════════════════════════════════════╝
```

A professional PyQt6 application for creating glitch art through SSTV (Slow Scan Television) signal corruption. Transform photos into aesthetic retro glitches or extreme digital chaos.

## Features

### Modern Interface
- **Compact Unified Header**: Streamlined toolbar with Open, Export, Copy, and Reset
- **Triple-Pane Layout**: Source, Parameters, and Output panels
- **Source Panel**: Drag-and-drop image loading with preview
- **Parameters Panel**: 16 presets from subtle aesthetic to extreme corruption
- **Output Panel**: A/B comparison toggle between clean and glitched versions with individual export buttons

### Audio Effects Pipeline

**New Dramatic Effects:**
- 🌊 **Phase Modulation**: Horizontal scanline displacement with chaotic patterns
- 💫 **Amplitude Modulation**: Brightness and color intensity chaos
- 🎵 **Harmonic Distortion**: Frequency overtones that corrupt color decoding
- ⚡ **Scanline Corruption**: Random per-line artifacts (phase inversion, frequency spikes, black bars, noise bursts)

**Classic Effects:**
- Sync Wobble & Dropout
- White/Pink/Gaussian/Crackle Noise
- Distortion & Bitcrush
- Frequency Shift & Bandpass Filter
- Delay/Echo & Time Stretch

### 16 Glitch Presets

**Aesthetic Tier** (Image stays recognizable):
- **Vintage VHS** - Gentle tracking errors with warm crackle
- **Lo-Fi Aesthetic** - Light bit reduction with pink noise
- **Analog Warmth** - Minimal phase wobble, harmonic character
- **Retro Broadcast** - Slight sync wobble with frequency tint
- **Film Grain** - Gaussian texture overlay
- **Pastel Dream** - Color frequency shifts, dreamy phase mod
- **Subtle Glitch** - Sparse scanline artifacts, light crackle
- **Soft Corruption** - Controlled wobble, gentle scanline hits

**Moderate Tier** (Noticeable but controlled):
- **VHS Tracking Error** - Retro VHS glitches
- **Chromatic Aberration** - RGB separation effects
- **Signal Dropout** - Sync corruption artifacts

**Extreme Tier** (Heavy corruption):
- **Digital Meltdown** - 2-bit audio with heavy harmonics
- **Scanline Hell** - Maximum scanline corruption
- **Total Chaos** - ALL effects maxed out

### Professional Export Features
- **Multiple Formats**: PNG, JPEG, TIFF, WebP, BMP with format-specific options
- **Quick Size Presets**: Square 1080×1080, 2048×2048, HD 1920×1080, 4K 3840×2160, Instagram Story 1080×1920, Half/Double size
- **Custom Dimensions**: Manual width/height with aspect ratio lock
- **Filename Customization**: Add prefix/suffix, auto-increment to avoid overwrites
- **Quality Control**: Adjustable JPEG/WebP quality, optimization options
- **A+B Export**: Individual export buttons for both clean and glitched versions

### Professional UI
- Compact unified header with essential controls
- Full menu bar (File, Edit, View, Help)
- Keyboard shortcuts (Ctrl+O, E, C, R, 1, 2, /, Q)
- Real-time audio visualizer focused on SSTV frequencies (1100-2400 Hz)
- Live progressive decoding with scanline-by-scanline updates
- Detailed transmission status updates
- Copy to clipboard support

### SSTV Modes Supported
- Martin M1 (320×256)
- Martin M2 (160×256)
- Scottie S1 (320×256)
- Scottie S2 (320×256)
- Robot 36 (320×240)
- PD 90 (320×240)

## Installation

```bash
# Clone the repository
git clone https://github.com/mitchaiet/ScanScratch.git
cd ScanScratch

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python3 main.py
```

1. **Load Image**: Drag-and-drop or File → Open Image (Ctrl+O)
2. **Select Preset**: Choose from 16 presets ranging from subtle aesthetic to extreme chaos
3. **Adjust Effects**: Fine-tune individual effect parameters
4. **Transmit**: Click the large TRANSMIT button to encode, apply effects, and decode
5. **Watch**: Live audio playback with progressive scanline-by-scanline decoding
6. **Compare**: Use A/B toggle to instantly compare clean vs glitched output
7. **Export**: Click "Export A" or "Export B" buttons for enhanced export options

## Dependencies

- PyQt6 - GUI framework
- pysstv - SSTV encoding
- numpy - Audio processing
- scipy - Signal processing and filtering
- Pillow - Image handling
- sounddevice - Audio playback

## Technical Details

### Custom SSTV Decoder
Since no Python SSTV decoder exists, ScanScratch includes a custom streaming decoder implementation using scipy for FM demodulation and frequency analysis. The decoder uses floating-point precision throughout to avoid cumulative timing errors.

**Performance Optimizations**:
- Uses `signal.lfilter()` instead of `filtfilt()` for efficient single-pass bandpass filtering
- Processes 5+ million audio samples smoothly without crashes
- Hilbert transform for instantaneous frequency detection
- Progressive line-by-line decoding synchronized with audio playback

### Real-Time Audio Visualization
The visualizer focuses on SSTV frequency range (1100-2400 Hz) with markers for:
- Sync pulse (1200 Hz)
- Black level (1500 Hz)
- White level (2300 Hz)

Updates at 60 FPS with smooth interpolation for fluid animation showing the actual corrupted audio signal.

### A/B Comparison
Dual transmission system decodes both clean and affected versions simultaneously. The affected version plays with audio and live progressive decoding, while the clean version decodes silently in the background for instant comparison. Individual export buttons for each version provide flexible output options.

## License

MIT License - Feel free to use, modify, and distribute.

## Credits

Built with Claude Code by Anthropic.
