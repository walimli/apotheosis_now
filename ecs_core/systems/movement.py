"""Movement system that integrates Position using Velocity components."""

from __future__ import annotations

from ecs_core.components import Position, Velocity
from ecs_core.systems_base import System


class MovementSystem(System):
    """Advance entity positions based on their velocity vectors."""

    def update(self, dt: float) -> None:
        if dt is None or dt <= 0:
            return
        for _entity, position, velocity in self.world.view(Position, Velocity):
            position.x += velocity.vx * dt
            position.y += velocity.vy * dt


__all__ = ["MovementSystem"]
