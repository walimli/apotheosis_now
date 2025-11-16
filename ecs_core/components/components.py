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
    render_x: float | None = None
    render_y: float | None = None

    def __post_init__(self) -> None:
        if self.render_x is None:
            self.render_x = float(self.x)
        if self.render_y is None:
            self.render_y = float(self.y)


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
class Soul:
    max_soul: int
    current_soul: Optional[int] = None
    depleted_announced: bool = False

    def __post_init__(self) -> None:
        self.max_soul = int(max(0, self.max_soul))
        if self.current_soul is None:
            self.current_soul = self.max_soul
        self.current_soul = int(max(0, min(int(self.current_soul), self.max_soul)))


@dataclass
class Evolve:
    time_event: str  # e.g., TimeEventType.DAWN_STARTED
    next_entity_id: Optional[str] = None  # Registry ID to become, or None


ControllerType = Literal["player_input", "mob_aggressive", "mob_passive", "npc"]


@dataclass
class Controller:
    type: ControllerType


@dataclass
class Drops:
    coins: Dict[str, float]  # "copper_coin": 1.25, "silver_coin": 0.4
    xp: int  # XP value to publish on death
