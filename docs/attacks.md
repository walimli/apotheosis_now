# Attacks System Overview

This document describes how the current attack pipeline is wired, which systems/components it depends on, and the fixes we have already attempted while debugging why wooden sword swings do not damage sprout entities.

## High-Level Flow

1. **AttackComponent** (attached to the attacker, e.g. the player) stores the chosen `attack_id`, cooldown, spawn offsets, and fine-tuning offsets (`spawn_offset`, `offset_x`, `offset_y`).  
2. **AttackSystem** listens for `request_attack` calls (from `PlayerAttackService`, AI, etc.). When cooldown allows, it:
   - Computes the spawn position: `Position.render_x/y` + facing vector × (`collider_radius + spawn_offset`) + `offset_x/y`.
   - Calls `MonsterFactoryService.spawn_attack_entity(attack_id, position)`.
3. **MonsterFactoryService** uses the evolvable registry to spawn the attack entity (wooden sword hitbox) at the requested world coordinates.
4. The **attack entity** carries:
   - `Position`, zero `Velocity`, a red `Renderable` circle, a trigger `Collider`, `Damage`, and a `Lifeline` (0.2s).
   - `Damage.target_classes` lists the entity markers it can harm (now includes `Mob`, `Plant`, `Object`).
   - Collider layer/mask currently set to `LAYER_PROJECTILE` and mask `LAYER_ENEMY | LAYER_PICKUP | LAYER_WALL`.
5. **MovementSystem** syncs colliders and produces `collision_events`.
6. **DamageSystem** listens to `collision_events`:
   - For each overlap, it checks if the “damager” entity carries `Damage` and the “target” carries `Health` of a matching entity class.
   - On contact mode, it calls `HealthSystem.take_damage` once per contact, then destroys the target immediately if `take_damage` reports death.
7. Any additional cleanup (drops, XP, etc.) must hook into `DropsSystem` and the inventory service (currently the drops system isn’t wired into the runtime, so no pickups spawn yet).

## Wiring Between Systems

- **Input → AttackSystem:** `PlayerAttackService` (spawned in `states/play/player/player_runtime.py`) calls `attack_system.request_attack(player_entity, facing)` when the player triggers the USE action.
- **AttackSystem ↔ MonsterFactory:** `AttackSystem` is configured in `states/play/bootstrap/ecs_runtime.py`; `attack_system.monster_factory = services.monster_factory`.
- **MonsterFactory Attack Registry:** `ecs_core/entities/attacks/wooden_sword.py` registers the hitbox factory via `evolvable_registry.register_factory("wooden_sword_attack", ...)`. The attack metadata lives in `data/entities/attacks.json`, and the spawn definition lives in `data/entities/attacks_spawn.json`.
- **DamageSystem Dependencies:** In the same bootstrap file, `DamageSystem` is given references to `movement_system`, `health_system`, and `services.time_manager`.

## Recent Fixes / Investigations

1. **Attack alignment:** Centered player sprites along X/feet along Y so the hitbox spawn math matches the visual character position.
2. **AttackComponent offsets:** Added `offset_x` / `offset_y` to `AttackComponent` and hooked them up in `player_core.py` so we can tweak per-weapon placement.
3. **Collider masks:** Updated wooden sword attack colliders to include `LAYER_PICKUP`, and sprout colliders to include `LAYER_PROJECTILE`, ensuring collisions occur.
4. **Component import alignment:** Switched every system to import components via `ecs_core.components` so `world.get(..., Health)` sees the same class objects as entity factories.
5. **DamageSystem kill path:** Added a direct `world.destroy_entity` call when `HealthSystem.take_damage` reports death to guarantee entities vanish at 0 HP.

## Remaining Issues

- Despite the above, wooden sword attacks still do not reduce sprout health. We have verified collider overlap (massive diameter, masks aligned) and that `Damage.target_classes` includes `Plant`. Yet `DamageSystem` still does not apply damage, so further debugging is required (e.g. logging collisions, confirming `collision_events` include trigger pairs, verifying `movement_system.collision_events` is non-empty).
- Drops/XP removal is tied to `DropsSystem`, but this system is not currently wired into the runtime, so even after damage works we will need to integrate drops separately if we expect loot feedback.

Keeping this history in `docs/attacks.md` should prevent us from redoing the same investigative steps when we continue debugging the attack failures.
