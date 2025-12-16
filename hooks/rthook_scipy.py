# Runtime hook to fix scipy import issues with PyInstaller
# This pre-imports scipy modules to avoid lazy loading issues

import sys

# Suppress the problematic scipy.stats import by pre-loading what we need
try:
    # Import scipy.signal directly without going through scipy.stats
    import scipy.signal._signaltools
    import scipy.signal._filter_design
    import scipy.signal._fir_filter_design
    import scipy.signal._spectral_py
    import scipy.fft
    import scipy.ndimage
except Exception:
    pass
