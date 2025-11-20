"""Glow tree crafted entities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from constants import LAYER_ENEMY, LAYER_PLAYER, LAYER_PROJECTILE, LAYER_WALL
from ecs_core.components import (
    Animation,
    AnimationState,
    Collider,
    Drops,
    Evolve,
    Health,
    Object,
    Position,
    RenderableEntityComponent,
    SafeZoneComponent,
    StaticBody,
)
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World
from services.monster_factory.evolve_registry import evolvable_registry

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AnimationConfig:
    sheet_rel_path: str
    sheet_size: tuple[int, int]
    columns: int
    rows: int
    fps: float = 6.0

    @property
    def frame_dimensions(self) -> tuple[int, int]:
        width, height = self.sheet_size
        return (width // self.columns, height // self.rows)

    @property
    def frame_count(self) -> int:
        return self.columns * self.rows


@dataclass(frozen=True)
class GlowStageConfig:
    entity_id: str
    sprite_rel_path: str
    z_index: int
    scale: float
    durability: int
    drops: Dict[str, float]
    safe_zone_radius: float
    next_stage_id: Optional[str] = None
    animation: Optional[AnimationConfig] = None


def _avg_quantity(min_qty: int, max_qty: int) -> float:
    return (float(min_qty) + float(max_qty)) / 2.0


GLOW_TREE_STAGES: Dict[str, GlowStageConfig] = {
    "glow_seedling": GlowStageConfig(
        entity_id="glow_seedling",
        sprite_rel_path="assets/placeables/glow_tree/glow_seedling.png",
        z_index=2,
        scale=1.0,
        durability=1,
        drops={"spore_coin": _avg_quantity(1, 2)},
        safe_zone_radius=2.0,
        next_stage_id="glow_sapling",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/glow_tree/glow_seedling.png",
            sheet_size=(192, 64),
            columns=3,
            rows=1,
            fps=6.0,
        ),
    ),
    "glow_sapling": GlowStageConfig(
        entity_id="glow_sapling",
        sprite_rel_path="assets/placeables/glow_tree/glow_sapling.png",
        z_index=3,
        scale=1.0,
        durability=4,
        drops={"log_coin": _avg_quantity(1, 2)},
        safe_zone_radius=2.0,
        next_stage_id="glow_mature",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/glow_tree/glow_sapling.png",
            sheet_size=(384, 192),
            columns=6,
            rows=3,
            fps=6.0,
        ),
    ),
    "glow_mature": GlowStageConfig(
        entity_id="glow_mature",
        sprite_rel_path="assets/placeables/glow_tree/glow_mature.png",
        z_index=3,
        scale=1.0,
        durability=6,
        drops={
            "log_coin": _avg_quantity(1, 2),
            "crystal_coin": _avg_quantity(1, 2),
        },
        safe_zone_radius=2.0,
        next_stage_id="glow_ancient",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/glow_tree/glow_mature.png",
            sheet_size=(480, 288),
            columns=6,
            rows=3,
            fps=6.0,
        ),
    ),
    "glow_ancient": GlowStageConfig(
        entity_id="glow_ancient",
        sprite_rel_path="assets/placeables/glow_tree/glow_ancient.png",
        z_index=3,
        scale=1.0,
        durability=8,
        drops={
            "log_coin": _avg_quantity(1, 2),
            "treasure_coin": _avg_quantity(1, 2),
        },
        safe_zone_radius=2.0,
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/glow_tree/glow_ancient.png",
            sheet_size=(660, 384),
            columns=6,
            rows=3,
            fps=6.0,
        ),
    ),
}


def _apply_animation(world: World, entity: Entity, config: AnimationConfig) -> None:
    sheet_path = str((PROJECT_ROOT / config.sheet_rel_path).resolve())
    frame_w, frame_h = config.frame_dimensions
    world.add(
        entity,
        Animation(
            sheet_path=sheet_path,
            sheet_w=config.sheet_size[0],
            sheet_h=config.sheet_size[1],
            frame_w=frame_w,
            frame_h=frame_h,
            row_order=["idle"],
            actions={"idle": config.frame_count},
            fps=config.fps,
            flip_x_for_left=False,
        ),
    )
    world.add(entity, AnimationState(current_action="idle"))


def _spawn_stage(world: World, entity_manager: EntityManager, config: GlowStageConfig) -> Entity:
    entity = entity_manager.create()
    world.add(entity, Object())
    world.add(entity, Position(x=0, y=0))
    world.add(entity, StaticBody())
    world.add(
        entity,
        Collider(
            diameter=32,
            offset_x=0,
            offset_y=0,
            layer=LAYER_WALL,
            mask=LAYER_PLAYER | LAYER_ENEMY | LAYER_WALL | LAYER_PROJECTILE,
            is_trigger=False,
        ),
    )
    world.add(
        entity,
        RenderableEntityComponent(
            sprite_path=str((PROJECT_ROOT / config.sprite_rel_path).resolve()),
            entity_id=config.entity_id,
            layer=config.z_index,
            scale=config.scale,
            anchor=(0.5, 0.5),
            offset=(0, 0),
        ),
    )
    world.add(
        entity,
        Health(
            max_health=config.durability,
            current_health=config.durability,
            regeneration=0,
            defense=0,
        ),
    )
    world.add(entity, Drops(coins=dict(config.drops), xp=0))
    if config.safe_zone_radius > 0:
        world.add(entity, SafeZoneComponent(radius_tiles=config.safe_zone_radius))
    if config.animation:
        _apply_animation(world, entity, config.animation)
    if config.next_stage_id:
        world.add(entity, Evolve(time_event="DAWN_STARTED", next_entity_id=config.next_stage_id))
    return entity


def spawn_glow_entity(world: World, entity_manager: EntityManager, stage_id: str) -> Entity:
    config = GLOW_TREE_STAGES[stage_id]
    return _spawn_stage(world, entity_manager, config)


def _register_factories() -> None:
    for stage_id in GLOW_TREE_STAGES.keys():
        evolvable_registry.register_factory(
            stage_id,
            lambda world, entity_manager, sid=stage_id: spawn_glow_entity(world, entity_manager, sid),
        )


_register_factories()

__all__ = ["spawn_glow_entity", "GLOW_TREE_STAGES"]
