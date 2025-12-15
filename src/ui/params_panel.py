"""Parameters panel with effect controls."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
import numpy as np

from .audio_visualizer import AudioVisualizer


class EffectSlider(QWidget):
    """A labeled slider for effect parameters."""

    value_changed = pyqtSignal(float)

    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        default: float,
        suffix: str = "",
        decimals: int = 0,
        tooltip: str = "",
    ):
        super().__init__()
        self._min = min_val
        self._max = max_val
        self._decimals = decimals
        self._suffix = suffix

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Label
        self.label = QLabel(label)
        self.label.setFixedWidth(100)
        if tooltip:
            self.label.setToolTip(tooltip)
            self.setToolTip(tooltip)
        layout.addWidget(self.label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(self._value_to_slider(default))
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, stretch=1)

        # Value display
        self.value_label = QLabel()
        self.value_label.setFixedWidth(60)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._update_value_label(default)
        layout.addWidget(self.value_label)

    def _value_to_slider(self, val: float) -> int:
        return int((val - self._min) / (self._max - self._min) * 100)

    def _slider_to_value(self, slider_val: int) -> float:
        return self._min + (slider_val / 100) * (self._max - self._min)

    def _on_slider_changed(self, slider_val: int):
        value = self._slider_to_value(slider_val)
        self._update_value_label(value)
        self.value_changed.emit(value)

    def _update_value_label(self, value: float):
        if self._decimals == 0:
            text = f"{int(value)}{self._suffix}"
        else:
            text = f"{value:.{self._decimals}f}{self._suffix}"
        self.value_label.setText(text)

    def value(self) -> float:
        return self._slider_to_value(self.slider.value())

    def set_value(self, val: float):
        self.slider.setValue(self._value_to_slider(val))


class EffectGroup(QGroupBox):
    """A group of effect controls with enable checkbox."""

    def __init__(self, title: str, enabled: bool = False):
        super().__init__()
        self.setTitle("")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 12)
        self._layout.setSpacing(6)

        # Header with enable checkbox
        header = QHBoxLayout()
        self.enable_checkbox = QCheckBox(title)
        self.enable_checkbox.setChecked(enabled)
        self.enable_checkbox.toggled.connect(self._on_enabled_changed)
        header.addWidget(self.enable_checkbox)
        header.addStretch()
        self._layout.addLayout(header)

        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 0)
        self.content_layout.setSpacing(4)
        self._layout.addWidget(self.content)

        self._on_enabled_changed(enabled)

    def _on_enabled_changed(self, enabled: bool):
        self.content.setEnabled(enabled)
        # Dim the content when disabled
        self.content.setStyleSheet("" if enabled else "color: #555;")

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def is_enabled(self) -> bool:
        return self.enable_checkbox.isChecked()


class ParamsPanel(QWidget):
    """Parameters panel with SSTV settings and effect controls."""

    transmit_requested = pyqtSignal()

    # Glitch presets - tuned for maximum visual impact
    PRESETS = {
        "Clean": {},

        # ===== AESTHETIC PRESETS (Image Still Recognizable) =====
        "Vintage VHS": {
            "noise_enabled": True, "noise_amount": 12, "noise_type": "Crackle",
            "syncwobble_enabled": True, "syncwobble_amount": 18, "syncwobble_freq": 2.5,
            "phasemod_enabled": True, "phasemod_depth": 15, "phasemod_rate": 3,
            "distortion_enabled": True, "distortion_drive": 25, "distortion_clip": 70,
        },
        "Lo-Fi Aesthetic": {
            "bitcrush_enabled": True, "bitcrush_bits": 6, "bitcrush_rate": 22050,
            "noise_enabled": True, "noise_amount": 8, "noise_type": "Pink",
            "harmonic_enabled": True, "harmonic_amount": 20, "harmonic_count": 2,
        },
        "Analog Warmth": {
            "phasemod_enabled": True, "phasemod_depth": 10, "phasemod_rate": 1.5,
            "harmonic_enabled": True, "harmonic_amount": 15, "harmonic_count": 2,
            "noise_enabled": True, "noise_amount": 5, "noise_type": "Pink",
        },
        "Retro Broadcast": {
            "syncwobble_enabled": True, "syncwobble_amount": 12, "syncwobble_freq": 1.8,
            "freqshift_enabled": True, "freqshift_hz": 45,
            "noise_enabled": True, "noise_amount": 10, "noise_type": "Gaussian",
        },
        "Film Grain": {
            "noise_enabled": True, "noise_amount": 18, "noise_type": "Gaussian",
            "harmonic_enabled": True, "harmonic_amount": 10, "harmonic_count": 1,
            "bitcrush_enabled": True, "bitcrush_bits": 7, "bitcrush_rate": 33075,
        },
        "Pastel Dream": {
            "freqshift_enabled": True, "freqshift_hz": 80,
            "phasemod_enabled": True, "phasemod_depth": 20, "phasemod_rate": 5,
            "harmonic_enabled": True, "harmonic_amount": 25, "harmonic_count": 2,
        },
        "Subtle Glitch": {
            "scanline_enabled": True, "scanline_freq": 8, "scanline_intensity": 35,
            "phasemod_enabled": True, "phasemod_depth": 12, "phasemod_rate": 6,
            "noise_enabled": True, "noise_amount": 6, "noise_type": "Crackle",
        },
        "Soft Corruption": {
            "syncwobble_enabled": True, "syncwobble_amount": 22, "syncwobble_freq": 4,
            "scanline_enabled": True, "scanline_freq": 12, "scanline_intensity": 45,
            "harmonic_enabled": True, "harmonic_amount": 18, "harmonic_count": 2,
        },

        # ===== MODERATE PRESETS (Noticeable but Controlled) =====
        "VHS Tracking Error": {
            "phasemod_enabled": True, "phasemod_depth": 40, "phasemod_rate": 4.5,
            "syncwobble_enabled": True, "syncwobble_amount": 35, "syncwobble_freq": 3.5,
            "noise_enabled": True, "noise_amount": 25, "noise_type": "Crackle",
            "distortion_enabled": True, "distortion_drive": 35, "distortion_clip": 65,
        },
        "Chromatic Aberration": {
            "phasemod_enabled": True, "phasemod_depth": 30, "phasemod_rate": 12,
            "freqshift_enabled": True, "freqshift_hz": 150,
            "delay_enabled": True, "delay_time": 3, "delay_feedback": 25, "delay_mix": 40,
            "harmonic_enabled": True, "harmonic_amount": 30, "harmonic_count": 2,
        },
        "Signal Dropout": {
            "syncdropout_enabled": True, "syncdropout_prob": 20, "syncdropout_duration": 8,
            "scanline_enabled": True, "scanline_freq": 18, "scanline_intensity": 55,
            "noise_enabled": True, "noise_amount": 30, "noise_type": "Crackle",
        },

        # ===== EXTREME PRESETS (Heavy Glitch) =====
        "Digital Meltdown": {
            "bitcrush_enabled": True, "bitcrush_bits": 2, "bitcrush_rate": 4400,
            "harmonic_enabled": True, "harmonic_amount": 70, "harmonic_count": 4,
            "scanline_enabled": True, "scanline_freq": 35, "scanline_intensity": 85,
            "freqshift_enabled": True, "freqshift_hz": -150,
        },
        "Scanline Hell": {
            "scanline_enabled": True, "scanline_freq": 45, "scanline_intensity": 95,
            "syncwobble_enabled": True, "syncwobble_amount": 80, "syncwobble_freq": 12,
            "bitcrush_enabled": True, "bitcrush_bits": 3, "bitcrush_rate": 6000,
            "noise_enabled": True, "noise_amount": 55, "noise_type": "White",
        },
        "Total Chaos": {
            "phasemod_enabled": True, "phasemod_depth": 85, "phasemod_rate": 10,
            "ampmod_enabled": True, "ampmod_depth": 70, "ampmod_rate": 14,
            "scanline_enabled": True, "scanline_freq": 40, "scanline_intensity": 90,
            "noise_enabled": True, "noise_amount": 75, "noise_type": "White",
            "bitcrush_enabled": True, "bitcrush_bits": 2, "bitcrush_rate": 3300,
            "distortion_enabled": True, "distortion_drive": 90, "distortion_clip": 35,
        },
    }

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Title
        title = QLabel("PARAMETERS")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # Scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(12)

        # Presets
        preset_group = QGroupBox("Glitch Presets")
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        preset_layout.addWidget(self.preset_combo)
        scroll_layout.addWidget(preset_group)

        # SSTV Settings
        sstv_group = QGroupBox("SSTV Mode")
        sstv_layout = QVBoxLayout(sstv_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Martin M1",
            "Martin M2",
            "Scottie S1",
            "Scottie S2",
            "Robot 36",
            "PD 90",
        ])
        sstv_layout.addWidget(self.mode_combo)
        scroll_layout.addWidget(sstv_group)

        # Phase Modulation Effect - horizontal scanline displacement
        self.phasemod_group = EffectGroup("Phase Modulation", enabled=False)
        self.phasemod_depth = EffectSlider("Depth", 0, 100, 50, "%",
            tooltip="How far to displace scanlines horizontally")
        self.phasemod_group.add_widget(self.phasemod_depth)
        self.phasemod_rate = EffectSlider("Rate", 0.5, 20, 8, " Hz", decimals=1,
            tooltip="Speed of horizontal displacement modulation")
        self.phasemod_group.add_widget(self.phasemod_rate)
        scroll_layout.addWidget(self.phasemod_group)

        # Amplitude Modulation Effect - brightness chaos
        self.ampmod_group = EffectGroup("Amplitude Modulation", enabled=False)
        self.ampmod_depth = EffectSlider("Depth", 0, 100, 50, "%",
            tooltip="Intensity of brightness/color modulation")
        self.ampmod_group.add_widget(self.ampmod_depth)
        self.ampmod_rate = EffectSlider("Rate", 1, 25, 12, " Hz", decimals=1,
            tooltip="Speed of amplitude modulation")
        self.ampmod_group.add_widget(self.ampmod_rate)
        scroll_layout.addWidget(self.ampmod_group)

        # Scanline Corruption Effect - random scanline artifacts
        self.scanline_group = EffectGroup("Scanline Corruption", enabled=False)
        self.scanline_freq = EffectSlider("Frequency", 0, 100, 15, "%",
            tooltip="How many scanlines to corrupt")
        self.scanline_group.add_widget(self.scanline_freq)
        self.scanline_intensity = EffectSlider("Intensity", 0, 100, 70, "%",
            tooltip="Severity of corruption artifacts")
        self.scanline_group.add_widget(self.scanline_intensity)
        scroll_layout.addWidget(self.scanline_group)

        # Harmonic Distortion Effect - frequency artifacts
        self.harmonic_group = EffectGroup("Harmonic Distortion", enabled=False)
        self.harmonic_amount = EffectSlider("Amount", 0, 100, 50, "%",
            tooltip="Amount of harmonic overtones to add")
        self.harmonic_group.add_widget(self.harmonic_amount)
        self.harmonic_count = EffectSlider("Harmonics", 1, 5, 3, "",
            tooltip="Number of harmonic overtones (1-5)")
        self.harmonic_group.add_widget(self.harmonic_count)
        scroll_layout.addWidget(self.harmonic_group)

        # Sync Wobble Effect - causes scanline displacement
        self.syncwobble_group = EffectGroup("Sync Wobble", enabled=False)
        self.syncwobble_amount = EffectSlider("Amount", 0, 100, 50, "%",
            tooltip="Intensity of horizontal scanline wobble")
        self.syncwobble_group.add_widget(self.syncwobble_amount)
        self.syncwobble_freq = EffectSlider("Speed", 0.5, 20, 5, " Hz", decimals=1,
            tooltip="How fast the wobble oscillates")
        self.syncwobble_group.add_widget(self.syncwobble_freq)
        scroll_layout.addWidget(self.syncwobble_group)

        # Sync Dropout Effect - random line corruption
        self.syncdropout_group = EffectGroup("Sync Dropout", enabled=False)
        self.syncdropout_prob = EffectSlider("Frequency", 0, 100, 15, "%",
            tooltip="How often sync dropouts occur")
        self.syncdropout_group.add_widget(self.syncdropout_prob)
        self.syncdropout_duration = EffectSlider("Duration", 1, 20, 5, " ms",
            tooltip="Length of each dropout")
        self.syncdropout_group.add_widget(self.syncdropout_duration)
        scroll_layout.addWidget(self.syncdropout_group)

        # Noise Effect - improved defaults for more impact
        self.noise_group = EffectGroup("Noise", enabled=False)
        self.noise_amount = EffectSlider("Amount", 0, 100, 35, "%",
            tooltip="Volume of noise added to the signal")
        self.noise_group.add_widget(self.noise_amount)

        noise_type_layout = QHBoxLayout()
        type_label = QLabel("Type")
        type_label.setToolTip("Type of noise: White (hiss), Pink (warmer), Gaussian (natural), Crackle (vinyl)")
        noise_type_layout.addWidget(type_label)
        self.noise_type = QComboBox()
        self.noise_type.addItems(["White", "Pink", "Gaussian", "Crackle"])
        self.noise_type.setToolTip("Type of noise: White (hiss), Pink (warmer), Gaussian (natural), Crackle (vinyl)")
        noise_type_layout.addWidget(self.noise_type, stretch=1)
        noise_container = QWidget()
        noise_container.setLayout(noise_type_layout)
        self.noise_group.add_widget(noise_container)
        scroll_layout.addWidget(self.noise_group)

        # Distortion Effect - more aggressive defaults
        self.distortion_group = EffectGroup("Distortion", enabled=False)
        self.distortion_drive = EffectSlider("Drive", 0, 100, 50, "%",
            tooltip="Amount of gain applied before clipping")
        self.distortion_group.add_widget(self.distortion_drive)
        self.distortion_clip = EffectSlider("Clip", 0, 100, 60, "%",
            tooltip="Clipping threshold - lower = harsher distortion")
        self.distortion_group.add_widget(self.distortion_clip)
        scroll_layout.addWidget(self.distortion_group)

        # Bitcrush Effect - lower defaults for more glitch
        self.bitcrush_group = EffectGroup("Bitcrush", enabled=False)
        self.bitcrush_bits = EffectSlider("Bit Depth", 1, 16, 5, " bits",
            tooltip="Audio bit depth - lower = more digital degradation")
        self.bitcrush_group.add_widget(self.bitcrush_bits)
        self.bitcrush_rate = EffectSlider("Sample Rate", 1000, 44100, 11025, " Hz",
            tooltip="Target sample rate - lower = more lo-fi")
        self.bitcrush_group.add_widget(self.bitcrush_rate)
        scroll_layout.addWidget(self.bitcrush_group)

        # Frequency Shift Effect - wider range
        self.freqshift_group = EffectGroup("Frequency Shift", enabled=False)
        self.freqshift_hz = EffectSlider("Shift", -500, 500, 100, " Hz",
            tooltip="Shift all frequencies up/down - creates color distortion")
        self.freqshift_group.add_widget(self.freqshift_hz)
        scroll_layout.addWidget(self.freqshift_group)

        # Bandpass Filter
        self.bandpass_group = EffectGroup("Bandpass Filter", enabled=False)
        self.bandpass_low = EffectSlider("Low Cut", 100, 2000, 500, " Hz",
            tooltip="Remove frequencies below this value")
        self.bandpass_group.add_widget(self.bandpass_low)
        self.bandpass_high = EffectSlider("High Cut", 1000, 10000, 2500, " Hz",
            tooltip="Remove frequencies above this value")
        self.bandpass_group.add_widget(self.bandpass_high)
        scroll_layout.addWidget(self.bandpass_group)

        # Delay Effect - more feedback for drama
        self.delay_group = EffectGroup("Delay / Echo", enabled=False)
        self.delay_time = EffectSlider("Time", 3, 500, 60, " ms",
            tooltip="Time between echoes")
        self.delay_group.add_widget(self.delay_time)
        self.delay_feedback = EffectSlider("Feedback", 0, 90, 65, "%",
            tooltip="Amount of signal fed back - higher = more repeats")
        self.delay_group.add_widget(self.delay_feedback)
        self.delay_mix = EffectSlider("Mix", 0, 100, 45, "%",
            tooltip="Blend between original and delayed signal")
        self.delay_group.add_widget(self.delay_mix)
        scroll_layout.addWidget(self.delay_group)

        # Time Stretch Effect - wider range
        self.timestretch_group = EffectGroup("Time Stretch", enabled=False)
        self.timestretch_rate = EffectSlider("Rate", 0.5, 2.5, 1.0, "x", decimals=2,
            tooltip="Playback speed - also changes pitch")
        self.timestretch_group.add_widget(self.timestretch_rate)
        scroll_layout.addWidget(self.timestretch_group)

        # Spacer
        scroll_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)

        # Audio visualizer (replaces progress bar)
        self.audio_visualizer = AudioVisualizer()
        main_layout.addWidget(self.audio_visualizer)

        # Transmit button
        self.transmit_button = QPushButton("TRANSMIT")
        self.transmit_button.setObjectName("transmitButton")
        self.transmit_button.clicked.connect(self.transmit_requested.emit)
        self.transmit_button.setEnabled(False)
        main_layout.addWidget(self.transmit_button)

    def set_transmit_enabled(self, enabled: bool):
        """Enable or disable the transmit button."""
        self.transmit_button.setEnabled(enabled)

    def set_progress(self, value: int):
        """Set progress value (0-100)."""
        self.audio_visualizer.set_progress(value)

    def set_audio_data(self, audio_data: np.ndarray, sample_rate: int):
        """Set audio data for visualization."""
        self.audio_visualizer.set_audio(audio_data, sample_rate)
        self.audio_visualizer.start_playback()

    def stop_audio_visualization(self):
        """Stop audio visualization."""
        self.audio_visualizer.stop_playback()

    def _apply_preset(self, preset_name: str):
        """Apply a preset configuration."""
        if preset_name not in self.PRESETS:
            return

        preset = self.PRESETS[preset_name]

        # Disable all effects first if it's the "Clean" preset
        if not preset:
            self.phasemod_group.enable_checkbox.setChecked(False)
            self.ampmod_group.enable_checkbox.setChecked(False)
            self.scanline_group.enable_checkbox.setChecked(False)
            self.harmonic_group.enable_checkbox.setChecked(False)
            self.syncwobble_group.enable_checkbox.setChecked(False)
            self.syncdropout_group.enable_checkbox.setChecked(False)
            self.noise_group.enable_checkbox.setChecked(False)
            self.distortion_group.enable_checkbox.setChecked(False)
            self.bitcrush_group.enable_checkbox.setChecked(False)
            self.freqshift_group.enable_checkbox.setChecked(False)
            self.bandpass_group.enable_checkbox.setChecked(False)
            self.delay_group.enable_checkbox.setChecked(False)
            self.timestretch_group.enable_checkbox.setChecked(False)
            return

        # Apply phase modulation settings
        if "phasemod_enabled" in preset:
            self.phasemod_group.enable_checkbox.setChecked(preset["phasemod_enabled"])
        if "phasemod_depth" in preset:
            self.phasemod_depth.set_value(preset["phasemod_depth"])
        if "phasemod_rate" in preset:
            self.phasemod_rate.set_value(preset["phasemod_rate"])

        # Apply amplitude modulation settings
        if "ampmod_enabled" in preset:
            self.ampmod_group.enable_checkbox.setChecked(preset["ampmod_enabled"])
        if "ampmod_depth" in preset:
            self.ampmod_depth.set_value(preset["ampmod_depth"])
        if "ampmod_rate" in preset:
            self.ampmod_rate.set_value(preset["ampmod_rate"])

        # Apply scanline corruption settings
        if "scanline_enabled" in preset:
            self.scanline_group.enable_checkbox.setChecked(preset["scanline_enabled"])
        if "scanline_freq" in preset:
            self.scanline_freq.set_value(preset["scanline_freq"])
        if "scanline_intensity" in preset:
            self.scanline_intensity.set_value(preset["scanline_intensity"])

        # Apply harmonic distortion settings
        if "harmonic_enabled" in preset:
            self.harmonic_group.enable_checkbox.setChecked(preset["harmonic_enabled"])
        if "harmonic_amount" in preset:
            self.harmonic_amount.set_value(preset["harmonic_amount"])
        if "harmonic_count" in preset:
            self.harmonic_count.set_value(preset["harmonic_count"])

        # Apply sync wobble settings
        if "syncwobble_enabled" in preset:
            self.syncwobble_group.enable_checkbox.setChecked(preset["syncwobble_enabled"])
        if "syncwobble_amount" in preset:
            self.syncwobble_amount.set_value(preset["syncwobble_amount"])
        if "syncwobble_freq" in preset:
            self.syncwobble_freq.set_value(preset["syncwobble_freq"])

        # Apply sync dropout settings
        if "syncdropout_enabled" in preset:
            self.syncdropout_group.enable_checkbox.setChecked(preset["syncdropout_enabled"])
        if "syncdropout_prob" in preset:
            self.syncdropout_prob.set_value(preset["syncdropout_prob"])
        if "syncdropout_duration" in preset:
            self.syncdropout_duration.set_value(preset["syncdropout_duration"])

        # Apply noise settings
        if "noise_enabled" in preset:
            self.noise_group.enable_checkbox.setChecked(preset["noise_enabled"])
        if "noise_amount" in preset:
            self.noise_amount.set_value(preset["noise_amount"])
        if "noise_type" in preset:
            idx = self.noise_type.findText(preset["noise_type"])
            if idx >= 0:
                self.noise_type.setCurrentIndex(idx)

        # Apply distortion settings
        if "distortion_enabled" in preset:
            self.distortion_group.enable_checkbox.setChecked(preset["distortion_enabled"])
        if "distortion_drive" in preset:
            self.distortion_drive.set_value(preset["distortion_drive"])
        if "distortion_clip" in preset:
            self.distortion_clip.set_value(preset["distortion_clip"])

        # Apply bitcrush settings
        if "bitcrush_enabled" in preset:
            self.bitcrush_group.enable_checkbox.setChecked(preset["bitcrush_enabled"])
        if "bitcrush_bits" in preset:
            self.bitcrush_bits.set_value(preset["bitcrush_bits"])
        if "bitcrush_rate" in preset:
            self.bitcrush_rate.set_value(preset["bitcrush_rate"])

        # Apply frequency shift settings
        if "freqshift_enabled" in preset:
            self.freqshift_group.enable_checkbox.setChecked(preset["freqshift_enabled"])
        if "freqshift_hz" in preset:
            self.freqshift_hz.set_value(preset["freqshift_hz"])

        # Apply bandpass settings
        if "bandpass_enabled" in preset:
            self.bandpass_group.enable_checkbox.setChecked(preset["bandpass_enabled"])
        if "bandpass_low" in preset:
            self.bandpass_low.set_value(preset["bandpass_low"])
        if "bandpass_high" in preset:
            self.bandpass_high.set_value(preset["bandpass_high"])

        # Apply delay settings
        if "delay_enabled" in preset:
            self.delay_group.enable_checkbox.setChecked(preset["delay_enabled"])
        if "delay_time" in preset:
            self.delay_time.set_value(preset["delay_time"])
        if "delay_feedback" in preset:
            self.delay_feedback.set_value(preset["delay_feedback"])
        if "delay_mix" in preset:
            self.delay_mix.set_value(preset["delay_mix"])

        # Apply time stretch settings
        if "timestretch_enabled" in preset:
            self.timestretch_group.enable_checkbox.setChecked(preset["timestretch_enabled"])
        if "timestretch_rate" in preset:
            self.timestretch_rate.set_value(preset["timestretch_rate"])

        # Disable effects not in the preset
        if "phasemod_enabled" not in preset:
            self.phasemod_group.enable_checkbox.setChecked(False)
        if "ampmod_enabled" not in preset:
            self.ampmod_group.enable_checkbox.setChecked(False)
        if "scanline_enabled" not in preset:
            self.scanline_group.enable_checkbox.setChecked(False)
        if "harmonic_enabled" not in preset:
            self.harmonic_group.enable_checkbox.setChecked(False)
        if "syncwobble_enabled" not in preset:
            self.syncwobble_group.enable_checkbox.setChecked(False)
        if "syncdropout_enabled" not in preset:
            self.syncdropout_group.enable_checkbox.setChecked(False)
        if "noise_enabled" not in preset:
            self.noise_group.enable_checkbox.setChecked(False)
        if "distortion_enabled" not in preset:
            self.distortion_group.enable_checkbox.setChecked(False)
        if "bitcrush_enabled" not in preset:
            self.bitcrush_group.enable_checkbox.setChecked(False)
        if "freqshift_enabled" not in preset:
            self.freqshift_group.enable_checkbox.setChecked(False)
        if "bandpass_enabled" not in preset:
            self.bandpass_group.enable_checkbox.setChecked(False)
        if "delay_enabled" not in preset:
            self.delay_group.enable_checkbox.setChecked(False)
        if "timestretch_enabled" not in preset:
            self.timestretch_group.enable_checkbox.setChecked(False)

    def get_effect_settings(self) -> dict:
        """Get current effect settings as a dictionary."""
        mode_text = self.mode_combo.currentText()
        mode_map = {
            "Martin M1": "MartinM1",
            "Martin M2": "MartinM2",
            "Scottie S1": "ScottieS1",
            "Scottie S2": "ScottieS2",
            "Robot 36": "Robot36",
            "PD 90": "PD90",
        }

        return {
            "sstv_mode": mode_map.get(mode_text, "MartinM1"),

            "phasemod_enabled": self.phasemod_group.is_enabled(),
            "phasemod_depth": self.phasemod_depth.value() / 100,
            "phasemod_rate": self.phasemod_rate.value(),

            "ampmod_enabled": self.ampmod_group.is_enabled(),
            "ampmod_depth": self.ampmod_depth.value() / 100,
            "ampmod_rate": self.ampmod_rate.value(),

            "scanline_enabled": self.scanline_group.is_enabled(),
            "scanline_freq": self.scanline_freq.value() / 100,
            "scanline_intensity": self.scanline_intensity.value() / 100,

            "harmonic_enabled": self.harmonic_group.is_enabled(),
            "harmonic_amount": self.harmonic_amount.value() / 100,
            "harmonic_count": int(self.harmonic_count.value()),

            "syncwobble_enabled": self.syncwobble_group.is_enabled(),
            "syncwobble_amount": self.syncwobble_amount.value() / 100,
            "syncwobble_freq": self.syncwobble_freq.value(),

            "syncdropout_enabled": self.syncdropout_group.is_enabled(),
            "syncdropout_prob": self.syncdropout_prob.value() / 100,
            "syncdropout_duration": self.syncdropout_duration.value(),

            "noise_enabled": self.noise_group.is_enabled(),
            "noise_amount": self.noise_amount.value() / 100,
            "noise_type": self.noise_type.currentText().lower(),

            "distortion_enabled": self.distortion_group.is_enabled(),
            "distortion_drive": self.distortion_drive.value() / 100,
            "distortion_clip": self.distortion_clip.value() / 100,

            "bitcrush_enabled": self.bitcrush_group.is_enabled(),
            "bitcrush_bits": int(self.bitcrush_bits.value()),
            "bitcrush_rate": int(self.bitcrush_rate.value()),

            "freqshift_enabled": self.freqshift_group.is_enabled(),
            "freqshift_hz": self.freqshift_hz.value(),

            "bandpass_enabled": self.bandpass_group.is_enabled(),
            "bandpass_low": self.bandpass_low.value(),
            "bandpass_high": self.bandpass_high.value(),

            "delay_enabled": self.delay_group.is_enabled(),
            "delay_time_ms": self.delay_time.value(),
            "delay_feedback": self.delay_feedback.value() / 100,
            "delay_mix": self.delay_mix.value() / 100,

            "timestretch_enabled": self.timestretch_group.is_enabled(),
            "timestretch_rate": self.timestretch_rate.value(),
        }
