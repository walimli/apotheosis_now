"""Factory helpers for spawning a simple wooden sword attack entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import constants
from ecs_core.components import Damage, Lifeline, Position, Renderable, Velocity
from ecs_core.components.collider import Collider
from ecs_core.components.entity_classes import Mob, Plant, Object
from ecs_core.entities.entities import Entity, EntityManager
from services.monster_factory.evolve_registry import evolvable_registry
from ecs_core.worlds.world import World


@dataclass(frozen=True)
class WoodenSwordAttackConfig:
    """Config describing how a wooden sword attack hitbox should spawn."""

    spawn_position: Tuple[float, float] = (0.0, 0.0)
    radius: int = 16
    color: Tuple[int, int, int] = (255, 0, 0)
    collider_diameter: int = 128
    collider_offset: Tuple[int, int] = (0, -12)
    collider_layer: int = constants.LAYER_PROJECTILE
    collider_mask: int = (
        constants.LAYER_ENEMY | constants.LAYER_PICKUP | constants.LAYER_WALL
    )
    lifetime: float = 0.2
    damage_rating: float = 1.0
    target_classes: tuple[type, ...] = (
        Mob,
        Plant,
        Object,
    )


def spawn_wooden_sword_attack(
    world: World,
    entity_manager: EntityManager,
    *,
    config: WoodenSwordAttackConfig | None = None,
) -> Entity:
    """Spawn a timed collider that deals contact damage for a short lifespan."""

    cfg = config or WoodenSwordAttackConfig()
    entity = entity_manager.create()

    world.add(
        entity,
        Position(
            x=int(cfg.spawn_position[0]),
            y=int(cfg.spawn_position[1]),
        ),
    )
    world.add(entity, Velocity(vx=0.0, vy=0.0))
    world.add(entity, Renderable(radius=cfg.radius, color=cfg.color))
    world.add(
        entity,
        Collider(
            diameter=cfg.collider_diameter,
            offset_x=cfg.collider_offset[0],
            offset_y=cfg.collider_offset[1],
            layer=cfg.collider_layer,
            mask=cfg.collider_mask,
            is_trigger=True,
        ),
    )
    world.add(
        entity,
        Damage(
            damage_rating=cfg.damage_rating,
            target_classes=cfg.target_classes or None,
            apply_mode="contact",
        ),
    )
    world.add(entity, Lifeline(duration=cfg.lifetime))

    return entity


evolvable_registry.register_factory("wooden_sword_attack", spawn_wooden_sword_attack)


__all__ = ["WoodenSwordAttackConfig", "spawn_wooden_sword_attack"]
