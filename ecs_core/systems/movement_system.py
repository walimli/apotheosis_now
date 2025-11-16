"""Movement + collision integration system."""

from __future__ import annotations

import math
from typing import Dict, Iterable, Optional, Set

from ecs_core.components import Collider, Position, Velocity
from ecs_core.systems.collision.collision import CollisionEvent, CollisionSystem
from ecs_core.systems_base import System


class MovementSystem(System):
    """Advance entity positions while syncing them with the collision system."""

    def __init__(
        self,
        world,
        *,
        world_size: tuple[int, int] = (4096, 4096),
        cell_size: int = 128,
    ) -> None:
        super().__init__(world)
        self.collision = CollisionSystem(world_size=world_size, cell_size=cell_size)
        self.collision_events: list[CollisionEvent] = []
        self._active_entities: Set[int] = set()

    # Optional hooks in case external systems want to limit the active set explicitly
    def register_entities(self, entity_ids: Iterable[int]) -> None:
        for entity_id in entity_ids:
            if entity_id in self._active_entities:
                continue
            position = self.world.get(entity_id, Position)
            collider = self.world.get(entity_id, Collider)
            if position and collider:
                velocity = self.world.get(entity_id, Velocity)
                self.collision.register(
                    entity_id,
                    collider,
                    (
                        self._quantize(position.x, velocity.vx if velocity else None),
                        self._quantize(position.y, velocity.vy if velocity else None),
                    ),
                )
                self._active_entities.add(entity_id)

    def unregister_entities(self, entity_ids: Iterable[int]) -> None:
        for entity_id in entity_ids:
            if entity_id not in self._active_entities:
                continue
            self.collision.unregister(entity_id)
            self._active_entities.discard(entity_id)

    def update(self, dt: float) -> None:
        if dt is None or dt <= 0:
            return
        self._sync_colliders()
        if not self._active_entities:
            self.collision_events = []
            return

        proposed_positions: Dict[int, tuple[float, float, float, float]] = {}
        for entity_id in self._active_entities:
            position = self.world.get(entity_id, Position)
            if position is None:
                continue
            base_x = position.render_x if position.render_x is not None else float(position.x)
            base_y = position.render_y if position.render_y is not None else float(position.y)
            velocity = self.world.get(entity_id, Velocity)
            if velocity:
                new_x = base_x + velocity.vx * dt
                new_y = base_y + velocity.vy * dt
            else:
                new_x, new_y = base_x, base_y
            position.render_x = new_x
            position.render_y = new_y
            proposed_positions[entity_id] = (new_x, new_y, base_x, base_y)

        if not proposed_positions:
            self.collision_events = []
            return

        grid_positions = {}
        quantized_lookup: Dict[int, tuple[int, int]] = {}
        for entity_id, proposed in proposed_positions.items():
            velocity = self.world.get(entity_id, Velocity)
            delta_x = velocity.vx * dt if velocity else proposed[0] - proposed[2]
            delta_y = velocity.vy * dt if velocity else proposed[1] - proposed[3]
            qx = self._quantize(proposed[0], delta_x)
            qy = self._quantize(proposed[1], delta_y)
            grid_positions[entity_id] = (qx, qy)
            quantized_lookup[entity_id] = (qx, qy)
        self.collision.update_positions(grid_positions)
        self.collision_events = self.collision.update()

        for entity_id in self._active_entities:
            resolved = self.collision.entity_pos.get(entity_id)
            if resolved is None:
                continue
            position = self.world.get(entity_id, Position)
            if position:
                position.x = int(resolved[0])
                position.y = int(resolved[1])
                quantized = quantized_lookup.get(entity_id)
                if (
                    quantized is None
                    or resolved[0] != quantized[0]
                    or resolved[1] != quantized[1]
                ):
                    position.render_x = float(resolved[0])
                    position.render_y = float(resolved[1])

    def _sync_colliders(self) -> None:
        """Automatically track entities with both Position and Collider components."""
        seen: Set[int] = set()
        for entity_id, position, collider in self.world.view(Position, Collider):
            seen.add(entity_id)
            if entity_id in self._active_entities:
                continue
            velocity = self.world.get(entity_id, Velocity)
            self.collision.register(
                entity_id,
                collider,
                (
                    self._quantize(position.x, velocity.vx if velocity else None),
                    self._quantize(position.y, velocity.vy if velocity else None),
                ),
            )
            self._active_entities.add(entity_id)

        removed = list(self._active_entities - seen)
        if removed:
            self.unregister_entities(removed)

    @staticmethod
    def _quantize(value: float, delta: Optional[float] = None) -> int:
        """Round toward the motion direction (ceil for +, floor for -) to avoid bias."""
        if delta is None or abs(delta) < 1e-9:
            return int(round(value))
        return math.ceil(value) if delta > 0 else math.floor(value)


__all__ = ["MovementSystem"]
