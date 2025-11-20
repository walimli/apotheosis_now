# Placement Service (Current Implementation)

This document describes how placement currently works, the data it consumes, and where to extend it. It supersedes the old migration plan.

## Runtime Flow
- **Selection**: `PlacementInventoryListener` tracks hotbar/selection events. If the selected stack matches a known `PlacementBlueprint`, placement activates; pill items are routed to the pill registry instead.
- **Ghost preview**: `PlacementPlacer` keeps `PlacementGhost` aligned to the cursor using base-surface coordinates from `DisplayService.get_present_params()` plus the ECS camera rect/scale. The ghost tints green/red based on validity and follows the blueprint’s anchor/offset/animation.
- **Validation**: Tiles are checked for player distance, void tiles, and occupancy using ECS `Position` with `Object`/`Plant` markers. Blueprints can require the player tile or ignore occupancy.
- **Placement attempt**: `handle_use_inventory` → `_attempt_entity_placement` calls `PlacementPlacer.try_place()`. On success the item is decremented, then `MonsterFactory.spawn_entity_at_tile(entity_id, tile)` is invoked. Pills consume immediately via `_apply_pill`.
- **Render pass**: `PlacementService.render` runs late in `PlayState.render`, drawing only the ghost overlay. Spawned entities render through ECS systems as usual.

## Key Modules
- `services/placement/service.py` – service wiring, cursor/input handlers, screen→base→world tile mapping, spawn requests.
- `services/placement/placer.py` – validates tiles, consumes inventory, drives ghost position/validity.
- `services/placement/ghost.py` – draws the preview sprite/animation with validity tinting.
- `services/placement/blueprints.py` – item→`PlacementBlueprint` definitions (entity id, sprite/animation, anchor/offset, radius rules). Sources are the crafted entity configs; no legacy placeable JSON parsing.
- `services/placement/selection.py` – listens for inventory selection changes and activates/deactivates placement (no polling).
- `services/placement/pills.py` – registry of consumable pill effects (health/soul).

## Data & Entities
- **Blueprints**: Built in code for glow trees, crystal colonies, skull wards, and sprout. Each blueprint names the `entity_id`, preview sprite/animation, anchor/scale, and placement constraints.
- **Entities**: Crafted placeables live under `ecs_core/entities/crafted/` and are enumerated in `data/entities/placeables_crafted.json`, which `MonsterFactory` loads. Assets/sprite sheets are pulled from the crafted configs (e.g., glow_tree, crystal_colony, skull_candle, skull_shrine).
- **Spawning**: `MonsterFactory.spawn_entity_at_tile` converts tile coords to world coords and instantiates via the crafted registry; spawn attempts are logged.

## Pipeline Touch Points
- **Input**: `PlaceablesInputAdapter` connects mouse actions to `PlacementService.handle_use_inventory`; cursor motion flows into `handle_cursor_move`.
- **Camera**: Uses the ECS `Camera2DComponent` (via `DisplayService`) for both coordinate mapping and ghost positioning, keeping cursor/ghost alignment.
- **Rendering**: `RenderSystem` draws static sprites; `AnimationSystem` draws animated entities (honoring renderable anchor/offset/scale). Placement ghost draws after world/entities, before UI.

## Behavior Notes
- Event-driven only—no per-frame input polling.
- Failed validation or missing blueprints abort placement with no inventory loss.
- Placement, spawn, render, and animation systems log missing assets or failed attempts to the console; silent failures are avoided.
