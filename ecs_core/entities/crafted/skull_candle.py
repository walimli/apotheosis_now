"""Skull candle crafted entity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from constants import LAYER_ENEMY, LAYER_PLAYER, LAYER_PROJECTILE, LAYER_WALL
from ecs_core.components import (
    Animation,
    AnimationState,
    Collider,
    Drops,
    Health,
    Object,
    Position,
    ProtectionZoneComponent,
    RenderableEntityComponent,
    SafeZoneComponent,
    StaticBody,
)
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World
from services.monster_factory.evolve_registry import evolvable_registry

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class SkullCandleConfig:
    sprite_rel_path: str = "assets/placeables/skull_candle/skull_candle_sheet.png"
    z_index: int = 3
    scale: float = 1.0
    durability: int = 6
    safe_zone_radius: float = 2.0
    protection_radius: float = 2.0
    fps: float = 6.0
    columns: int = 6
    rows: int = 3
    sheet_size: tuple[int, int] = (288, 240)

    @property
    def frame_dimensions(self) -> tuple[int, int]:
        width, height = self.sheet_size
        return (width // self.columns, height // self.rows)

    @property
    def frame_count(self) -> int:
        return self.columns * self.rows


CONFIG = SkullCandleConfig()


def spawn_skull_candle(world: World, entity_manager: EntityManager) -> Entity:
    entity = entity_manager.create()
    world.add(entity, Object())
    world.add(entity, Position(x=0, y=0))
    world.add(entity, StaticBody())
    world.add(
        entity,
        Collider(
            diameter=48,
            offset_x=0,
            offset_y=0,
            layer=LAYER_WALL,
            mask=LAYER_PLAYER | LAYER_ENEMY | LAYER_WALL | LAYER_PROJECTILE,
            is_trigger=False,
        ),
    )
    sprite_path = str((PROJECT_ROOT / CONFIG.sprite_rel_path).resolve())
    world.add(
        entity,
        RenderableEntityComponent(
            sprite_path=sprite_path,
            entity_id="skull_candle",
            layer=CONFIG.z_index,
            scale=CONFIG.scale,
            anchor=(0.5, 0.7),
            offset=(0, 0),
        ),
    )
    world.add(
        entity,
        Health(
            max_health=CONFIG.durability,
            current_health=CONFIG.durability,
            regeneration=0,
            defense=0,
        ),
    )
    world.add(entity, Drops(coins={"skull_candle_coin": 1.0}, xp=0))
    world.add(entity, SafeZoneComponent(radius_tiles=CONFIG.safe_zone_radius))
    world.add(entity, ProtectionZoneComponent(radius_tiles=CONFIG.protection_radius))
    frame_w, frame_h = CONFIG.frame_dimensions
    world.add(
        entity,
        Animation(
            sheet_path=sprite_path,
            sheet_w=CONFIG.sheet_size[0],
            sheet_h=CONFIG.sheet_size[1],
            frame_w=frame_w,
            frame_h=frame_h,
            row_order=["idle"],
            actions={"idle": CONFIG.frame_count},
            fps=CONFIG.fps,
            flip_x_for_left=False,
        ),
    )
    world.add(entity, AnimationState(current_action="idle"))
    return entity


evolvable_registry.register_factory("skull_candle", spawn_skull_candle)

__all__ = ["spawn_skull_candle"]
