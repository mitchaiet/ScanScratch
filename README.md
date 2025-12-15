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

A professional PyQt6 application for creating glitch art through SSTV (Slow Scan Television) signal corruption.

## Features

### Triple-Pane Layout
- **Source Panel**: Drag-and-drop image loading with preview
- **Parameters Panel**: Real-time effect controls with 10 extreme presets
- **Output Panel**: A/B comparison toggle between clean and affected transmissions

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

### Extreme Presets
- **VHS Tracking Error** - Retro VHS glitches with phase modulation
- **Digital Meltdown** - 2-bit audio with heavy harmonics
- **Chromatic Aberration** - RGB separation effects
- **Signal Dropout** - Heavy sync corruption
- **Amplitude Chaos** - Extreme brightness modulation
- **Scanline Hell** - Maximum scanline corruption
- **Extreme Corruption** - ALL effects maxed out
- **Psychedelic Transmission** - Complex modulations
- **Glitch Storm** - 1-bit audio chaos

### Professional UI
- Full menu bar (File, Edit, View, Help)
- Keyboard shortcuts (Ctrl+O, E, C, R, 1, 2, /, Q)
- Export dialog with multiple formats (PNG, JPEG, TIFF, WebP, BMP)
- Real-time audio visualizer focused on SSTV frequencies
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
2. **Select Preset**: Choose from 10 extreme glitch presets
3. **Adjust Effects**: Fine-tune individual effect parameters
4. **Transmit**: Click TRANSMIT button to encode, corrupt, and decode
5. **Compare**: Use A/B toggle to compare clean vs affected output
6. **Export**: File → Export Image (Ctrl+E) to save your glitch art

## Dependencies

- PyQt6 - GUI framework
- pysstv - SSTV encoding
- numpy - Audio processing
- scipy - Signal processing and filtering
- Pillow - Image handling
- sounddevice - Audio playback

## Technical Details

### Custom SSTV Decoder
Since no Python SSTV decoder exists, ScanScratch includes a custom decoder implementation using scipy for FM demodulation and frequency analysis. The decoder uses floating-point precision throughout to avoid cumulative timing errors that cause diagonal skew.

### Real-Time Audio Visualization
The visualizer focuses on SSTV frequency range (1100-2400 Hz) with markers for:
- Sync pulse (1200 Hz)
- Black level (1500 Hz)
- White level (2300 Hz)

Updates at 60 FPS with smooth interpolation for fluid animation.

### A/B Comparison
Dual transmission system decodes both clean and affected versions simultaneously. The affected version plays with audio and live progressive decoding, while the clean version decodes silently in the background for instant comparison.

## License

MIT License - Feel free to use, modify, and distribute.

## Credits

Built with Claude Code by Anthropic.
