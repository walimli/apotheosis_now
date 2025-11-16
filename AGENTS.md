# DEVELOPER INSTRUCTIONS

Welcome to the team Codex! So glad to have you. Are you excited to work in pygame?

## MANDATORY WORKFLOW REQUIREMENTS

### Planning Step Protocol
**ALWAYS** begin every new task with a Planning Step:
1. **Investigate** as directed by the user
2. **Formulate** a complete TODO list regarding the request
3. **Create** a multi-phase plan if the task is complex
4. **Ask the user for confirmation** of the TODO list before proceeding
5. **Wait for explicit approval** before writing any code

### Pre-Code Requirements
- **NEVER** change or write code unless the Planning Step has been completed
- **NEVER** proceed without user confirmation of the TODO list
- Code changes are only permitted after explicit user approval

### Implementation Standards
- **NEVER** institute fallbacks in code
- A change either works or it doesn't - failures must be immediately visible
- **NEVER** add debug messages for in-game behaviors unless explicitly instructed
- All code changes must be direct and purposeful

### Testing and Execution Restrictions
- **NEVER** attempt to use `main.py` or run the game yourself
- **You cannot run the game or test implementations independently**
- **ALWAYS** ask the user to test the game when verification is needed
- **NEVER** create test files or ad hoc testing environments
- **NEVER** create external test implementations outside the main game
- **NEVER** attempt to access files outside of the codebase without explicit permission, attempting to do so will result in immediate termination.

### Change Management
- **NEVER** make changes the user has not requested or agreed to
- **NEVER** create backwards compatibility for legacy code when implementing new functions

Remember our company motto: Minimum Viable Product!

## Event-Driven Updates (Do Not Poll Per Frame)

- General principles
  - Prefer event-driven updates over per-frame polling for state changes and input.
  - Only run deterministic, time-based work in `update()` (e.g., physics, animation, timers, rendering prep).

- Anti-patterns to avoid
  - Cross-system polling in update loops (signature: `if external_system.flag: ...`).
  - Input polling in update loops (`pygame.key.get_pressed()`, `pygame.mouse.get_pos()`, `pygame.mouse.get_pressed()`).
  - Busy loops or ad hoc frame loops outside the central state manager.

- Input handling rules
  - Use pygame events (KEYDOWN/UP, MOUSEMOTION, MOUSEBUTTONDOWN/UP, MOUSEWHEEL) or the `PlayInputBus` to react to input.
  - Cache cursor position/hover state on events; do not re-query devices in `update()`.
  - Use axis aggregation via the input bus for movement; do not implement custom key scanning.

- Cross-system state changes
  - Use explicit signals/listeners or a shared bus for state transitions (e.g., `CraftingStateChanged(active: bool)`).
  - Subscribe during bootstrap and seed initial state once; unsubscribe/clear on teardown.
  - Do not reach across systems in `update()` to check flags; maintain local state set by events.

- Implementation standards (enforced)
  - No fallbacks or legacy code paths once event-driven wiring is in place.


## Codebase Notes

  - yawnoc_source is the codebase of a different game. It is here only for reference. (ignore this note if you are not aware of yawnoc_source)


  ## Available Dependencies

  Before designing a new system/service or refactoring old systems/services, please quickly review this list and identify any library that would likely improve efficiency and reduce the size of the codebase outside of what is normally included in python/pygame.

  ALL Dependencies (Not all are used in codebase, I just have them in case we need them.) 

cffi,Required by pymunk and moderngl

llvmlite,Required by numba

moderngl,Your OpenGL shaders and GPU rendering

noise,"Procedural terrain, biomes, caves"

numba,"Speed up simulation, pathfinding, spawn logic
"
numpy,Core of tile/chunk/world data

pillow,"Load textures, sprites, UI images"

pip,Not used at runtime — only for installing

pycparser,Required by cffi

pygame,"Main game loop, input, window"

pygame-ce,Improved Pygame (you likely use this instead of vanilla)

pygame_gui,"In-game UI (menus, buttons, HUD)"

pymunk,"Physics: collisions, gravity, rigid bodies"

PyPDF2,Only if you generate in-game manuals/PDFs — otherwise dev-only

python-i18n,In-game localization (multi-language support)

PyTMX,"Load Tiled maps for levels, spawn zones, etc."

pytweening,"Smooth camera pans, UI animations"

pydantic,"Parse and validate spawn rules, config, save files"

loguru,In-game debug logs (can be disabled in release)

tqdm,Only for world generation progress — can be stripped in release



# requirements-dev.txt (dev only - not used in game)

py-spy
snakeviz
tornado
glcontext