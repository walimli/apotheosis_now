from __future__ import annotations

from typing import Tuple

from ecs_core.components.aggressive_components import AggressivePathfindingComponent
from ecs_core.components import Speed, Velocity
from ecs_core.worlds.world import World

from .pathfinding import AggressivePathfindingManager


class AggressiveAIService:
    """Minimal AI service hooking controller callbacks to the path manager."""

    def __init__(self, world: World, manager: AggressivePathfindingManager) -> None:
        self.world = world
        self.manager = manager

    def update_aggressive(self, entity_id: int, dt: float) -> None:
        component = self.world.get(entity_id, AggressivePathfindingComponent)
        if component is None:
            component = AggressivePathfindingComponent()
            self.world.add(entity_id, component)
        self.manager.register_entity(entity_id)
        self._apply_direction(entity_id, component)

    def update_passive(self, entity_id: int, dt: float) -> None:  # pragma: no cover
        return

    def update_npc(self, entity_id: int, dt: float) -> None:  # pragma: no cover
        return

    def _apply_direction(
        self, entity_id: int, component: AggressivePathfindingComponent
    ) -> None:
        direction = (component.dir_x, component.dir_y)
        speed = self.world.get(entity_id, Speed)
        if speed is None:
            return
        vx, vy = self._normalize(direction)
        velocity = self.world.get(entity_id, Velocity)
        if velocity is None:
            velocity = Velocity(vx=0.0, vy=0.0)
            self.world.add(entity_id, velocity)
        velocity.vx = vx * speed.pixels_per_second
        velocity.vy = vy * speed.pixels_per_second

    @staticmethod
    def _normalize(vector):
        dx, dy = vector
        length = (dx * dx + dy * dy) ** 0.5
        if length <= 1e-6:
            return 0.0, 0.0
        return dx / length, dy / length


def setup_aggressive_pathfinding(
    play_state,
) -> Tuple[AggressivePathfindingManager, AggressiveAIService]:
    manager = AggressivePathfindingManager(play_state)
    service = AggressiveAIService(play_state.ecs_world, manager)
    return manager, service


__all__ = ["AggressiveAIService", "setup_aggressive_pathfinding"]
