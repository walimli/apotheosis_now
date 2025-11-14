"""Convenience helpers for constructing pre-seeded inventories."""

from __future__ import annotations

from services.inventory.inventory import Inventory

DEFAULT_STARTER_ITEM = "pick_wooden_medallion"


def create_player_inventory() -> Inventory:
    """Return a new player inventory with default starter items."""
    inventory = Inventory()
    remainder = inventory.add(DEFAULT_STARTER_ITEM, 1)
    if remainder:
        raise RuntimeError(
            f"Failed to seed starter item '{DEFAULT_STARTER_ITEM}' (remainder {remainder})"
        )
    inventory.set_selected_index(0)
    return inventory


__all__ = ["create_player_inventory", "DEFAULT_STARTER_ITEM"]
