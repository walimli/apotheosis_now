# Entity Movement Pipeline

## Overview
Entity motion flows through a small set of ECS components and systems: input updates velocities, movement integrates positions while syncing with collision, and rendering consumes the resolved positions to draw sprites and drive the camera. This document notes each major step and captures the rounding bias investigation we completed.

## Key Components and Systems
- `ecs_core/components/components.py`
  - `Velocity` stores per-axis speed in pixels/second as floats, written by input/controller systems.
  - `Position` now tracks the integer coordinates used by collision (`x`, `y`) as well as smoothed render-space floats (`render_x`, `render_y`) to preserve sub-pixel movement.
- `ecs_core/systems/controller.py`
  - Converts player input (or AI intent) into normalized direction vectors and applies speed scalars, writing the resulting floats into `Velocity`.
- `ecs_core/systems/movement_system.py`
  - Integrates velocity over `dt`, produces proposed float positions, and feeds quantized integer positions into the `CollisionSystem`.
  - After collision resolution, updates `Position.x/y` with the resolved ints and keeps `render_x/y` aligned with the latest float proposal or collision push.
- `ecs_core/systems/collision/collision.py`
  - Spatial hash of collider circles; receives integer positions, detects overlaps, resolves non-trigger penetrations, and reports collision events.
- `services/display/display_system/camera.py`
  - Smooth follow camera that lerps toward the player’s render coordinates and exposes the current viewport for culling.
- `ecs_core/systems/render.py` & `ecs_core/systems/animation/animation.py`
  - Translate `Position.render_x/y` into screen-space coordinates for sprite/circle drawing so sub-pixel motion is visible without jitter.
- `states/play/play_state.py` and `states/play/player/player_runtime.py`
  - Keep the camera centered on the player by reading the render coordinates, ensuring consistent parallax and follow behavior.
- `services/landscaping/manager.py`
  - Uses the player’s render position for hover targeting to keep cursor overlays aligned with the visually rendered entity location.

## Bias & Jitter Fix
- **Issue:** Movement previously stored only integers in `Position`, and converting floats via `int()` introduced a directional bias (faster up/left, slower down/right). Switching to directional rounding removed the bias but exposed heavy jitter because renderers consumed those alternating ints.
- **Resolution:** `MovementSystem` now quantizes for collision using a direction-aware `_quantize()` yet keeps `render_x/render_y` as float proposals. Rendering, camera tracking, and hover targeting all read the render floats, so entities display smooth motion while collisions remain deterministic. This resolved both the original speed bias and the subsequent jitter without requiring broad changes to the collision grid.
