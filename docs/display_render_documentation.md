# Display & Render Pipeline Notes

Quick reference for how world rendering, cameras, and input coordinates flow through the game. Use this when wiring new services (placement, UI overlays) so sprites land where expected.

## Surfaces & Camera
- **DisplayService** owns the window (`screen`) and the logical `base_surface`. `PlayState.render` draws onto `base_surface`; `DisplayService.render()` later scales that to the window.
- **Camera**: `DisplayService` maintains a `FollowCamera` with `rect` (world-space view) and `scale`. `PlayState` mirrors that into the ECS `Camera2DComponent` on `camera_entity`. Systems should read that component for view info instead of the display directly.
- **Coordinate mapping**: For UI/input, convert screen pixels to base-surface pixels with `DisplayService.get_present_params()`; then map base pixels to world using the camera rect/scale. Placement uses this before turning cursor positions into tile coords.

## Render Order in PlayState.render
1. **WorldRenderer.render_visible_chunks** – draws terrain tiles and legacy chunk objects (from `world_renderer._chunk_objects`) to `base_surface`.
2. **RenderSystem.update(0.0)** – draws entities with `RenderableEntityComponent` that do not also have `Animation` + `AnimationState` (animated entities are skipped to avoid double draw). Anchors/offsets/scale/size are applied here.
3. **AnimationSystem.render** – overlays animated frames for entities with `Animation` + `AnimationState` (and respects `RenderableEntityComponent` anchor/offset/scale if present).
4. **PlayerAnimationSystem / Landscaping / HitBox overlays** – state-specific passes.
5. **PlacementService.render** – draws the placement ghost overlay (uses the ECS camera).
6. **Crafting/UI** – draws UI elements to `base_surface`.
7. **DisplayService.render()** (outside PlayState) scales `base_surface` to the window.

## WorldRenderer Scope
- Manages terrain chunk caching and optional legacy object sprites (`object_sprites`). ECS entities are *not* routed through WorldRenderer; they rely on RenderSystem/AnimationSystem.
- Visibility is computed from the camera rect/scale. Chunk/object rendering is skipped if the chunk is outside the rect or missing from cache.

## ECS Renderers
- **RenderSystem**: Loads sprite assets on demand; applies `size` or `scale`; positions using `anchor` (default `(0.5, 1.0)`) and `offset`. Logs missing/failed sprite loads and caches successes. Skips entities that also have `Animation`/`AnimationState`.
- **AnimationSystem**: Drives sheet animations. Uses `row_order` to pick a row, computes columns/rows from the sheet, wraps columns across the sheet, and truncates with a log if requested frames exceed sheet bounds. If frames/sheet cannot be loaded, it logs and skips drawing. When `RenderableEntityComponent` is present, anchor/offset/scale/size are applied to the animated frame.
- Both systems read from the same ECS `world` populated by factories/MonsterFactory; no extra registration is required after spawn.

## Input / Placement Coordinates
- Input adapters feed cursor positions captured in screen space. Placement maps them to base-surface pixels (`get_present_params`) and then to world tiles using the ECS camera rect/scale.
- Ghost preview uses the same camera to convert world positions back to screen for drawing, keeping cursor/ghost alignment.

## Common Pitfalls
- **Missing sprites**: If `RenderableEntityComponent.sprite_path` or `Animation.sheet_path` is wrong or unreadable, renderers log the failure and skip drawing. Check console output for `[RenderSystem]` or `[AnimationSystem]` when nothing appears.
- **Scale vs. anchor**: Large sprites rely on correct `anchor`/`offset`. If mis-set, sprites can render far from the intended tile even though the entity exists.
- **Chunk objects vs. ECS entities**: Only legacy chunk objects use `world_renderer._chunk_objects`; ECS entities will not appear there. Do not expect WorldRenderer to draw ECS entities.
- **Coordinate mix-ups**: Use base-surface coordinates (not window pixels) when mapping input to world space. Always pair cursor mapping with the same camera used for rendering.

## Quick Debug Checklist
1. Verify the entity exists in the ECS `world` with `RenderableEntityComponent` (and `Animation` if animated).
2. Confirm sprite paths exist on disk and sheet dimensions match the animation config; watch console logs for missing/truncated frame messages.
3. Check camera rect/scale: entity position should be inside the view.
4. Ensure anchors/offsets are sane for sprite size; try `(0.5, 0.5)` anchors when in doubt.
5. For chunk objects, confirm they are pushed into `world_renderer._chunk_objects`; for ECS entities, rely on the render systems only.
