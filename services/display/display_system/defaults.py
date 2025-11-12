"""Display system constants and defaults.

Notes:
- The current presentation path uses a fixed 2x pixel scale; the
  MAX_SCALE_FACTOR and MIN_SCALE_FACTOR values are placeholders not used
  by the display service.
"""

BASE_WIDTH = 800
BASE_HEIGHT = 600
MAX_SCALE_FACTOR = 4.0  # not used by fixed 2x present path
MIN_SCALE_FACTOR = 0.5  # not used by fixed 2x present path
"""Whether the game window should start borderless on the primary monitor.

When True, the window is created without a frame (NOFRAME) sized to the
desktop resolution of the primary monitor. The logical render size (base
surface) is derived from the actual window size using the fixed pixel scale.
"""
BORDERLESS_DEFAULT = True
