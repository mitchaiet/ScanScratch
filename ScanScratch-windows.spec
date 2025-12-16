# -*- mode: python ; coding: utf-8 -*-
# Windows build spec for ScanScratch

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

# Add icon if it exists
icon_file = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None

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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=icon_file,
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
