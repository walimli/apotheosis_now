"""Default hardware-to-action bindings."""

from dataclasses import dataclass
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

import pygame

from .actions import PlayAction


@dataclass(frozen=True)
class InputBinding:
    """Represents a mapping from a hardware input to a play action."""

    action: PlayAction
    trigger: Tuple[str, int]
    value: object | None = None


def _hotbar_select_bindings() -> Tuple[InputBinding, ...]:
    bindings = []
    for offset, key in enumerate(
        (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9),
        start=0,
    ):
        bindings.append(
            InputBinding(
                action=PlayAction.HOTBAR_SELECT,
                trigger=("key", key),
                value=offset,
            )
        )
    return tuple(bindings)


DEFAULT_BINDINGS: Dict[PlayAction, Tuple[InputBinding, ...]] = {
    PlayAction.INTERACT_PRIMARY: (
        InputBinding(action=PlayAction.INTERACT_PRIMARY, trigger=("key", pygame.K_SPACE)),
    ),
    PlayAction.USE_INVENTORY: (
        InputBinding(action=PlayAction.USE_INVENTORY, trigger=("mouse_button", 1)),
    ),
    PlayAction.VARIANT_CYCLE: (
        InputBinding(action=PlayAction.VARIANT_CYCLE, trigger=("mouse_button", 3)),
    ),
    PlayAction.PILL_ACTIVATE: (
        InputBinding(action=PlayAction.PILL_ACTIVATE, trigger=("key", pygame.K_e)),
    ),
    PlayAction.PAUSE_TOGGLE: (
        InputBinding(action=PlayAction.PAUSE_TOGGLE, trigger=("key", pygame.K_ESCAPE)),
    ),
    PlayAction.INVENTORY_LOCK_TOGGLE: (
        InputBinding(
            action=PlayAction.INVENTORY_LOCK_TOGGLE,
            trigger=("key", pygame.K_q),
        ),
    ),
    PlayAction.HOTBAR_SCROLL: (
        InputBinding(action=PlayAction.HOTBAR_SCROLL, trigger=("mouse_wheel", 1), value=1),
        InputBinding(action=PlayAction.HOTBAR_SCROLL, trigger=("mouse_wheel", -1), value=-1),
    ),
    PlayAction.HOTBAR_SELECT: _hotbar_select_bindings(),
    PlayAction.SCROLL: (
        InputBinding(action=PlayAction.SCROLL, trigger=("mouse_wheel", 1), value=1),
        InputBinding(action=PlayAction.SCROLL, trigger=("mouse_wheel", -1), value=-1),
    ),
    PlayAction.MOVE: (
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_w), value=(0.0, -1.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_s), value=(0.0, 1.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_a), value=(-1.0, 0.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_d), value=(1.0, 0.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_UP), value=(0.0, -1.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_DOWN), value=(0.0, 1.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_LEFT), value=(-1.0, 0.0)),
        InputBinding(action=PlayAction.MOVE, trigger=("key_axis", pygame.K_RIGHT), value=(1.0, 0.0)),
    ),
}


def build_trigger_lookup(
    bindings: Dict[PlayAction, Tuple[InputBinding, ...]]
) -> Dict[Tuple[str, int], List[InputBinding]]:
    lookup: Dict[Tuple[str, int], List[InputBinding]] = defaultdict(list)
    for action_bindings in bindings.values():
        for binding in action_bindings:
            lookup[binding.trigger].append(binding)
    return lookup
