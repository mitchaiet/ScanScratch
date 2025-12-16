# -*- mode: python ; coding: utf-8 -*-
# macOS build spec for ScanScratch

import os
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = []
binaries = []
hiddenimports = ['sounddevice', 'soundfile']

# Collect ALL of scipy to avoid lazy loading issues
scipy_ret = collect_all('scipy')
datas += scipy_ret[0]
binaries += scipy_ret[1]
hiddenimports += scipy_ret[2]

# Also collect pysstv
pysstv_ret = collect_all('pysstv')
datas += pysstv_ret[0]
binaries += pysstv_ret[1]
hiddenimports += pysstv_ret[2]

# Collect our src package
src_ret = collect_all('src')
datas += src_ret[0]
binaries += src_ret[1]
hiddenimports += src_ret[2]

# Collect moviepy for video export
moviepy_ret = collect_all('moviepy')
datas += moviepy_ret[0]
binaries += moviepy_ret[1]
hiddenimports += moviepy_ret[2]

# imageio is used by moviepy
imageio_ret = collect_all('imageio')
datas += imageio_ret[0]
binaries += imageio_ret[1]
hiddenimports += imageio_ret[2]

# Add icon if it exists
icon_file = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython', 'matplotlib', 'pandas', 'torch', 'tensorflow',
        'transformers', 'nltk', 'jedi', 'zmq', 'pygments',
        'moviepy', 'imageio', 'cv2', 'skimage', 'lxml',
        'pyarrow', 'tkinter', '_tkinter'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ScanScratch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScanScratch',
)
app = BUNDLE(
    coll,
    name='ScanScratch.app',
    icon=icon_file,
    bundle_identifier='com.scanscratch.app',
    info_plist={
        'CFBundleName': 'ScanScratch',
        'CFBundleDisplayName': 'ScanScratch',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'ScanScratch needs audio access for SSTV transmission playback.',
    },
)
