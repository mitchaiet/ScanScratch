"""
py2app setup script for ScanScratch
Usage: python setup.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt6', 'numpy', 'scipy', 'PIL', 'pysstv', 'sounddevice'],
    'includes': ['sounddevice', 'soundfile'],
    'excludes': ['tkinter', 'matplotlib', 'pandas'],
    # 'iconfile': 'icon.icns',  # Optional: add an icon
    'plist': {
        'CFBundleName': 'ScanScratch',
        'CFBundleDisplayName': 'ScanScratch',
        'CFBundleIdentifier': 'com.scanscratch.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'ScanScratch needs audio access for SSTV transmission playback.',
    }
}

setup(
    app=APP,
    name='ScanScratch',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
