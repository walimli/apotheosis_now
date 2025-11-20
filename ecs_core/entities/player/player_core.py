"""Player entity bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from constants import LAYER_ENEMY, LAYER_PICKUP, LAYER_PLAYER, LAYER_WALL
from ecs_core.components import (
    AttackComponent,
    Controller,
    Health,
    Position,
    Speed,
    Soul,
    Velocity,
)
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
    max_soul: int = 100
    attack_id: str = "wooden_sword_attack"
    attack_cooldown: float = 0.5
    cooldown_timer: float = 0.0
    spawn_offset: float = 16.0  # Extra distance beyond collider radius
    offset_x: float = 0.0  # Fine-tuning offset along X after facing application
    offset_y: float = -12.0  # Fine-tuning offset along Y after facing application


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
    max_soul = int(cfg.max_soul)
    world.add(entity, Soul(max_soul=max_soul, current_soul=max_soul))
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
    world.add(
        entity,
        AttackComponent(
            attack_id=cfg.attack_id,
            attack_cooldown=cfg.attack_cooldown,
            cooldown_timer=cfg.cooldown_timer,
            spawn_offset=cfg.spawn_offset,
            offset_x=cfg.offset_x,
            offset_y=cfg.offset_y,
        ),
    )

    return entity


__all__ = ["PlayerConfig", "spawn_player"]
