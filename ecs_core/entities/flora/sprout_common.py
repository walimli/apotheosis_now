"""Shared helpers for sprout entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

from constants import LAYER_PICKUP, LAYER_PLAYER
from ecs_core.components import Drops, Evolve, Health, Position
from ecs_core.components.collider import Collider
from ecs_core.components.entity_classes import Plant
from ecs_core.components.rendering_components import RenderableEntityComponent
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPRITE_ROOT = (
    PROJECT_ROOT / "assets" / "objects" / "grass_shrubs" / "bedlam_fauna"
).resolve()


@dataclass
class SproutConfig:
    sprite_path: str
    spawn_position: Tuple[float, float] = (0.0, 0.0)
    max_health: int = 1
    regeneration: int = 0
    defense: int = 0
    collider_diameter: int = 24
    collider_offset: Tuple[int, int] = (0, 0)
    collider_layer: int = LAYER_PICKUP
    collider_mask: int = LAYER_PLAYER
    drops: Dict[str, float] = field(default_factory=lambda: {"plant_coin": 1.0})
    xp: int = 0
    evolve_event: str = "HEARTBEAT"
    next_entity_id: Optional[str] = None
    registry_id: str = "sprout"
    render_layer: int = 0
    render_size: Optional[Tuple[int, int]] = None
    render_scale: float = 1.0
    render_anchor: Tuple[float, float] = (0.5, 0.5)
    render_offset: Tuple[int, int] = (0, 0)


def spawn_sprout_entity(
    world: World,
    entity_manager: EntityManager,
    *,
    config: SproutConfig,
) -> Entity:
    if not config.sprite_path:
        raise ValueError("SproutConfig.sprite_path must be set")

    entity = entity_manager.create()
    world.add(entity, Plant())
    world.add(
        entity,
        Position(x=int(config.spawn_position[0]), y=int(config.spawn_position[1])),
    )
    world.add(
        entity,
        Health(
            max_health=config.max_health,
            current_health=config.max_health,
            regeneration=config.regeneration,
            defense=config.defense,
        ),
    )
    world.add(entity, Drops(coins=dict(config.drops), xp=config.xp))
    world.add(
        entity,
        Collider(
            diameter=config.collider_diameter,
            offset_x=config.collider_offset[0],
            offset_y=config.collider_offset[1],
            layer=config.collider_layer,
            mask=config.collider_mask,
            is_trigger=False,
        ),
    )
    world.add(
        entity,
        RenderableEntityComponent(
            sprite_path=str(Path(config.sprite_path).resolve()),
            entity_id=config.registry_id,
            layer=config.render_layer,
            size=config.render_size,
            scale=config.render_scale,
            anchor=config.render_anchor,
            offset=config.render_offset,
        ),
    )
    world.add(
        entity,
        Evolve(
            time_event=config.evolve_event,
            next_entity_id=config.next_entity_id,
        ),
    )
    return entity


__all__ = ["SproutConfig", "SPRITE_ROOT", "spawn_sprout_entity"]
