"""Inventory selection listener for placement service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

from services.inventory.inventory import Inventory

from .blueprints import PlacementBlueprint
from .pills import PillRegistry


@dataclass(frozen=True)
class PlacementSelectionState:
    slot_index: int
    item_id: Optional[str]
    qty: int
    blueprint: Optional[PlacementBlueprint]
    is_pill: bool
    handled_by_fence: bool


SelectionCallback = Callable[[PlacementSelectionState], None]


class PlacementInventoryListener:
    """Observe inventory selection changes and emit placement states."""

    def __init__(
        self,
        inventory: Inventory,
        *,
        blueprints: Dict[str, PlacementBlueprint],
        pill_registry: PillRegistry,
        fence_items: Optional[Set[str]] = None,
    ) -> None:
        self._inventory = inventory
        self._blueprints = blueprints
        self._pill_registry = pill_registry
        self._fence_items = set(fence_items or set())
        self._callbacks: List[SelectionCallback] = []
        self._state = self._compute_state()
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        self._inventory.add_selection_listener(self._handle_selection_change)
        self._notify(self._state)
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
    def state(self) -> PlacementSelectionState:
        return self._state

    def _handle_selection_change(
        self,
        slot_index: int,
        item_id: Optional[str],
        qty: int,
    ) -> None:
        state = self._compute_state(slot_index, item_id, qty)
        if state == self._state:
            return
        self._state = state
        self._notify(state)

    def _compute_state(
        self,
        slot_index: Optional[int] = None,
        item_id: Optional[str] = None,
        qty: Optional[int] = None,
    ) -> PlacementSelectionState:
        if slot_index is None or item_id is None or qty is None:
            slot_index = self._inventory.get_selected_index()
            slot = self._inventory.get_selected_slot()
            item_id = slot.item_id
            qty = slot.qty
        qty = max(0, int(qty or 0))
        normalized_id = item_id if qty > 0 else None
        blueprint = None
        if normalized_id is not None:
            blueprint = self._blueprints.get(normalized_id)
        is_pill = bool(normalized_id and self._pill_registry.is_pill(normalized_id))
        handled_by_fence = bool(normalized_id in self._fence_items)
        return PlacementSelectionState(
            slot_index=slot_index,
            item_id=normalized_id,
            qty=qty,
            blueprint=blueprint,
            is_pill=is_pill,
            handled_by_fence=handled_by_fence,
        )

    def _notify(self, state: PlacementSelectionState) -> None:
        for callback in list(self._callbacks):
            try:
                callback(state)
            except Exception:
                continue


__all__ = ["PlacementInventoryListener", "PlacementSelectionState"]
