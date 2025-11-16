# Monster Factory Pipeline

## Overview
`services/monster_factory/monster_factory.py` is the single entry point for all non-player entity spawning. It handles three responsibilities:

1. Load spawn rules from `data/entities/*_spawn.json`.
2. React to game events (world chunks appearing, time events, bespoke triggers) and resolve those rules into spawn coordinates.
3. Instantiate concrete ECS entities by calling the registered factories and placing them into the active `World`.

Because the rest of the ECS is deterministic and data-oriented, the monster factory acts as the orchestration layer that understands external services (time manager, world builder, renderer). The goal is to keep PlayState focused on wiring, while the factory owns the procedural rules and metadata lookups needed to feed the world.

## Files

| File | Purpose |
| --- | --- |
| `monster_factory.py` | Service implementation (event wiring, chunk listeners, spawn execution). |
| `spawn_config.py` | Dataclasses + loader that parse `*_spawn.json` files into normalized `SpawnRule`s. |
| `placement.py` | Helpers for region detection, eligibility checks, and tile selection (islands / voids / tiles). |
| `evolve_registry.py` | Evolvable entity registry used by both the monster factory and the ECS `EvolveSystem`. |
| `entity_pipeline.md` | This documentation. |

## JSON Spawn Rules

Every entity that can be spawned by the factory has a `<entity_id>_spawn.json` file in `data/entities/`. The filename stem must match the entity ID registered in `data/entities/monster_manual.json`. Example: `sprout_spawn.json`.

Schema (per event):
```json
{
  "spawn_events": {
    "world_start": {
      "spawn_chance": 0.9,
      "spawn_per": "island",
      "eligible_tiles": [1, 14, 24, 34],
      "spawn_number": "randomint(1,5)",
      "share_tile": false,
      "exact_position": "pass"
    },
    "sprout_planted": {
      "spawn_chance": 1.0,
      "spawn_per": "event",
      "spawn_number": 1,
      "exact_position": "required"
    }
  }
}
```

Supported fields:

- `spawn_events`: object keyed by event name (lowercase). Each value can be a single rule object or list of rule objects.
- `spawn_chance`: float [0,1]. Applied per island/tile/void region.
- `spawn_per`: `"island" | "tile" | "void" | "event"`.
  - `island`: run once per contiguous land region.
  - `tile`: evaluate each eligible tile independently.
  - `void`: run once per contiguous void region.
  - `event`: expect a `world_position` in the event payload (used for “planting” or scripted spawns).
- `eligible_tiles`: optional list of tile codes (numbers from `constants.py`). Moss overlays (14/24/34) are accepted and normalized automatically.
- `spawn_number`: integer (exact count) or string `randomint(min,max)`.
- `share_tile`: allow multiple entities to occupy the same tile. When false, the service shuffles the eligible tile list to avoid duplicates.
- `exact_position`: `"pass"` (ignore payload coordinates) or any other string (requires `world_position` from the event payload).

All spawn files are lazy-loaded: the factory only parses a file the first time one of its events is requested.

## Event Wiring

### Chunk Generation (`world_start`)
1. PlayState constructs `WorldRenderer` and `MonsterFactoryService` during `_initialize_services`.
2. `world_renderer.add_chunk_listener(monster_factory.handle_chunk_created)` wires the service so it sees every chunk that is cached for the first time.
3. Each chunk callback constructs a context with the chunk key, tile array, and chunk/tile sizes, then calls `monster_factory._process_event("world_start", context)`.
4. Spawn rules that target `world_start` evaluate against the chunk’s tile data: the service finds islands, picks eligible tiles, and calls `_spawn_entity`.

### Time Events
1. PlayState instantiates `TimeManager` and `monster_factory.attach_time_manager(self.time_manager)` immediately after the chunk wiring.
2. The factory subscribes to every `TimeEventType` (or a subset if needed). The time manager calls `_handle_time_event` as soon as a `TimeEvent` occurs, so the factory reacts in the same frame.
3. Event names are normalized to lowercase (e.g., `DAWN_STARTED` -> `dawn_started`) to match the JSON keys.
4. Each matching rule spawns procedurally (per island/tile/void) or expects an explicit event payload (for `"event"` rules).

