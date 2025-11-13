# PlayState Refactor – Multi-Phase TODO

This document tracks the work required to turn `states/play/play_state.py` back into a thin orchestrator that only wires services/systems together. The phases below are ordered to reduce merge pain and isolate risk. Check off each task only when the phase’s definition of done is satisfied.

---

## Phase 0 – Discovery & Safety Nets
- [ ] Re-read `states/play/play_state.py` to capture every helper that currently embeds game logic (tile loading, HUD, pause toggles, camera math, chunk streaming, motion integration).
- [ ] Audit consumers: `services/display/display_system/*`, `services/world_renderer/*`, `services/inputs/bindings.py`, `states/pause_state/pause_state.py`, and `ecs_core/systems/movement.py` so the refactor aligns with existing APIs.
- [ ] Confirm required assets (`assets/tiles`) exist on disk so removing placeholder generation will not break boot; document fallback expectations if they are intentionally missing.

**Exit criteria:** everyone involved understands the available services/systems and we have confidence that PlayState can delegate all responsibilities without adding new fallbacks.

---

## Phase 1 – Asset Loading Cleanup
- [ ] Remove `_create_placeholder_tilesheet` and every call site in `states/play/play_state.py` (currently lines ~168–205) so PlayState depends solely on `services.asset_loader.load_tilesheet`.
- [ ] Decide how to surface missing assets: either let the exception bubble (failing fast) or move graceful handling into `load_tilesheet` itself so orchestration code stays ignorant.
- [ ] Run a cold boot (user-validated per workflow) to ensure tile assets load successfully without the placeholder logic.

**Exit criteria:** PlayState performs no asset fabrication; asset module owns all tile-sheet behavior.

---

## Phase 2 – UI/HUD Extraction
- [ ] Create `services/ui/ui_manager.py` with a `UIManager` (or similar) responsible for drawing HUD overlays (clock/time display, pause banner, future widgets).
- [ ] Move `render_hud` concerns from `states/play/play_state.py:269+` into the UI manager, including font acquisition via `DisplayService`.
- [ ] Update PlayState to own only a reference to `UIManager` and pass it the data it needs (e.g., `time_manager.clock`, pause flag supplied by StateManager).
- [ ] Ensure UI manager is initialized in `PlayState.__init__` (after display/time services are available) and invoked during the state’s `render`/`render_hud` without inline pygame calls.

**Exit criteria:** PlayState no longer imports fonts or draws HUD elements directly; all HUD work flows through `services/ui/ui_manager.py`.

---

## Phase 3 – Pause Handling Alignment
- [ ] Remove `_toggle_pause` and related `PlayInputBus` subscriptions from PlayState (`states/play/play_state.py:288` and `_initialize_input`).
- [ ] Wire the existing `PlayAction.PAUSE_TOGGLE` binding (see `services/inputs/bindings.py`) to transition control to `states/state_manager.StateManager.set_state("pause")`. PlayState should simply forward the action to the manager or raise a signal the manager already listens for.
- [ ] If PlayState still needs awareness of paused state (for HUD text, etc.), have it query the StateManager or receive a callback from `PauseState` rather than managing `self.paused`.
- [ ] Keep any pause-related helpers near `states/pause_state/*` (e.g., a tiny `pause_service.py`) if auxiliary utilities are required.

**Exit criteria:** Only `PauseState` pauses/resumes time and PlayState never toggles pause internally.

---

## Phase 4 – Camera + Display Service Integration
- [ ] Delete `_update_camera_rect` and `_update_camera_follow` from PlayState (lines ~296–360).
- [ ] Inspect `services/display/display_system/service.py` and `camera.py` to expose whatever helper is needed to:  
  1. register the player entity as the follow target,  
  2. react to `pygame.VIDEORESIZE` events by delegating to the display service,  
  3. retrieve the active camera rect for rendering calls (`world_renderer`, `AnimationSystem`).
- [ ] If small glue helpers are missing, add them under `services/display/display_system/` (never inside PlayState).
- [ ] Update PlayState’s render/update loops to pull camera information exclusively through `DisplayService` APIs.

**Exit criteria:** PlayState makes zero direct camera or deadzone calculations; everything routes through the display service.

---

## Phase 5 – World Renderer & Chunk Streaming
- [ ] Remove `_generate_visible_chunks` and any local chunk/object/entity caches from PlayState (`world_chunks`, `world_objects`, `world_entities` fields).
- [ ] Study `services/world_renderer/manager.py`, `chunk_cache.py`, and related files to identify the correct API for requesting chunk generation/visibility based on camera position.
- [ ] Refactor PlayState to request “ensure chunks around camera are ready” via the world-renderer manager instead of regenerating them.
- [ ] Confirm that world builder usage (seed, chunk size) is configured within the renderer service; if not, extend the service to accept the parameters during initialization instead of reimplementing logic in PlayState.

**Exit criteria:** Chunk management and rendering live entirely within `services/world_renderer`; PlayState simply supplies camera/viewport info and triggers draw calls.

---

## Phase 6 – Movement System Adoption
- [ ] Migrate `_integrate_motion` into `ecs_core/systems/movement.py` (file already exists; currently empty) as a proper ECS system that reads `Position` + `Velocity`.
- [ ] Register the new `MovementSystem` inside `_initialize_ecs` and update the state’s `update()` loop to call `movement_system.update(dt)` instead of the deleted helper.
- [ ] Ensure the movement system follows ECS conventions (uses the world reference, respects `dt <= 0` guard, etc.) and add minimal docstrings/comments for clarity.

**Exit criteria:** Motion integration is executed by an ECS system, not PlayState helper code.

---

## Phase 7 – Wiring & Verification
- [ ] After phases 1–6, re-read PlayState to guarantee it only performs orchestration: service initialization, system updates, delegations, and no direct gameplay logic.
- [ ] Update imports to reflect removed helpers (drop `numpy`, unused ECS components, etc.).
- [ ] Ask the user to run the game and verify:  
  - tile assets load without placeholder,  
  - HUD renders through the new UI manager,  
  - pause flow uses `PauseState`,  
  - camera and world rendering behave as before,  
  - movement still works using the new ECS system.
- [ ] Document any follow-up tasks discovered during verification (e.g., further ECS migrations) back into this file or a tracking issue.

**Exit criteria:** PlayState is lean, all delegated systems are in place, and manual verification passes without regressions.

---

### Notes & Constraints
- Follow the event-driven rules from `AGENTS.md`: no polling-based fallbacks, no debug toggles, no alternate code paths.
- Never run `main.py` yourself; rely on the user for runtime verification.
- Keep new helpers within the appropriate service folders (display, world renderer, pause state, UI) to avoid PlayState bloat.
- Avoid adding new fallbacks—fail fast so issues are visible to the team.
