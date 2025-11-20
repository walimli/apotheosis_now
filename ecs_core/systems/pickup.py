"""System for handling collectible entities when the player overlaps them."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ecs_core.components import PickupComponent
from ecs_core.systems.movement_system import MovementSystem
from ecs_core.systems_base import System

if TYPE_CHECKING:
    from services.inventory import Inventory
else:  # pragma: no cover
    Inventory = object


class PickupSystem(System):
    """Consumes collision events to grant pickups to the player inventory."""

    def __init__(self, world) -> None:
        super().__init__(world)
        self.movement_system: Optional[MovementSystem] = None
        self.inventory: Optional[Inventory] = None
        self.player_entity: Optional[int] = None

    def bind_player(self, player_entity: int, inventory: Inventory) -> None:
        """Bind the player entity and inventory used for pickups."""
        self.player_entity = player_entity
        self.inventory = inventory

    def update(self, dt: float) -> None:
        del dt
        if not self.movement_system or self.player_entity is None or self.inventory is None:
            return

        events = getattr(self.movement_system, "collision_events", None) or []
        if not events:
            return

        for event in events:
            self._try_collect(event.a, event.b)
            self._try_collect(event.b, event.a)

    def _try_collect(self, primary: int, other: int) -> None:
        if primary != self.player_entity:
            return
        if not self.world.has_entity(other):
            return
        pickup = self.world.get(other, PickupComponent)
        if pickup is None or pickup.quantity <= 0:
            return

        remainder = self.inventory.add(
            pickup.item_id,
            pickup.quantity,
            prefer_slot=pickup.prefer_slot,
        )
        collected = pickup.quantity - remainder
        if collected <= 0:
            return

        if remainder > 0:
            pickup.quantity = remainder
            return

        self.world.destroy_entity(other)


__all__ = ["PickupSystem"]
