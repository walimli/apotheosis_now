# systems/ecs/components.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Literal, Dict, Tuple, List


@dataclass
class Speed:
    pixels_per_second: float


@dataclass
class Renderable:
    radius: int
    color: tuple = (255, 255, 255)


@dataclass
class Velocity:
    vx: float
    vy: float


@dataclass
class Position:
    x: int
    y: int


# Example game-specific ones
@dataclass(frozen=True)
class HeldItem:
    item_id: str


@dataclass(frozen=True)
class Harvestable:
    growth: float
    ready: bool = False


@dataclass
class Health:
    max_health: int
    current_health: int
    regeneration: int  # HP restored per HEARTBEAT
    defense: int  # Flat damage reduction per attack
    sound: Optional[str] = None  # sound_registry key or None


@dataclass
class Evolve:
    time_event: str  # e.g., TimeEventType.DAWN, TimeEventType.NIGHTFALL
    stage: Optional[int] = None  # Entity ID to become, or None


ControllerType = Literal["player_input", "mob_aggressive", "mob_passive", "npc"]


@dataclass
class Controller:
    type: ControllerType


@dataclass
class Drops:
    coins: Dict[str, float]  # "copper_coin": 1.25, "silver_coin": 0.4
    xp: int  # XP value to publish on death
