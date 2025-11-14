"""Sprout entity definition."""

from __future__ import annotations

from typing import Optional

from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.entities.evolve_registry import evolvable_registry
from ecs_core.entities.flora.sprout_common import (
    SPRITE_ROOT,
    SproutConfig,
    spawn_sprout_entity,
)
from ecs_core.worlds.world import World


def _default_config() -> SproutConfig:
    return SproutConfig(
        sprite_path=str((SPRITE_ROOT / "flower_1.png").resolve()),
        registry_id="sprout",
        next_entity_id="twice_sprout",
    )


def spawn_sprout(
    world: World,
    entity_manager: EntityManager,
    *,
    config: Optional[SproutConfig] = None,
) -> Entity:
    """Create and register the base sprout entity inside the ECS world."""

    return spawn_sprout_entity(world, entity_manager, config=config or _default_config())


evolvable_registry.register_factory("sprout", spawn_sprout)


__all__ = ["spawn_sprout", "SproutConfig"]
