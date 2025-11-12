from __future__ import annotations

from typing import Optional

from .inventory import Inventory, Slot
from .cursor import InventoryCursor
from .items import get_item


def _get_slot(inventory: Inventory, slot_index: int) -> Optional[Slot]:
    if slot_index < 0 or slot_index >= len(inventory.slots):
        return None
    return inventory.slots[slot_index]


def handle_left_click(inventory: Inventory, cursor: InventoryCursor, slot_index: int) -> bool:
    """Handle primary-button interaction with a hotbar slot."""
    slot = _get_slot(inventory, slot_index)
    if slot is None:
        return False

    changed = False

    if cursor.carrying():
        if slot.is_empty():
            slot.item_id = cursor.item_id
            slot.qty = cursor.qty
            cursor.clear()
            changed = True
        elif slot.item_id == cursor.item_id:
            stack_max = get_item(slot.item_id).stack_max
            can_add = min(stack_max - slot.qty, cursor.qty)
            if can_add > 0:
                slot.qty += can_add
                cursor.qty -= can_add
                if cursor.qty <= 0:
                    cursor.clear()
                changed = True
        else:
            slot.item_id, cursor.item_id = cursor.item_id, slot.item_id
            slot.qty, cursor.qty = cursor.qty, slot.qty
            if cursor.qty <= 0:
                cursor.clear()
            changed = True
    else:
        if not slot.is_empty():
            cursor.start_drag(slot.item_id, slot.qty)
            slot.clear()
            changed = True

    if changed:
        inventory._emit_change()
    return changed


def handle_right_click(inventory: Inventory, cursor: InventoryCursor, slot_index: int) -> bool:
    """Handle alternate-button interaction with a hotbar slot (single-item pickup)."""
    slot = _get_slot(inventory, slot_index)
    if slot is None:
        return False

    changed = False

    if slot.is_empty():
        if not cursor.carrying():
            return False
        slot.item_id = cursor.item_id
        slot.qty = 1
        cursor.qty -= 1
        if cursor.qty <= 0:
            cursor.clear()
        changed = True
    else:
        item_id = slot.item_id
        stack_max = get_item(item_id).stack_max
        if cursor.carrying() and cursor.item_id != item_id:
            return False
        if cursor.carrying() and cursor.qty >= stack_max:
            return False
        slot.qty -= 1
        if slot.qty <= 0:
            slot.clear()
        if cursor.carrying():
            cursor.qty += 1
        else:
            cursor.start_drag(item_id, 1)
        changed = True

    if changed:
        inventory._emit_change()
    return changed


__all__ = ["handle_left_click", "handle_right_click"]
