# ECS Component Reference

Reference of every component under `ecs_core/components`. Each section lists the file, its components, their intent, and any overlaps to watch for.

---

## animation_components.py
- `Animation`: Describes a sprite sheet (paths, sheet/frame sizes, ordering, action-to-frame counts, fps, horizontal flipping). Supports `row_order` labels of `"pass"` to skip unused rows and optional `sheet_variants`/`flip_variants` dictionaries so multiple sprite sheets (front/back/side) can be tied to one component.
- `AnimationState`: Mutable runtime state (current action, frame index, timer accumulator, facing). Includes a `variant` field that selects which sheet variant to use alongside `Animation`.

**Redundancy notes:** None – tightly coupled pair with distinct responsibilities (static data vs. runtime state).

---

## collider.py
- `Collider`: Circular (diameter) collision shape with offsets, layer/mask bitfields, trigger flag, and `immovable` boolean; defaults point to enemy layer from `constants`. `immovable=True` makes collision resolution push only the opposing body (used for static props/walls).

**Redundancy notes:** Single implementation; no duplicates elsewhere.

---

## static_body.py
- `StaticBody`: Marker to denote immovable entities. `MovementSystem` sets the collider’s `immovable` flag when this marker is present so `CollisionSystem` leaves the body in place during resolution.

---

## hit_box.py
- `HitBox`: Marks entities whose colliders can be outlined; stores outline color (defaults to red) and the stroke width.

**Redundancy notes:** Works alongside `Collider`; no overlap with other render markers.

---

## player_animation.py
- `PlayerAnimationHandle`: Carries a reference to the legacy `PlayerAnimationService` so systems can update/render the bespoke player sprite.

**Redundancy notes:** Unique to the player bridge; no other systems should attach this component.

---

## physics.py
- `Friction`: Applies drag to velocity over time (`drag` multiplier, `min_velocity` threshold).

**Redundancy notes:** Used by `MovementSystem` to slow down entities (e.g., dropped items).

---

## attack.py
- `AttackComponent`: Identifies which attack template (`attack_id`) an entity can trigger, tracks cooldown state, and exposes `spawn_offset`, `offset_x`, and `offset_y` for tuning the hitbox spawn origin relative to the owner's collider.

**Redundancy notes:** Shared between player and future AI attackers; keep it generic.

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
