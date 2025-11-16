# ECS + PlayState Integration

This guide walks through the entity-component-system (`ecs_core`) architecture and shows how the `PlayState` wiring drives it during gameplay.

## Core ECS Primitives
- **World (`ecs_core/worlds/world.py`)** stores components in `{ComponentType: {Entity: Component}}` tables, maintains an entity index, and exposes helpers such as `add/remove/get`, `view(*components)` for joins, and `entities_with(...)`. Everything that needs to read/write components receives a `World`.
- **EntityManager (`ecs_core/entities/entities.py`)** hands out monotonically increasing integer IDs via `create()`. Entities are just identifiers; all data lives in components.
- **System (`ecs_core/systems_base.py`)** is an abstract base with an `update(dt)` contract. Concrete systems expect a `World` (either injected through their constructor or assigned right after instantiation, e.g., `controller_system.world = world`).
- **Components (`ecs_core/components/...`)** are lightweight data classes grouped by domain (movement, rendering, collider, etc.). Systems query the `World` for the components they operate on.

## Bootstrapping Services
`states/play/bootstrap/services.py` encapsulates non‑ECS services (tile sheet loader, `WorldRenderer`, `MonsterFactory`, `TimeManager`, `UIManager`, `NotificationService`, etc.) inside a `PlayServices` dataclass so `PlayState` can initialize them once and store references.

## Creating the ECS Runtime
`create_ecs_runtime()` in `states/play/bootstrap/ecs_runtime.py` builds the ECS layer and returns `ECSRuntime`:
1. Instantiate a `World` and `EntityManager`.
2. Create a dedicated camera entity, seed it with `Camera2DComponent` sized to `DisplayService`’s base surface.
3. Construct system instances (render, controller, animation, speed, movement, soul, evolve). Some systems are initialized with the world via constructor (`MovementSystem(world)`); others assign `system.world = world` to satisfy the base contract.
4. Wire aggressive pathfinding by constructing a `_PathfindingPlayStateProxy` so the AI bootstrap can see the `World`, `MovementSystem`, and selected `PlayState` attributes.
5. Bind the `MonsterFactoryService` to the ECS world/entity manager so entity templates can spawn into the same runtime.

The resulting `ECSRuntime` bundles references (`world`, `entity_manager`, `camera_entity`, every system, plus pathfinding services) so `PlayState` can capture everything at once.

## PlayState Lifecycle
`states/play/play_state.py` orchestrates ECS plus services in a deterministic order:

1. **Initialization**
   - Build services via `build_services(...)` and stash them on the state instance.
   - Create the ECS runtime, then copy `world`, `entity_manager`, systems, and camera entity onto `PlayState`.
   - Call `_sync_camera_component_from_display()` to mirror the display camera rect/scale into the ECS `Camera2DComponent`.
   - Spawn the player using `spawn_player_runtime(...)` which:
     - Calls `ecs_core.entities.player.spawn_player(...)` to create the entity and attach components.
     - Registers the entity with `ControllerSystem` and the aggressive pathfinding manager.
     - Syncs the display camera to the player’s initial `Position`.
     - Builds UI/inventory bindings (`PlayerBindings`) for downstream services.
   - Bootstrap landscaping systems (requires player bindings) and wire input adapters (`wire_play_input`) using the shared `PlayInputBus`.

2. **Event Handling**
   - `handle_events(...)` first intercepts global window events (QUIT, VIDEORESIZE), informs `DisplayService` and notifications, then passes remaining events to the input bus.

3. **Update Loop**
   - Advance `TimeManager`, feed notifications, then update systems in order:
     1. `ControllerSystem.update(dt)`
     2. Aggressive pathfinding manager
     3. `AnimationSystem`, `SpeedSystem`, `MovementSystem`, `SoulSystem`, `EvolveSystem`
     4. Landscaping system (if present)
   - `_update_camera_tracking(dt)` reads `Position` for the player entity, updates the display camera, and resyncs the ECS `Camera2DComponent`.
   - `_prepare_world_chunks()` requests the `WorldRenderer` ensure chunks covering the current camera rect are generated.

4. **Rendering**
   - `render(...)` pulls the current `Camera2DComponent`, asks `WorldRenderer` to draw visible chunks, runs `RenderSystem.update(0.0)` to draw entities, renders animations, and lets the landscaping system render overlays.
   - `render_hud(...)` delegates to `UIManager` after world rendering.

## Extending the Flow
When adding new ECS components or systems:
- Define the component data under `ecs_core/components/` (grouped by concern).
- Create a system subclass of `System`, decide whether it needs the world in the constructor or as a separate attribute, and place it in `ecs_core/systems/...`.
- Update `create_ecs_runtime()` to instantiate the system, inject the `World`, and expose it via the `ECSRuntime` dataclass so `PlayState` can keep a reference.
- If the system must act every frame, invoke it inside `PlayState.update(...)` after any dependencies (respect deterministic order). Avoid per-frame polling across systems; rely on events or explicit signals to mutate state.
- For entity-specific registration (like controllers), hook into the relevant spawn/bootstrap helpers (`spawn_player_runtime`, factories, etc.) so new systems receive the components they need right after entities are created.

Following this structure ensures new functionality plugs neatly into the existing ECS/runtime wiring without resorting to per-frame polling or hidden side effects.