### Manual Triggers
Any system can call `monster_factory.emit_event("sprout_planted", {"world_position": (x, y)})`. The service normalizes the event name and runs the matching rules. This is how future systems (planting, quest rewards, etc.) can ask for spawns without knowing the JSON schema.

## Entity Creation

`_spawn_entity` uses `services/monster_factory/evolve_registry.py`. The registry loads initial metadata from `data/entities/monster_manual.json` (so we have display names + descriptions) and stores callables for each entity (sprout, twice_sprout, etc.). Those factories are registered when the corresponding modules are imported (in `MonsterFactoryService._ensure_entity_factories_loaded`).

Given an entity ID, the registry calls the factory with the ECS `World` and `EntityManager`. After creation, the monster factory ensures a `Position` component exists and offsets it to the candidate tile’s center.

## PlayState Integration

```python
# states/play/play_state.py
from services.monster_factory import MonsterFactoryService

def _initialize_services(self):
    ...
    self.world_renderer = WorldRenderer(...)
    self.monster_factory = MonsterFactoryService(
        project_root=self.project_root,
        chunk_size=world_builder.chunk_size,
        tile_size=self.world_renderer.tile_size,
    )
    self.world_renderer.add_chunk_listener(self.monster_factory.handle_chunk_created)
    self.time_manager = TimeManager()
    self.monster_factory.attach_time_manager(self.time_manager)
    ...

def _initialize_ecs(self):
    self.ecs_world = World()
    self.entity_manager = EntityManager()
    ...
    self.monster_factory.bind_world(self.ecs_world, self.entity_manager)
```

- Chunk listeners fire before the ECS world exists, so the factory queues events until `bind_world` is called. Once the world and entity manager are ready, the queued chunk events replay automatically.
- PlayState does **not** attempt to spawn entities itself; it simply forwards events to the factory and keeps rendering concerns in `WorldRenderer` + `RenderSystem`.

## Evolve System

- The `Evolve` component (in `ecs_core/components/components.py`) stores `time_event` and `next_entity_id`.
- `ecs_core/systems/evolve.py` watches `Evolve` components and `TimeManager.current_event`. When the time manager reports a matching event (e.g., `HEARTBEAT`), the system destroys the old entity and asks the same `evolvable_registry` to spawn the successor.
- PlayState now instantiates `EvolveSystem` alongside the other systems, wiring in the ECS world, entity manager, and time manager, then calls `evolve_system.update(dt)` each frame.

## Rendering & Discovery

- Spawned entities carry `RenderableEntityComponent` data via the entity factory (see `ecs_core/entities/flora/sprout_common.py`). Once the monster factory places them in the world, the existing `RenderSystem` handles sprite drawing.
- Because chunk listeners fire for every new chunk, exploration naturally streams in new spawns. If a chunk is regenerated (e.g., after landscaping), the factory can be called manually to rescan the chunk and reapply `world_start` rules if desired.

## Extending the Pipeline

1. **Add a new entity**: implement its factory under `ecs_core/entities/...`, register with `evolvable_registry`, and add an entry to `monster_manual.json`.
2. **Create a spawn config**: add `<entity_id>_spawn.json` with the desired events and rules.
3. **Hook events**: for new triggers (e.g., crafting, quest completion), publish an event via `monster_factory.emit_event`. For additional chunk-enumeration logic (biomes, marshes), extend `placement.py`.
4. **Test**: spawn configs fail fast. Invalid expressions (bad `spawn_number`, missing eligible_tiles) raise errors during load so they can be fixed immediately.

## Runtime Checklist

- `MonsterFactoryService` created in PlayState `_initialize_services`.
- `world_renderer.add_chunk_listener` connected before chunk generation.
- `monster_factory.attach_time_manager` called before `TimeManager.update`.
- `_initialize_ecs` binds the world/entity manager to the factory.
- `EvolveSystem` runs each frame so `Evolve` components respond to time events.
- `RenderSystem.update` called during PlayState.render to draw spawned entities.

With those pieces in place, all non-player entities are fully data driven: designers adjust JSON files, engineers add entity factories, and the monster factory handles the rest.***
