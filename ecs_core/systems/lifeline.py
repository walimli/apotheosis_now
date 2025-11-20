from __future__ import annotations

from ecs_core.components import Lifeline


class LifelineSystem:
    def __init__(self) -> None:
        self.world = None

    def update(self, dt: float) -> None:
        if not self.world or dt <= 0:
            return

        for entity_id, lifeline in list(self.world.get_component(Lifeline)):
            lifeline.remaining -= dt
            if lifeline.remaining <= 0:
                self.world.destroy_entity(entity_id)
