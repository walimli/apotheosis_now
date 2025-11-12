Display System Overview

The display package provides a crisp, predictable rendering path by separating logical rendering from presentation. Game states draw onto a fixed-size base surface first, then the display service presents that frame to the actual window using integer scaling and letterboxing. A simple camera exposes world-to-screen mapping, a visible rectangle for culling, and a small deadzone with lerped catch‑up to improve feel while keeping pixels sharp.

Render Flow

- States render to the base surface provided by the display service. This surface represents the logical render size for the game frame.
- After the state finishes drawing, the display service scales the composed frame by a fixed pixel factor (2x) using nearest‑neighbor and centers it in the window with black bars as needed.
- HUD elements that should draw at screen resolution (not doubled) render after the present step and before the display flip.

Scaling Policy

- Nearest‑neighbor everywhere during runtime: world tiles, objects, entities, and the final present step use nearest scaling to keep pixels crisp.
- One‑time asset preprocessing also uses nearest when the tilesheet is resized from 32×32 to 64×64 tiles, preserving hard edges.
- The SDL renderer scaling hint is set at program start to request nearest filtering at the system level. This prevents accidental smoothing if renderer‑driven scaling is introduced later.
- Integer snapping is preserved throughout rendering. Camera rectangles and blit destinations are computed as integers, avoiding sub‑pixel positions that can cause blur.

Files at a Glance

- systems/display/display_system/service.py
  - Role: Window creation, base surface management, present step, letterboxing, and borderless toggle.
  - Behavior: Maintains a fixed 2x pixel scale for presentation. Scales the base surface with nearest‑neighbor and centers it in the window. Exposes current presentation parameters (pixel scale and offsets) for input mapping.
  - Notes: The present step does not flip the display. Callers render HUD at screen scale after present and then flip.

- systems/display/display_system/camera.py
  - Role: Camera used by play state to convert world coordinates to screen coordinates and to provide a visible rectangle for culling.
  - Behavior: Centers on the player with a configurable deadzone measured in tiles. While the player moves inside the deadzone, the camera holds. When the player leaves it, the camera smoothly catches up toward the nearest edge using a tunable lerp rate. The camera’s rectangle is integer‑based to keep draw math aligned to pixels.
  - Notes: The camera exposes a scale field for future zoom uses. World‑to‑screen calculations and culling rely on this scale and the current origin.

- systems/display/display_system/defaults.py
  - Role: Centralized defaults for display sizing and startup behavior.
  - Behavior: Provides base width/height and the default for starting in borderless mode on the primary monitor.
  - Notes: Min/max scale constants are placeholders not used by the current fixed 2x presentation path.

- systems/display/display_system/__init__.py
  - Role: Convenience exports for the display service class.

Camera Behavior

- Deadzone: A box centered on the viewport sized in tiles (default three tiles in all directions). While the player’s center remains inside this box, the camera remains steady.
- Catch‑up: When the player leaves the deadzone, the camera targets the nearest edge that brings the player back within the box and lerps toward that target each frame. The lerp rate controls how quickly the camera closes the distance.
- Mapping: The camera provides a world‑to‑screen helper for placing sprites and a visible rectangle for selecting which chunks and entities to draw.

Input Mapping Notes

- Because the frame is presented at a fixed 2x scale and centered, the display service exposes the active pixel scale and offsets for mapping input correctly from window coordinates to base surface coordinates. Use these values to translate pointer positions when handling UI interactions at base resolution.

Resizing and Borderless

- In windowed mode the display service responds to resize events by recreating the window surface and recomputing the base surface size for the fixed 2x present scale.
- In borderless mode the window matches the desktop resolution of the primary monitor and ignores manual resize events.

Troubleshooting

- Soft or blurry tiles: Ensure nearest‑neighbor preprocessing is active for the tilesheet and the global SDL renderer quality hint is set before initializing pygame. Verify that all draw destinations are integers and that scaling during presentation uses nearest.
- Camera feel: Adjust the deadzone size (in tiles) or the lerp rate to make the camera hold longer or catch up faster. These settings affect feel but do not compromise pixel sharpness.
- HUD alignment: HUD should render after the present step at screen scale. If elements appear offset, recheck input mapping and confirm you are using the latest presentation offsets from the display service.

