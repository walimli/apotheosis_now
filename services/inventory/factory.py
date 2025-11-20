"""Convenience helpers for constructing pre-seeded inventories."""

from __future__ import annotations

from services.inventory.inventory import Inventory

DEFAULT_STARTER_ITEMS = [
    ("pick_wooden_medallion", 1),
    ("sword_wooden_medallion", 1),
]


def create_player_inventory() -> Inventory:
    """Return a new player inventory with default starter items."""
    inventory = Inventory()
    for slot_index, (item_id, qty) in enumerate(DEFAULT_STARTER_ITEMS):
        remainder = inventory.add(item_id, qty, prefer_slot=slot_index)
        if remainder:
            raise RuntimeError(
                f"Failed to seed starter item '{item_id}' (remainder {remainder})"
            )
    inventory.set_selected_index(0)
    return inventory


__all__ = ["create_player_inventory", "DEFAULT_STARTER_ITEMS"]
