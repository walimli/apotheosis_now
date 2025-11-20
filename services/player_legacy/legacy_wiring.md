# Legacy Player Animator Wiring

This document summarizes how the legacy `PlayerAnimator` integrates with the current ECS runtime.

## Runtime Flow
- `PlayerAnimationService` wraps the legacy animator, sets the asset root, listens for inventory selection changes (pick vs. sword), and exposes helpers (`play_pick_swing`, `play_sword_swing`, `play_interact`) plus the raw `trigger_action`.
- During `spawn_player_runtime`, the service is instantiated, bound to the player inventory, attached via `PlayerAnimationHandle`, and stored on the `PlayState` (`play_state.player_animation_service`) so other systems can trigger actions.
- `PlayerAnimationSystem` (ECS) updates the service each frame using the player’s `Position` and blits the current surface relative to the camera rect.

## Action Hooks
- `LandscapingSystem` calls `play_pick_swing()` before harvesting (pick equipped) and `play_interact()` before placing a tile so the animation starts immediately with the player’s current facing.
- Other systems can trigger bespoke animations by invoking `play_state.player_animation_service.trigger_action("state_name")` or by adding new helpers to the service.

## Asset Loading
- `image_loader.set_player_asset_root()` runs during service construction, pointing the loader at the downsized 115x115 sheets under `assets/player/`.
- The legacy state-map definitions remain intact (`state_map.py`), so all action/direction combinations continue to resolve exactly as they did in the original project.
