import os
import sys

# Ensure SDL uses nearest-neighbor scaling for any renderer-driven scaling.
# Must be set before importing any module that imports pygame.
os.environ['SDL_RENDER_SCALE_QUALITY'] = '0'

from states.state_manager import StateManager

if __name__ == "__main__":
    game = StateManager()
    game.run()
