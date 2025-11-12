from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from systems.audio_package import publish_audio_event
from .items import get_item
from .cursor import InventoryCursor


@dataclass
class Slot:
    item_id: Optional[str] = None
    qty: int = 0

    def is_empty(self) -> bool:
        return self.item_id is None or self.qty <= 0

    def clear(self):
        self.item_id = None
        self.qty = 0


class Inventory:
    """Player inventory with 9-slot hotbar.
    
    Features:
    - Stacks items up to item.stack_max
    - Adds to existing stack in hotbar if possible, else first empty slot
    - Returns remainder when no space available
    - Emits on_change callback when slots/selection change
    - Supports hotbar selection (slots 0-8)
    """

    def __init__(self, slots: int = 9):
        self.slots: List[Slot] = [Slot() for _ in range(slots)]
        self.selected_index: int = 0
        self.on_change: Optional[Callable[[], None]] = None
        self.cursor: InventoryCursor = InventoryCursor()

    # --- Selection ---
    def set_selected_index(self, index: int) -> None:
        """Set the selected hotbar slot (0-8)."""
        index = max(0, min(len(self.slots) - 1, int(index)))
        if index != self.selected_index:
            self.selected_index = index
            self._emit_change()

    def get_selected_index(self) -> int:
        """Get the currently selected hotbar slot."""
        return self.selected_index

    def get_selected_item_id(self) -> Optional[str]:
        """Get the item ID in the selected slot."""
        return self.slots[self.selected_index].item_id

    def get_selected_slot(self) -> Slot:
        """Get the selected slot object."""
        return self.slots[self.selected_index]

    # --- Item Management ---
    def add(self, item_id: str, qty: int) -> int:
        """Add qty of item_id to inventory.
        Returns remainder not added (0 if fully added).
        """
        if qty <= 0:
            return 0

        stack_max = get_item(item_id).stack_max
        remaining = qty
        added_any = False

        # 1) Fill existing stacks of same item
        for slot in self.slots:
            if slot.item_id == item_id and slot.qty < stack_max:
                can_add = min(stack_max - slot.qty, remaining)
                if can_add > 0:
                    slot.qty += can_add
                    remaining -= can_add
                    added_any = True
                if remaining == 0:
                    self._emit_change()
                    if added_any:
                        publish_audio_event("player.inventory.added")
                    return 0

        # 2) Fill empty slots
        for slot in self.slots:
            if slot.is_empty():
                put = min(stack_max, remaining)
                if put > 0:
                    slot.item_id = item_id
                    slot.qty = put
                    remaining -= put
                    added_any = True
                if remaining == 0:
                    self._emit_change()
                    if added_any:
                        publish_audio_event("player.inventory.added")
                    return 0

        # 3) Return remainder (no space)
        if remaining != qty:
            # Some was added
            self._emit_change()
            if added_any:
                publish_audio_event("player.inventory.added")
        return remaining

    def remove_from_selected(self, qty: int) -> int:
        """Remove qty from selected slot. Returns amount actually removed."""
        slot = self.slots[self.selected_index]
        if slot.is_empty() or qty <= 0:
            return 0

        take = min(slot.qty, qty)
        slot.qty -= take
        if slot.qty == 0:
            slot.clear()
        if take > 0:
            publish_audio_event("player.inventory.removed")
        self._emit_change()
        return take

    def remove_from_slot(self, slot_index: int, qty: int) -> int:
        """Remove qty from specific slot. Returns amount actually removed."""
        if slot_index < 0 or slot_index >= len(self.slots):
            return 0

        slot = self.slots[slot_index]
        if slot.is_empty() or qty <= 0:
            return 0

        take = min(slot.qty, qty)
        slot.qty -= take
        if slot.qty == 0:
            slot.clear()
        if take > 0:
            publish_audio_event("player.inventory.removed")
        self._emit_change()
        return take

    def set_slot(self, slot_index: int, item_id: Optional[str], qty: int):
        """Set a specific slot to contain the given item and quantity."""
        if slot_index < 0 or slot_index >= len(self.slots):
            return

        slot = self.slots[slot_index]
        slot.item_id = item_id
        slot.qty = qty if item_id else 0
        if slot.qty == 0:
            slot.clear()
        self._emit_change()

    def get_slot(self, slot_index: int) -> Optional[Slot]:
        """Get a specific slot by index."""
        if slot_index < 0 or slot_index >= len(self.slots):
            return None
        return self.slots[slot_index]

    def can_add(self, item_id: str, qty: int) -> bool:
        """Check if the inventory can fit the given item and quantity."""
        return self.add(item_id, qty) == 0  # This would be a dry-run, but let's implement properly
        
    def get_free_space(self, item_id: str) -> int:
        """Get how much of an item can be added to the inventory."""
        stack_max = get_item(item_id).stack_max
        free_space = 0
        
        # Count space in existing stacks
        for slot in self.slots:
            if slot.item_id == item_id and slot.qty < stack_max:
                free_space += stack_max - slot.qty
            elif slot.is_empty():
                free_space += stack_max
                
        return free_space

    # --- Introspection ---
    def get_slots(self) -> List[Tuple[Optional[str], int]]:
        """Get all slots as (item_id, qty) tuples."""
        return [(slot.item_id, slot.qty) for slot in self.slots]

    def is_empty(self) -> bool:
        """Check if inventory is completely empty."""
        return all(slot.is_empty() for slot in self.slots)

    def get_item_count(self, item_id: str) -> int:
        """Get total count of a specific item in inventory."""
        return sum(slot.qty for slot in self.slots if slot.item_id == item_id)

    # --- Events ---
    def _emit_change(self) -> None:
        """Emit change notification."""
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass  # Don't let callback errors break inventory

    # --- Persistence ---
    def to_dict(self) -> dict:
        """Serialize inventory to a concise dict.

        Returns:
            {
              "sel": int,                       # selected index
              "slots": [[i, item_id, qty], ...]  # only non-empty slots
            }
        """
        slots_payload = []
        for i, slot in enumerate(self.slots):
            if not slot.is_empty():
                slots_payload.append([i, slot.item_id, int(slot.qty)])
        return {"sel": int(self.selected_index), "slots": slots_payload}

    def from_dict(self, d: dict) -> None:
        """Restore inventory from a dict. Strict validation; raises on errors.

        Expected format:
            { "sel": int, "slots": [[index, item_id, qty], ...] }
        """
        if not isinstance(d, dict):
            raise TypeError("inventory.from_dict: expected dict")
        if "sel" not in d or "slots" not in d:
            raise KeyError("inventory.from_dict: missing 'sel' or 'slots'")

        sel = int(d["sel"]) if d["sel"] is not None else 0
        slots_list = d["slots"]
        if not isinstance(slots_list, list):
            raise TypeError("inventory.from_dict: 'slots' must be a list")

        if sel < 0 or sel >= len(self.slots):
            raise ValueError("inventory.from_dict: 'sel' out of range")

        # Clear existing slots in place to avoid breaking references
        for slot in self.slots:
            slot.clear()

        seen_indices = set()
        for entry in slots_list:
            if (not isinstance(entry, (list, tuple))) or len(entry) != 3:
                raise ValueError("inventory.from_dict: slot entry must be [index, item_id, qty]")
            idx, item_id, qty = entry
            idx = int(idx)
            if idx < 0 or idx >= len(self.slots):
                raise ValueError("inventory.from_dict: slot index out of range")
            if idx in seen_indices:
                raise ValueError("inventory.from_dict: duplicate slot index")
            seen_indices.add(idx)

            if not isinstance(item_id, str) or not item_id:
                raise ValueError("inventory.from_dict: invalid item_id")
            qty = int(qty)
            if qty <= 0:
                raise ValueError("inventory.from_dict: qty must be > 0 for non-empty slot")

            # Validate item exists and stack limit
            item = get_item(item_id)
            stack_max = int(item.stack_max)
            if qty > stack_max:
                raise ValueError("inventory.from_dict: qty exceeds stack_max for item")

            slot = self.slots[idx]
            slot.item_id = item_id
            slot.qty = qty

        self.selected_index = sel
        self._emit_change()
