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

    def _normalize(self) -> None:
        self.max_health = int(max(0, self.max_health))
        self.current_health = int(max(0, min(self.current_health, self.max_health)))

    def take_damage(self, amount: int) -> int:
        """Apply direct damage ignoring defense and return amount removed."""
        dmg = int(amount)
        if dmg <= 0:
            return 0
        self._normalize()
        before = self.current_health
        self.current_health = max(0, self.current_health - dmg)
        return before - self.current_health

    def heal(self, amount: int) -> int:
        """Restore health up to max_health and return amount healed."""
        heal_amount = int(amount)
        if heal_amount <= 0:
            return 0
        self._normalize()
        before = self.current_health
        self.current_health = min(self.max_health, self.current_health + heal_amount)
        return self.current_health - before


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
        self.depleted_announced = bool(self.depleted_announced)

    def _normalize(self) -> None:
        if self.current_soul is None:
            self.current_soul = self.max_soul
        self.current_soul = int(max(0, min(int(self.current_soul), self.max_soul)))

    def can_spend(self, amount: int) -> bool:
        spend = int(amount)
        if spend <= 0:
            return True
        self._normalize()
        return self.current_soul is not None and self.current_soul >= spend

    def consume(self, amount: int) -> bool:
        """Consume soul if available; returns True on success."""
        spend = int(amount)
        if spend <= 0:
            return True
        if not self.can_spend(spend):
            return False
        assert self.current_soul is not None
        self.current_soul -= spend
        if self.current_soul <= 0:
            self.current_soul = 0
            self.depleted_announced = True
        else:
            self.depleted_announced = False
        return True

    def announce_blocked(self) -> None:
        """Set the depleted flag so UI/services can react."""
        self.depleted_announced = True


@dataclass
class Evolve:
    time_event: str  # e.g., TimeEventType.DAWN_STARTED
    next_entity_id: Optional[str] = None  # Registry ID to become, or None


@dataclass
class Lifeline:
    duration: float  # Total lifetime in seconds
    remaining: float | None = None  # Remaining time; defaults to duration

    def __post_init__(self) -> None:
        if self.remaining is None:
            self.remaining = float(self.duration)
        self.duration = float(max(0.0, self.duration))
        self.remaining = float(max(0.0, self.remaining))


@dataclass
class Damage:
    damage_rating: float
    target_classes: tuple[type, ...] | None = None
    apply_mode: Literal["contact", "time_event"] = "contact"
    time_event: Optional[str] = None

    def __post_init__(self) -> None:
        self.damage_rating = float(max(0.0, self.damage_rating))
        if self.target_classes:
            self.target_classes = tuple(self.target_classes)
        if self.time_event:
            self.time_event = str(self.time_event)


ControllerType = Literal["player_input", "mob_aggressive", "mob_passive", "npc"]


@dataclass
class Controller:
    type: ControllerType


@dataclass
class Drops:
    coins: Dict[str, float]  # "copper_coin": 1.25, "silver_coin": 0.4
    xp: int  # XP value to publish on death


@dataclass
class PickupComponent:
    """Marks an entity as collectible and describes its inventory payload."""

    item_id: str
    quantity: int = 1
    prefer_slot: Optional[int] = None

    def __post_init__(self) -> None:
        self.item_id = str(self.item_id or "").strip()
        if not self.item_id:
            raise ValueError("PickupComponent requires a non-empty item_id")
        self.quantity = int(max(0, self.quantity or 0))
        if self.prefer_slot is not None:
            self.prefer_slot = int(self.prefer_slot)
