import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from pysstv.color import Robot36, MartinM1, ScottieS1
import wave
import logging
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import threading
import time
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import scipy.signal as signal
from scipy.io import wavfile
import matplotlib
from scipy import ndimage
matplotlib.use('TkAgg')
logging.getLogger('matplotlib.font_manager').disabled = True

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# List of required packages
REQUIRED_PACKAGES = ['pysstv', 'pyaudio', 'Pillow', 'pydub', 'simpleaudio', 'numpy', 'matplotlib']

def install_packages(packages):
    """Install the required packages using pip."""
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            logging.info(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def setup_venv():
    """Set up a virtual environment and install dependencies."""
    if not os.path.exists('venv'):
        logging.info("Creating virtual environment...")
        subprocess.check_call([sys.executable, '-m', 'venv', 'venv'])

    python_executable = os.path.join('venv', 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join('venv', 'bin', 'python')

    logging.info("Installing dependencies in virtual environment...")
    for package in REQUIRED_PACKAGES:
        subprocess.check_call([python_executable, '-m', 'pip', 'install', package])

def select_image():
    """Open a file dialog to select an image."""
    global image_label, encode_button
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png")])
    if file_path:
        image_label.configure(text=file_path)
        show_image_preview(file_path)
        encode_button.configure(state=tk.NORMAL)

def show_image_preview(file_path):
    """Display a preview of the selected image."""
    image = Image.open(file_path)
    image.thumbnail((320, 240))  # Ensure the image is resized appropriately
    photo = ImageTk.PhotoImage(image)
    image_preview.config(image=photo)
    image_preview.image = photo

def generate_audio():
    """Generate SSTV audio with proper VIS code and sync pulses."""
    try:
        image_path = image_label.cget("text")
        mode = mode_var.get()
        image = Image.open(image_path)
        
        # Convert and resize image
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if mode == 'Robot36':
            image = image.resize((320, 240))
            sstv = Robot36(image, samples_per_sec=44100, bits=16)
        elif mode == 'MartinM1':
            image = image.resize((320, 256))
            sstv = MartinM1(image, samples_per_sec=44100, bits=16)
        elif mode == 'ScottieS1':
            image = image.resize((320, 256))
            sstv = ScottieS1(image, samples_per_sec=44100, bits=16)
            
        # Enable VOX tone
        sstv.vox_enabled = True
        
        # Generate WAV file
        wav_file = "output.wav"
        sstv.write_wav(wav_file)
        
        # Load audio for playback
        global audio_segment
        audio_segment = AudioSegment.from_wav(wav_file)
        
        # Enable controls
        play_button.config(state=tk.NORMAL)
        pause_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.NORMAL)
        save_button.config(state=tk.NORMAL)
        
        messagebox.showinfo("Success", "Audio generated successfully!")
        
    except Exception as e:
        logging.error(f"Failed to generate audio: {e}", exc_info=True)
        messagebox.showerror("Error", f"Failed to generate audio: {e}")

def play_audio():
    """Play the audio file."""
    global playback, start_time
    if audio_segment:
        playback = _play_with_simpleaudio(audio_segment)
        start_time = time.time()
        update_scrubber()
        threading.Thread(target=update_visualizer).start()

def pause_audio():
    """Pause the audio playback."""
    if playback:
        playback.stop()

def stop_audio():
    """Stop the audio playback."""
    if playback:
        playback.stop()
        scrubber.set(0)

def update_scrubber():
    """Update the scrubber position."""
    if playback and playback.is_playing():
        elapsed_time = time.time() - start_time
        total_duration = len(audio_segment) / 1000.0  # Convert to seconds
        position = (elapsed_time / total_duration) * 100
        scrubber_control.set(position)
        root.after(100, update_scrubber)

def save_audio():
    """Save the audio file."""
    file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
    if file_path:
        audio_segment.export(file_path, format="wav")
        messagebox.showinfo("Success", "Audio saved successfully!")

def decode_robot36_line(audio_segment, start_time, elapsed_time, current_line):
    """Decode a single line of Robot36 SSTV transmission with improved sync and color accuracy."""
    try:
        # Constants for Robot36
        SAMPLE_RATE = 44100
        SYNC_FREQ = 1200
        PORCH_FREQ = 1500
        BLACK_FREQ = 1500
        WHITE_FREQ = 2300
        
        # Apply phase correction from slider
        phase_correction = phase_var.get() * np.pi / 180.0
        
        # Get audio samples for current line
        line_start = int(elapsed_time * SAMPLE_RATE)
        line_duration = int(0.15 * SAMPLE_RATE)  # 150ms per line
        line_audio = np.array(audio_segment.get_array_of_samples()[line_start:line_start + line_duration])
        
        if len(line_audio) < line_duration:
            return np.zeros((320, 3))
        
        # Apply phase correction and demodulate
        analytic_signal = signal.hilbert(line_audio.astype(float) / 32768.0)
        phase = np.unwrap(np.angle(analytic_signal)) + phase_correction
        frequency = np.diff(phase) / (2.0 * np.pi) * SAMPLE_RATE
        
        # Apply skew correction
        skew = skew_var.get()
        if skew != 0:
            samples_shift = int(skew * SAMPLE_RATE / 1000.0)
            frequency = np.roll(frequency, samples_shift)
        
        # Extract color components with proper timing
        def extract_color(start_ms, duration_ms):
            start_idx = int(start_ms * SAMPLE_RATE / 1000.0)
            samples = int(duration_ms * SAMPLE_RATE / 1000.0)
            if start_idx + samples > len(frequency):
                return np.zeros(320)
            
            color_samples = frequency[start_idx:start_idx + samples]
            color_samples = ndimage.gaussian_filter1d(color_samples, sigma=1.0)
            
            # Convert to pixel values
            pixels = np.interp(
                np.linspace(0, len(color_samples), 320),
                np.arange(len(color_samples)),
                color_samples
            )
            
            # Convert frequency to color intensity with gamma correction
            pixels = np.clip((pixels - BLACK_FREQ) / (WHITE_FREQ - BLACK_FREQ), 0, 1)
            pixels = np.power(pixels, 1/2.2) * 255
            return pixels.astype(np.uint8)
        
        # Extract RGB with proper timing
        r = extract_color(9, 43.3)    # Start after sync pulse
        g = extract_color(53.3, 43.3) # Start after red
        b = extract_color(97.6, 43.3) # Start after green
        
        return np.column_stack((r, g, b))
        
    except Exception as e:
        logging.error(f"Error decoding line {current_line}: {e}")
        return np.zeros((320, 3))

def update_visualizer():
    """Update the visualizer with the current audio data."""
    if not hasattr(update_visualizer, 'image_data'):
        update_visualizer.image_data = np.zeros((240, 320, 3), dtype=np.uint8)
        update_visualizer.last_line = -1
    
    while playback and playback.is_playing():
        try:
            # Get current position in audio
            elapsed_time = time.time() - start_time
            
            # Robot36 timing constants
            LINE_TIME_MS = 150  # Each line takes 150ms
            line_duration = LINE_TIME_MS / 1000.0
            
            # Calculate current line
            current_line = int(elapsed_time / line_duration)
            if 0 <= current_line < 240 and current_line != update_visualizer.last_line:
                line_data = decode_robot36_line(
                    audio_segment, 
                    start_time, 
                    current_line * line_duration,
                    current_line
                )
                update_visualizer.image_data[current_line] = line_data
                update_visualizer.last_line = current_line
            
                # Update the display
                ax.clear()
                ax.imshow(update_visualizer.image_data)
                ax.axis('off')
                canvas.draw()
            
            time.sleep(0.001)  # Shorter sleep for more precise timing
            
        except Exception as e:
            logging.error(f"Visualizer error: {e}")
            time.sleep(0.001)

def create_ui():
    """Create the main UI layout with improved organization."""
    # Make all UI elements global so they can be accessed from other functions
    global root, image_preview, image_label, encode_button, play_button, pause_button
    global stop_button, save_button, fig, ax, canvas, phase_var, skew_var
    global scrubber_control, mode_var, progress_var
    
    root = tk.Tk()
    root.title("SSTV Transmitter")
    
    # Main content frame
    main_frame = ttk.Frame(root)
    main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
    # Input frame (left side)
    input_frame = ttk.LabelFrame(main_frame, text="Input Image")
    input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    
    # Image selection and encoding controls
    button_frame = ttk.Frame(input_frame)
    button_frame.pack(fill=tk.X, pady=5)
    
    select_button = ttk.Button(button_frame, text="Select Image", command=select_image)
    select_button.pack(side=tk.LEFT, padx=5)
    
    encode_button = ttk.Button(button_frame, text="Encode Audio", command=generate_audio, state=tk.DISABLED)
    encode_button.pack(side=tk.LEFT, padx=5)
    
    image_label = ttk.Label(input_frame)
    image_label.pack()
    
    image_preview = ttk.Label(input_frame)
    image_preview.pack(pady=5)
    
    # Preview frame (right side)
    preview_frame = ttk.LabelFrame(main_frame, text="SSTV Preview")
    preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    
    # Create matplotlib figure for preview
    fig, ax = plt.subplots(figsize=(6, 4))
    canvas = FigureCanvasTkAgg(fig, master=preview_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Bottom control panel
    control_frame = ttk.LabelFrame(root, text="Controls")
    control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
    
    # Control variables initialization
    mode_var = tk.StringVar(value='Robot36')
    phase_var = tk.DoubleVar(value=0.0)
    skew_var = tk.DoubleVar(value=0.0)
    
    # Mode selection
    mode_frame = ttk.Frame(control_frame)
    mode_frame.pack(fill=tk.X, pady=2)
    
    ttk.Label(mode_frame, text="SSTV Mode:").pack(side=tk.LEFT)
    mode_combo = ttk.Combobox(mode_frame, textvariable=mode_var, values=['Robot36', 'MartinM1', 'ScottieS1'], width=15)
    mode_combo.pack(side=tk.LEFT, padx=5)
    
    # Phase control
    phase_frame = ttk.Frame(control_frame)
    phase_frame.pack(fill=tk.X, pady=2)
    
    ttk.Label(phase_frame, text="Phase:").pack(side=tk.LEFT)
    phase_slider = ttk.Scale(phase_frame, from_=-180, to=180, variable=phase_var, orient=tk.HORIZONTAL)
    phase_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    # Skew control
    skew_frame = ttk.Frame(control_frame)
    skew_frame.pack(fill=tk.X, pady=2)
    
    ttk.Label(skew_frame, text="Skew:").pack(side=tk.LEFT)
    skew_slider = ttk.Scale(skew_frame, from_=-45, to=45, variable=skew_var, orient=tk.HORIZONTAL)
    skew_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    # Transport controls
    transport_frame = ttk.Frame(control_frame)
    transport_frame.pack(fill=tk.X, pady=2)
    
    play_button = ttk.Button(transport_frame, text="Play", command=play_audio, state=tk.DISABLED)
    play_button.pack(side=tk.LEFT, padx=2)
    
    pause_button = ttk.Button(transport_frame, text="Pause", command=pause_audio, state=tk.DISABLED)
    pause_button.pack(side=tk.LEFT, padx=2)
    
    stop_button = ttk.Button(transport_frame, text="Stop", command=stop_audio, state=tk.DISABLED)
    stop_button.pack(side=tk.LEFT, padx=2)
    
    save_button = ttk.Button(transport_frame, text="Save Audio", command=save_audio, state=tk.DISABLED)
    save_button.pack(side=tk.LEFT, padx=2)
    
    # Scrubber
    scrubber_frame = ttk.Frame(control_frame)
    scrubber_frame.pack(fill=tk.X, pady=2)
    
    scrubber_control = ttk.Scale(scrubber_frame, from_=0, to=100, orient=tk.HORIZONTAL)
    scrubber_control.pack(fill=tk.X, expand=True, padx=5)
    
    # Progress bar
    progress_var = tk.DoubleVar()
    progress = ttk.Progressbar(control_frame, variable=progress_var, maximum=100)
    progress.pack(fill=tk.X, pady=2)
    
    # Don't return anything since we're using global variables
    return None

def main():
    """Main function to set up the GUI."""
    setup_venv()

    if not os.environ.get('VIRTUAL_ENV'):
        python_executable = os.path.join('venv', 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join('venv', 'bin', 'python')
        script_path = os.path.abspath(__file__)
        subprocess.check_call([python_executable, script_path])
        sys.exit()

    # Just call create_ui() without assignment since we're using global variables
    create_ui()
    root.mainloop()

if __name__ == "__main__":
    main()
