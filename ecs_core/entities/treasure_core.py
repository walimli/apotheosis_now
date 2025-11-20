"""Treasure core entity definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

from constants import (
    LAYER_ENEMY,
    LAYER_PLAYER,
    LAYER_PROJECTILE,
    LAYER_WALL,
)
from ecs_core.components import Drops, Health, Position, Velocity
from ecs_core.components.entity_classes import Object
from ecs_core.components.animation_components import Animation, AnimationState
from ecs_core.components.collider import Collider
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World
from services.monster_factory.evolve_registry import evolvable_registry

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "objects"
TREASURE_CORE_SPRITE = (ASSET_ROOT / "treasure_core.png").resolve()


@dataclass
class TreasureCoreConfig:
    """Configurable stats for treasure core spawns."""

    spawn_position: Tuple[float, float] = (0.0, 0.0)
    max_health: int = 3
    defense: int = 0
    drops: Dict[str, float] = field(default_factory=lambda: {"treasure_coin": 1.0})
    xp_reward: int = 25
    collider_diameter: int = 64
    collider_offset: Tuple[int, int] = (0, 0)
    animation_fps: float = 6.0


def spawn_treasure_core(
    world: World,
    entity_manager: EntityManager,
    *,
    config: Optional[TreasureCoreConfig] = None,
) -> Entity:
    cfg = config or TreasureCoreConfig()
    entity = entity_manager.create()

    world.add(entity, Object())
    world.add(
        entity,
        Position(
            x=float(cfg.spawn_position[0]),
            y=float(cfg.spawn_position[1]),
        ),
    )
    world.add(entity, Velocity(vx=0.0, vy=0.0))
    world.add(
        entity,
        Health(
            max_health=int(cfg.max_health),
            current_health=int(cfg.max_health),
            regeneration=0,
            defense=int(cfg.defense),
        ),
    )
    world.add(
        entity,
        Collider(
            diameter=int(cfg.collider_diameter),
            offset_x=int(cfg.collider_offset[0]),
            offset_y=int(cfg.collider_offset[1]),
            layer=LAYER_WALL,
            mask=LAYER_PLAYER | LAYER_ENEMY | LAYER_PROJECTILE,
            is_trigger=False,
        ),
    )
    world.add(entity, Drops(coins=dict(cfg.drops), xp=int(cfg.xp_reward)))
    world.add(
        entity,
        Animation(
            sheet_path=str(TREASURE_CORE_SPRITE),
            sheet_w=256,
            sheet_h=64,
            frame_w=64,
            frame_h=64,
            row_order=["idle"],
            actions={"idle": 4},
            fps=float(cfg.animation_fps),
            flip_x_for_left=False,
        ),
    )
    world.add(entity, AnimationState(current_action="idle", variant="default"))

    return entity


evolvable_registry.register_factory("treasure_core", spawn_treasure_core)


__all__ = ["TreasureCoreConfig", "spawn_treasure_core"]
