"""Player entity bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from constants import LAYER_ENEMY, LAYER_PICKUP, LAYER_PLAYER, LAYER_WALL
from ecs_core.components import (
    Controller,
    Health,
    Position,
    Speed,
    Velocity,
)
from ecs_core.components.animation_components import Animation, AnimationState
from ecs_core.components.collider import Collider
from ecs_core.components.entity_classes import Player
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World


@dataclass(frozen=True)
class PlayerConfig:
    """Configurable defaults for spawning the player entity."""

    spawn_position: Tuple[float, float] = (400.0, 300.0)
    speed: float = 512.0
    collider_diameter: int = 32
    animation_size: int = 32
    max_health: int = 10
    controller_type: str = "player_input"


def spawn_player(
    world: World,
    entity_manager: EntityManager,
    *,
    config: Optional[PlayerConfig] = None,
) -> Entity:
    """Create and register the player entity inside the ECS world."""

    cfg = config or PlayerConfig()
    entity = entity_manager.create()

    world.add(entity, Player())
    world.add(
        entity,
        Position(x=float(cfg.spawn_position[0]), y=float(cfg.spawn_position[1])),
    )
    world.add(entity, Velocity(vx=0.0, vy=0.0))
    world.add(entity, Speed(pixels_per_second=float(cfg.speed)))
    world.add(
        entity,
        Health(
            max_health=int(cfg.max_health),
            current_health=int(cfg.max_health),
            regeneration=0,
            defense=0,
        ),
    )
    world.add(entity, Controller(type=cfg.controller_type))
    world.add(
        entity,
        Collider(
            diameter=int(cfg.collider_diameter),
            layer=LAYER_PLAYER,
            mask=LAYER_ENEMY | LAYER_WALL | LAYER_PICKUP,
            is_trigger=False,
        ),
    )

    anim_size = int(cfg.animation_size)
    world.add(
        entity,
        Animation(
            sheet_path=None,
            sheet_w=anim_size,
            sheet_h=anim_size,
            frame_w=anim_size,
            frame_h=anim_size,
            row_order=["idle"],
            actions={"idle": 1},
            fps=1.0,
            flip_x_for_left=True,
        ),
    )
    world.add(entity, AnimationState())
    return entity


__all__ = ["PlayerConfig", "spawn_player"]
