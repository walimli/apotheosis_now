"""Canonical action identifiers for the play input system."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class PlayAction(Enum):
    """Enumerated player-facing input intents."""

    MOVE = auto()
    USE_INVENTORY = auto()
    INTERACT_PRIMARY = auto()
    VARIANT_CYCLE = auto()
    HOTBAR_SCROLL = auto()
    HOTBAR_SELECT = auto()
    PILL_ACTIVATE = auto()
    PAUSE_TOGGLE = auto()
    CRAFT_TOGGLE = auto()
    INVENTORY_LOCK_TOGGLE = auto()
    CURSOR_MOVE = auto()
    SCROLL = auto()


@dataclass(frozen=True)
class AxisAction:
    """Descriptor for axis-based actions (e.g., movement)."""

    action: PlayAction
    components: Tuple[str, ...] = ("x", "y")


MOVE_AXIS = AxisAction(action=PlayAction.MOVE, components=("x", "y"))
