"""Stone fence crafted entities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from constants import LAYER_ENEMY, LAYER_PLAYER, LAYER_PROJECTILE, LAYER_WALL
from ecs_core.components import (
    Collider,
    Drops,
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
class FenceVariantConfig:
    entity_id: str
    sprite_rel_path: str
    connecting_edges: Tuple[str, ...]
    z_index: int = 2
    scale: float = 1.0
    durability: int = 3
    drop_item: str = "stone_fence_coin"
    drop_quantity: float = 1.0


FENCE_VARIANTS: Dict[str, FenceVariantConfig] = {
    "stone_fence_top": FenceVariantConfig(
        entity_id="stone_fence_top",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_top.png",
        connecting_edges=("bottom",),
    ),
    "stone_fence_bottom": FenceVariantConfig(
        entity_id="stone_fence_bottom",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_bottom.png",
        connecting_edges=("top",),
    ),
    "stone_fence_left": FenceVariantConfig(
        entity_id="stone_fence_left",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_left.png",
        connecting_edges=("right",),
    ),
    "stone_fence_right": FenceVariantConfig(
        entity_id="stone_fence_right",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_right.png",
        connecting_edges=("left",),
    ),
    "stone_fence_hcon": FenceVariantConfig(
        entity_id="stone_fence_hcon",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_hcon.png",
        connecting_edges=("left", "right"),
    ),
    "stone_fence_vcon": FenceVariantConfig(
        entity_id="stone_fence_vcon",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_vcon.png",
        connecting_edges=("top", "bottom"),
    ),
    "stone_fence_tlc": FenceVariantConfig(
        entity_id="stone_fence_tlc",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_tlc.png",
        connecting_edges=("bottom", "right"),
    ),
    "stone_fence_trc": FenceVariantConfig(
        entity_id="stone_fence_trc",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_trc.png",
        connecting_edges=("bottom", "left"),
    ),
    "stone_fence_blc": FenceVariantConfig(
        entity_id="stone_fence_blc",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_blc.png",
        connecting_edges=("top", "right"),
    ),
    "stone_fence_brc": FenceVariantConfig(
        entity_id="stone_fence_brc",
        sprite_rel_path="assets/placeables/fences/stone_fence/stone_fence_brc.png",
        connecting_edges=("top", "left"),
    ),
}


def _spawn_variant(world: World, entity_manager: EntityManager, config: FenceVariantConfig) -> Entity:
    entity = entity_manager.create()
    world.add(entity, Object())
    world.add(entity, Position(x=0, y=0))
    world.add(entity, StaticBody())
    world.add(
        entity,
        Collider(
            diameter=64,
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
            anchor=(0.5, 0.6),
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
    world.add(entity, Drops(coins={config.drop_item: config.drop_quantity}, xp=1))
    return entity


def spawn_stone_fence(world: World, entity_manager: EntityManager, variant_id: str) -> Entity:
    config = FENCE_VARIANTS[variant_id]
    return _spawn_variant(world, entity_manager, config)


def _register_factories() -> None:
    for variant_id in FENCE_VARIANTS.keys():
        evolvable_registry.register_factory(
            variant_id,
            lambda world, entity_manager, vid=variant_id: spawn_stone_fence(world, entity_manager, vid),
        )


_register_factories()

__all__ = ["spawn_stone_fence", "FENCE_VARIANTS"]
