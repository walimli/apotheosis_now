# ECS Component Reference

Reference of every component under `ecs_core/components`. Each section lists the file, its components, their intent, and any overlaps to watch for.

---

## animation_components.py
- `Animation`: Describes a sprite sheet (paths, sheet/frame sizes, ordering, action-to-frame counts, fps, horizontal flipping). Supports `row_order` labels of `"pass"` to skip unused rows and optional `sheet_variants`/`flip_variants` dictionaries so multiple sprite sheets (front/back/side) can be tied to one component.
- `AnimationState`: Mutable runtime state (current action, frame index, timer accumulator, facing). Includes a `variant` field that selects which sheet variant to use alongside `Animation`.

**Redundancy notes:** None – tightly coupled pair with distinct responsibilities (static data vs. runtime state).

---

## collider.py
- `Collider`: Circular (diameter) collision shape with offsets, layer/mask bitfields, and trigger flag; defaults point to enemy layer from `constants`.

**Redundancy notes:** Single implementation; no duplicates elsewhere.

---

## components.py
- `Speed`: Scalar speed in pixels per second (used by movement systems).
- `Renderable`: Simplistic radial render proxy (`radius`, RGB color). Likely for debug/placeholder visuals.
- `Velocity`: Basic velocity vector (`vx`, `vy`).
- `Position`: World coordinates (`x`, `y`).
- `HeldItem`: Frozen component storing currently held inventory `item_id`.
- `Harvestable`: Growth state with `growth` progress and `ready` flag.
- `Health`: Combat stats (max/current HP, regen per heartbeat, defense, optional sound cue).
- `Soul`: Secondary resource with clamped initialization (`max_soul`, `current_soul`, depletion flag).
- `Evolve`: Time-driven evolution hook (`time_event`, optional `next_entity_id` to morph into).
- `Controller`: Tag for control scheme (`player_input`, `mob_aggressive`, `mob_passive`, `npc`).
- `Drops`: Loot table mapping coin types to drop odds plus XP reward.

**Redundancy notes:** `Renderable` overlaps conceptually with `rendering_components.RenderableEntityComponent` (two different render descriptors—circle vs. sprite). Coordinate/velocity components are unique.

---

## entity_classes.py
- `Player`: Marker for player-controlled entities.
- `Mob`: Marker for mobile hostile/neutral AI.
- `NPC`: Marker for stationary NPC providers.
- `Plant`: Marker for vegetation that grows/harvests.
- `Object`: Marker for static interactable objects.

**Redundancy notes:** Purposefully separate markers even though empty. No overlap besides all being identity tags; ensure systems watch for the right marker instead of duplicating checks.

---

## rendering_components.py
- `Camera2DComponent`: Rendering viewport state (pygame `Rect`, scale, scroll vector).
- `VoidVisualComponent`: Parameters for shader-based void/CRT effect (time, scroll, saturation, parallax, readiness).
- `TerrainChunkComponent`: Placeholder linking chunk key to cached `Surface`.
- `RenderableEntityComponent`: Describes sprite drawables (path, entity id, layer, size/scale, anchor, pixel offset).

**Redundancy notes:** As noted earlier, `RenderableEntityComponent` and `components.Renderable` both flag entities for drawing but expect different rendering strategies (sprite vs. primitive). Clarify usage to avoid double attachment.

---

## __init__.py
Currently empty aside from package wiring; no components defined here.

---

## Identified Redundancies
1. **Renderable vs. RenderableEntityComponent** – Two rendering descriptors; choose one based on whether you need primitive circle rendering (`Renderable`) or sprite-based drawing (`RenderableEntityComponent`). Avoid attaching both unless two render passes are genuinely required.
2. **Entity markers** – Multiple empty dataclasses (`Player`, `Mob`, `NPC`, `Plant`, `Object`). They intentionally overlap structurally but encode different semantics; treat them as mutually exclusive markers rather than trying to consolidate unless the gameplay semantics truly match.

No other duplicate functionality detected across the inspected files.
