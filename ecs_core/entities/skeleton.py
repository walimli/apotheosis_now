"""Skeleton entity definition without aggressive AI wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

from constants import LAYER_ENEMY, LAYER_PLAYER, LAYER_PROJECTILE, LAYER_WALL
from ecs_core.components import (
    Animation,
    AnimationState,
    AggressivePathfindingComponent,
    Controller,
    Drops,
    Health,
    Mob,
    Position,
    Speed,
    Velocity,
)
from ecs_core.components.collider import Collider
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World
from services.monster_factory.evolve_registry import evolvable_registry

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "mobs" / "skeleton_basic"


@dataclass
class SkeletonConfig:
    """Configurable stats for wiring skeleton entities into the ECS world."""

    spawn_position: Tuple[float, float] = (0.0, 0.0)
    speed_px_per_s: float = 32.0
    max_health: int = 3
    regeneration: int = 0
    defense: int = 0
    xp_reward: int = 1
    coin_drops: Dict[str, float] = field(default_factory=dict)
    collider_diameter: int = 32
    collider_offset: Tuple[int, int] = (0, 0)


def spawn_skeleton(
    world: World,
    entity_manager: EntityManager,
    *,
    config: Optional[SkeletonConfig] = None,
) -> Entity:
    """Create the skeleton entity inside the ECS world."""
    cfg = config or SkeletonConfig()
    entity = entity_manager.create()

    world.add(entity, Mob())
    world.add(
        entity,
        Position(
            x=float(cfg.spawn_position[0]),
            y=float(cfg.spawn_position[1]),
        ),
    )
    world.add(entity, Velocity(vx=0.0, vy=0.0))
    world.add(entity, Speed(pixels_per_second=float(cfg.speed_px_per_s)))
    world.add(
        entity,
        Health(
            max_health=int(cfg.max_health),
            current_health=int(cfg.max_health),
            regeneration=int(cfg.regeneration),
            defense=int(cfg.defense),
        ),
    )
    world.add(entity, Controller(type="mob_aggressive"))
    world.add(
        entity,
        Collider(
            diameter=int(cfg.collider_diameter),
            offset_x=int(cfg.collider_offset[0]),
            offset_y=int(cfg.collider_offset[1]),
            layer=LAYER_ENEMY,
            mask=LAYER_PLAYER | LAYER_WALL | LAYER_ENEMY | LAYER_PROJECTILE,
            is_trigger=False,
        ),
    )
    world.add(entity, Drops(coins=dict(cfg.coin_drops), xp=int(cfg.xp_reward)))
    world.add(entity, AggressivePathfindingComponent())
    _attach_animation(world, entity)
    return entity


def _attach_animation(world: World, entity: Entity) -> None:
    row_order = [
        "pass",
        "pass",
        "walk",
        "damaged",
        "idle",
        "die",
        "attack_1",
        "attack_2",
        "attack_3",
    ]
    actions = {
        "walk": 8,
        "damaged": 5,
        "idle": 8,
        "die": 6,
        "attack_1": 13,
        "attack_2": 17,
        "attack_3": 23,
    }
    sheet_variants = {
        "default": str((ASSET_ROOT / "skelly_front.png").resolve()),
        "front": str((ASSET_ROOT / "skelly_front.png").resolve()),
        "back": str((ASSET_ROOT / "skelly_back.png").resolve()),
        "side": str((ASSET_ROOT / "skelly_right.png").resolve()),
    }
    anim = Animation(
        sheet_path=sheet_variants["front"],
        sheet_w=1104,
        sheet_h=432,
        frame_w=48,
        frame_h=48,
        row_order=row_order,
        actions=actions,
        fps=10.0,
        flip_x_for_left=True,
        sheet_variants=sheet_variants,
        flip_variants={"side"},
    )
    state = AnimationState(current_action="idle", variant="front")
    world.add(entity, anim)
    world.add(entity, state)


evolvable_registry.register_factory("skeleton_basic", spawn_skeleton)


__all__ = ["SkeletonConfig", "spawn_skeleton"]
