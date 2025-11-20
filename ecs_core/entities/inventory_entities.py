"""Coin and loot drop entity definitions."""

from __future__ import annotations

import random
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from constants import LAYER_PLAYER, LAYER_PICKUP
from ecs_core.components import PickupComponent, Position, Velocity
from ecs_core.components.animation_components import Animation, AnimationState
from ecs_core.components.physics import Friction
from ecs_core.components.collider import Collider
from ecs_core.components.entity_classes import Object
from ecs_core.components.rendering_components import RenderableEntityComponent
from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World
from services.monster_factory.evolve_registry import evolvable_registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TREASURE_COIN_SHEET = (
    PROJECT_ROOT / "assets" / "coins" / "drops" / "moon_coin" / "moon_coin_sheet_32.png"
).resolve()
TREASURE_COIN_FRAME_COUNT = 10
TREASURE_COIN_FRAME_SIZE: Tuple[int, int] = (32, 32)


@dataclass
class DropBounceConfig:
    """Configuration for drop bounce behavior."""
    initial_velocity_range: Tuple[float, float] = (80.0, 120.0)  # px/sec
    bounce_damping: float = 0.6  # 60% velocity retained after bounce
    bounce_cooldown: float = 0.2  # seconds between bounces
    max_bounces: int = 3


@dataclass
class CoinConfig:
    """Configuration for coin drops."""
    sprite_path: str
    spawn_position: Tuple[float, float]
    coin_value: int = 1
    collider_diameter: int = 16
    collider_offset: Tuple[int, int] = (0, 0)
    collider_layer: int = LAYER_PICKUP
    collider_mask: int = LAYER_PLAYER  # Only collide with player
    bounce_config: Optional[DropBounceConfig] = None
    registry_id: str = "coin"
    inventory_item_id: Optional[str] = None


def spawn_coin_entity(
    world: World,
    entity_manager: EntityManager,
    *,
    config: CoinConfig,
) -> Entity:
    """Spawn a coin entity with bouncing behavior."""
    if not config.sprite_path:
        raise ValueError("CoinConfig.sprite_path must be set")

    entity = entity_manager.create()
    world.add(entity, Object())  # Use Object as base marker for pickable items

    # Position
    world.add(
        entity,
        Position(x=int(config.spawn_position[0]), y=int(config.spawn_position[1])),
    )

    # Collider
    world.add(
        entity,
        Collider(
            diameter=config.collider_diameter,
            offset_x=config.collider_offset[0],
            offset_y=config.collider_offset[1],
            layer=config.collider_layer,
            mask=config.collider_mask,
            is_trigger=True,  # Triggers pickup, doesn't block movement
        ),
    )

    # Renderable
    world.add(
        entity,
        RenderableEntityComponent(
            sprite_path=str(Path(config.sprite_path).resolve()),
            entity_id=config.registry_id,
            layer=1,  # Above ground, below player
            size=(32, 32),
            scale=1.0,
            anchor=(0.5, 0.5),
            offset=(0, 0),
        ),
    )

    # Add velocity for bounce behavior if configured
    if config.bounce_config:
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*config.bounce_config.initial_velocity_range)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        world.add(entity, Velocity(vx=vx, vy=vy))
        # Add friction to stop the bounce
        world.add(entity, Friction(drag=0.05, min_velocity=10.0))

    pickup_item_id = config.inventory_item_id or config.registry_id
    if not pickup_item_id:
        raise ValueError("Pickup entities require an inventory item id")
    pickup_quantity = max(1, int(config.coin_value))
    world.add(
        entity,
        PickupComponent(
            item_id=pickup_item_id,
            quantity=pickup_quantity,
        ),
    )

    return entity


def spawn_coin_at_position(
    world: World,
    entity_manager: EntityManager,
    position: Tuple[int, int],
    *,
    coin_value: int = 1,
    sprite_path: str = "assets/objects/coin.png",  # Default path
    registry_id: str = "coin",
    inventory_item_id: Optional[str] = None,
) -> Entity:
    """Convenience function to spawn a coin at a specific position."""
    config = CoinConfig(
        sprite_path=sprite_path,
        spawn_position=position,
        coin_value=coin_value,
        bounce_config=DropBounceConfig(),
        registry_id=registry_id,
        inventory_item_id=inventory_item_id,
    )
    return spawn_coin_entity(world, entity_manager, config=config)


