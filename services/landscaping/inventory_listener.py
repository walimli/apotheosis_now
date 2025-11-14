from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


SelectionCallback = Callable[["LandscapingSelectionState"], None]


@dataclass(frozen=True)
class LandscapingSelectionState:
    """Snapshot of the equipped slot relevant to landscaping."""

    slot_index: int
    item_id: Optional[str]
    qty: int
    harvest_enabled: bool
    placement_tile_code: Optional[int]


class LandscapingInventoryListener:
    """Watches the inventory hotbar selection for landscaping tools."""

    def __init__(
        self,
        inventory,
        *,
        harvest_item_id: str,
        placement_items: Dict[str, int],
    ) -> None:
        self._inventory = inventory
        self._harvest_item_id = harvest_item_id
        self._placement_items = dict(placement_items)
        self._callbacks: List[SelectionCallback] = []
        self._state = self._compute_state()
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        self._inventory.add_selection_listener(self._handle_selection_change)
        # Emit current state immediately so subscribers are in sync.
        self._notify_listeners(self._state)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        self._inventory.remove_selection_listener(self._handle_selection_change)
        self._attached = False

    def subscribe(self, callback: SelectionCallback) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            callback(self._state)

    def unsubscribe(self, callback: SelectionCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @property
    def state(self) -> LandscapingSelectionState:
        return self._state

    def _handle_selection_change(
        self, slot_index: int, item_id: Optional[str], qty: int
    ) -> None:
        state = self._compute_state(slot_index, item_id, qty)
        if state == self._state:
            return
        self._state = state
        self._notify_listeners(state)

    def _compute_state(
        self,
        slot_index: Optional[int] = None,
        item_id: Optional[str] = None,
        qty: Optional[int] = None,
    ) -> LandscapingSelectionState:
        if slot_index is None or item_id is None or qty is None:
            slot_index = self._inventory.get_selected_index()
            slot = self._inventory.get_selected_slot()
            item_id = slot.item_id
            qty = slot.qty
        qty = max(0, int(qty or 0))
        harvest_enabled = item_id == self._harvest_item_id and qty > 0
        placement_tile_code = None
        if not harvest_enabled and qty > 0 and item_id is not None:
            placement_tile_code = self._placement_items.get(item_id)
        return LandscapingSelectionState(
            slot_index=slot_index,
            item_id=item_id,
            qty=qty,
            harvest_enabled=harvest_enabled,
            placement_tile_code=placement_tile_code,
        )

    def _notify_listeners(self, state: LandscapingSelectionState) -> None:
        for callback in list(self._callbacks):
            try:
                callback(state)
            except Exception:
                continue


__all__ = ["LandscapingInventoryListener", "LandscapingSelectionState"]
