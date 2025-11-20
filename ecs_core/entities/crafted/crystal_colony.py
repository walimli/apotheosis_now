"""Crystal colony crafted entities."""

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
class CrystalStageConfig:
    entity_id: str
    sprite_rel_path: str
    z_index: int
    scale: float
    durability: int
    drops: Dict[str, float]
    next_stage_id: Optional[str] = None
    animation: Optional[AnimationConfig] = None


def _avg_quantity(min_qty: int, max_qty: int) -> float:
    return (float(min_qty) + float(max_qty)) / 2.0


CRYSTAL_STAGES: Dict[str, CrystalStageConfig] = {
    "crystal_seedling": CrystalStageConfig(
        entity_id="crystal_seedling",
        sprite_rel_path="assets/placeables/crystal_colony/crystal_seedling.png",
        z_index=2,
        scale=1.0,
        durability=6,
        drops={"crystal_coin": _avg_quantity(1, 1)},
        next_stage_id="crystal_sapling",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/crystal_colony/crystal_seedling.png",
            sheet_size=(192, 64),
            columns=3,
            rows=1,
            fps=6.0,
        ),
    ),
    "crystal_sapling": CrystalStageConfig(
        entity_id="crystal_sapling",
        sprite_rel_path="assets/placeables/crystal_colony/crystal_sapling.png",
        z_index=2,
        scale=1.0,
        durability=6,
        drops={"crystal_coin": _avg_quantity(1, 2)},
        next_stage_id="crystal_mature",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/crystal_colony/crystal_sapling.png",
            sheet_size=(192, 64),
            columns=3,
            rows=1,
            fps=6.0,
        ),
    ),
    "crystal_mature": CrystalStageConfig(
        entity_id="crystal_mature",
        sprite_rel_path="assets/placeables/crystal_colony/crystal_mature.png",
        z_index=2,
        scale=1.0,
        durability=6,
        drops={"crystal_coin": _avg_quantity(2, 3)},
        next_stage_id="crystal_ancient",
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/crystal_colony/crystal_mature.png",
            sheet_size=(192, 64),
            columns=3,
            rows=1,
            fps=6.0,
        ),
    ),
    "crystal_ancient": CrystalStageConfig(
        entity_id="crystal_ancient",
        sprite_rel_path="assets/placeables/crystal_colony/crystal_ancient.png",
        z_index=2,
        scale=1.0,
        durability=6,
        drops={"crystal_coin": _avg_quantity(3, 4)},
        animation=AnimationConfig(
            sheet_rel_path="assets/placeables/crystal_colony/crystal_ancient.png",
            sheet_size=(192, 64),
            columns=3,
            rows=1,
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


def _spawn_stage(world: World, entity_manager: EntityManager, config: CrystalStageConfig) -> Entity:
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
            anchor=(0.5, 0.7),
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
    if config.animation:
        _apply_animation(world, entity, config.animation)
    if config.next_stage_id:
        world.add(entity, Evolve(time_event="DAWN_STARTED", next_entity_id=config.next_stage_id))
    return entity


def spawn_crystal_entity(world: World, entity_manager: EntityManager, stage_id: str) -> Entity:
    config = CRYSTAL_STAGES[stage_id]
    return _spawn_stage(world, entity_manager, config)


def _register_factories() -> None:
    for stage_id in CRYSTAL_STAGES.keys():
        evolvable_registry.register_factory(
            stage_id,
            lambda world, entity_manager, sid=stage_id: spawn_crystal_entity(world, entity_manager, sid),
        )


_register_factories()

__all__ = ["spawn_crystal_entity", "CRYSTAL_STAGES"]
