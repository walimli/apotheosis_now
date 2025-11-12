"""Player-specific ECS components and configurations."""

from dataclasses import dataclass
from typing import Optional, Literal

# Import layer constants for collision system
from ecs_core.systems.collision.collision import (
    LAYER_PLAYER,
    LAYER_ENEMY,
    LAYER_WALL,
    LAYER_PICKUP,
)


@dataclass(frozen=True)
class Player:
    """Player entity marker component."""

    pass


@dataclass
class Speed:
    """Movement speed component."""

    pixels_per_second: float


@dataclass
class Health:
    """Health component for player entity."""

    max_health: int
    current_health: int
    regeneration: int = 0  # HP restored per HEARTBEAT
    defense: int = 0  # Flat damage reduction per attack
    sound: Optional[str] = None  # sound_registry key or None


@dataclass
class Controller:
    """Controller component defining entity control type."""

    type: Literal["player_input"]


@dataclass
class Collider:
    """Collider component for player collision detection."""

    diameter: int
    offset_x: int = 0
    offset_y: int = 0
    layer: int = LAYER_PLAYER
    mask: int = LAYER_ENEMY | LAYER_WALL | LAYER_PICKUP
    is_trigger: bool = False
