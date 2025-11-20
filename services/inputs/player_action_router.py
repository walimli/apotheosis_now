from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

from .actions import PlayAction
from .adapters import BaseInputAdapter
from .state import PlayInputState


@dataclass
class PrimaryActionRouter(BaseInputAdapter):
    """Delegates primary-click actions to combat when applicable."""

    inventory: Any
    attack_service: Any
    sword_item_ids: Tuple[str, ...] = ("sword_wooden_medallion",)
    _canonical_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self._canonical_ids = tuple(item.lower() for item in self.sword_item_ids)

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if not (button and button.pressed):
            return
        if not self._is_sword_selected():
            return
        handler = getattr(self.attack_service, "handle_primary_attack", None)
        if callable(handler):
            handler()

    def _is_sword_selected(self) -> bool:
        inventory = self.inventory
        if inventory is None:
            return False
        slot = inventory.get_selected_slot()
        if slot is None:
            return False
        item_id = getattr(slot, "item_id", None)
        qty = getattr(slot, "qty", 0)
        if not item_id or qty <= 0:
            return False
        return item_id.lower() in self._canonical_ids
