from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class CollisionHandle:
    """Lightweight helper that keeps a mover registered with the collision manager."""

    width: float
    height: float
    offset_x: float
    offset_y: float
    _world: Optional[object] = None
    _collision: Optional[object] = None
    _mover_id: Optional[int] = None

    def ensure_attached(self, world) -> None:
        if world is None:
            raise ValueError("CollisionHandle.ensure_attached requires a world instance")

        if self._world is world and self._collision is not None:
            return

        collision = getattr(world, "collision", None)
        if collision is None:
            raise AttributeError("World instance does not expose a collision manager")

        if self._collision is not None and self._mover_id is not None:
            self._collision.unregister_mover(self._mover_id)

        mover = collision.register_mover(
            width=self.width,
            height=self.height,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
        )
        self._world = world
        self._collision = collision
        self._mover_id = mover.mover_id

    def update_from_entity_position(self, entity_x: float, entity_y: float) -> None:
        if self._collision is None or self._mover_id is None:
            return
        top_left_x = entity_x + self.offset_x
        top_left_y = entity_y + self.offset_y
        self._collision.update_mover_bounds(self._mover_id, top_left_x, top_left_y)

    def resolve_move(
        self,
        *,
        entity_x: float,
        entity_y: float,
        delta_x: float,
        delta_y: float,
    ) -> Tuple[float, float]:
        if self._collision is None or self._mover_id is None:
            raise RuntimeError("CollisionHandle must be attached before resolving movement")

        start_x = entity_x + self.offset_x
        start_y = entity_y + self.offset_y
        new_top_left_x, new_top_left_y = self._collision.resolve_move(
            x=start_x,
            y=start_y,
            width=self.width,
            height=self.height,
            delta_x=delta_x,
            delta_y=delta_y,
            mover_id=self._mover_id,
        )
        # Convert back to entity origin by removing offset.
        new_entity_x = new_top_left_x - self.offset_x
        new_entity_y = new_top_left_y - self.offset_y
        return (new_entity_x, new_entity_y)

    def detach(self) -> None:
        if self._collision is not None and self._mover_id is not None:
            self._collision.unregister_mover(self._mover_id)
        self._world = None
        self._collision = None
        self._mover_id = None
