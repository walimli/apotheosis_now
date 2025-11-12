from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class InventoryCursor:
    """Tracks the stack currently carried by the player's cursor."""

    item_id: Optional[str] = None
    qty: int = 0

    def carrying(self) -> bool:
        return self.item_id is not None and self.qty > 0

    def start_drag(self, item_id: str, qty: int) -> None:
        qty = int(qty)
        if qty <= 0:
            self.clear()
            return
        self.item_id = item_id
        self.qty = qty

    def clear(self) -> None:
        self.item_id = None
        self.qty = 0

    def set(self, item_id: Optional[str], qty: int) -> None:
        if item_id is None or qty <= 0:
            self.clear()
        else:
            self.item_id = item_id
            self.qty = int(qty)

    def take(self, amount: int) -> Tuple[Optional[str], int]:
        if not self.carrying() or amount <= 0:
            return (None, 0)
        taken = min(self.qty, amount)
        item_id = self.item_id
        self.qty -= taken
        if self.qty <= 0:
            self.clear()
        return (item_id, taken)


__all__ = ["InventoryCursor"]