def spawn_treasure_coin_drop(
    world: World,
    entity_manager: EntityManager,
    *,
    bounce_config: Optional[DropBounceConfig] = None,
) -> Entity:
    """Spawn the animated treasure coin drop entity."""
    entity = entity_manager.create()
    world.add(entity, Object())
    world.add(entity, Position(x=0, y=0))
    world.add(
        entity,
        Collider(
            diameter=32,
            offset_x=0,
            offset_y=0,
            layer=LAYER_PICKUP,
            mask=LAYER_PLAYER,
            is_trigger=True,
        ),
    )
    world.add(
        entity,
        PickupComponent(
            item_id="treasure_coin",
            quantity=1,
        ),
    )
    world.add(
        entity,
        Animation(
            sheet_path=str(TREASURE_COIN_SHEET),
            sheet_w=TREASURE_COIN_FRAME_SIZE[0] * TREASURE_COIN_FRAME_COUNT,
            sheet_h=TREASURE_COIN_FRAME_SIZE[1],
            frame_w=TREASURE_COIN_FRAME_SIZE[0],
            frame_h=TREASURE_COIN_FRAME_SIZE[1],
            row_order=["idle"],
            actions={"idle": TREASURE_COIN_FRAME_COUNT},
            fps=12.0,
            flip_x_for_left=False,
        ),
    )
    world.add(entity, AnimationState(current_action="idle", variant="default"))

    bounce = bounce_config or DropBounceConfig()
    angle = random.uniform(0.0, 2 * math.pi)
    speed = random.uniform(*bounce.initial_velocity_range)
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed
    world.add(entity, Velocity(vx=vx, vy=vy))
    world.add(entity, Friction(drag=0.05, min_velocity=10.0))
    return entity


def _create_coin_factory(sprite_path: str, registry_id: str):
    """Create a factory function for a specific coin type."""

    def factory(world: World, entity_manager: EntityManager) -> Entity:
        return spawn_coin_at_position(
            world,
            entity_manager,
            (0, 0),
            sprite_path=sprite_path,
            registry_id=registry_id,
            inventory_item_id=registry_id,
        )

    return factory


# Register all coin types
# Note: In a full implementation, we might load these from coins.json dynamically,
# but for now we register them explicitly to match the drops.json metadata.
_COIN_TYPES = {
    "coin": "assets/objects/coin.png",
    "bone_dust": "assets/coins/inventory/bone_dust_coin.png",
    "plant_coin": "assets/coins/inventory/plant_coin.png",
    "spore_coin": "assets/coins/inventory/spore_coin.png",
    "stone_coin": "assets/coins/inventory/stone_coin.png",
    "glow_spore_coin": "assets/coins/inventory/glow_spore_coin.png",
    "log_coin": "assets/coins/inventory/log_coin.png",
    "crystal_coin": "assets/coins/inventory/crystal_coin.png",
    "clay_coin": "assets/coins/inventory/clay_coin.png",
    "redrock_coin": "assets/coins/inventory/redrock_coin.png",
    "skull_shrine_coin": "assets/coins/inventory/skull_shrine_coin.png",
    "skull_candle_coin": "assets/coins/inventory/skull_candle_coin.png",
    "stone_fence_coin": "assets/coins/inventory/stone_fence_coin.png",
    "wood_fence_coin": "assets/coins/inventory/wood_fence_coin.png",
    "bucket_coin": "assets/coins/inventory/bucket_coin.png",
}

for coin_id, sprite_path in _COIN_TYPES.items():
    evolvable_registry.register_factory(
        coin_id,
        _create_coin_factory(sprite_path, registry_id=coin_id),
    )

evolvable_registry.register_factory(
    "treasure_coin",
    lambda world, entity_manager: spawn_treasure_coin_drop(world, entity_manager),
)


__all__ = [
    "CoinConfig",
    "DropBounceConfig",
    "spawn_coin_entity",
    "spawn_coin_at_position",
    "spawn_treasure_coin_drop",
]
