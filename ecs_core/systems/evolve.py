from typing import Optional

from ecs_core.components import Evolve, Position
from ecs_core.entities.entities import EntityManager
from services.monster_factory.evolve_registry import (
    EvolvableEntityRegistry,
    evolvable_registry,
)
from ecs_core.worlds.world import World


class EvolveSystem:
    def __init__(
        self,
        registry: Optional[EvolvableEntityRegistry] = None,
    ) -> None:
        self.world: Optional[World] = None
        self.time_service = None  # Set externally
        self.entity_manager: Optional[EntityManager] = None
        self.registry = registry or evolvable_registry

    def update(self, dt: float):
        if not self.time_service or not self.world:
            return

        current_event = self.time_service.current_event  # e.g., TimeEventType.DAWN

        for eid, evolve in list(self.world.get_component(Evolve)):
            if evolve.time_event == current_event and evolve.next_entity_id:
                self._evolve_entity(eid, evolve.next_entity_id)

    def _evolve_entity(self, old_eid: int, next_entity_id: str) -> None:
        if not self.registry or not self.entity_manager or not self.world:
            return

        old_pos = self.world.get_component(old_eid, Position)
        if old_pos:
            pos_data = (
                float(old_pos.x),
                float(old_pos.y),
                float(old_pos.render_x if old_pos.render_x is not None else old_pos.x),
                float(old_pos.render_y if old_pos.render_y is not None else old_pos.y),
            )
        else:
            pos_data = (0.0, 0.0, 0.0, 0.0)

        self.world.destroy_entity(old_eid)

        try:
            new_entity = self.registry.spawn(next_entity_id, self.world, self.entity_manager)
        except KeyError:
            return

        new_pos = self.world.get(new_entity, Position)
        if not new_pos:
            return
        new_pos.x = pos_data[0]
        new_pos.y = pos_data[1]
        new_pos.render_x = pos_data[2]
        new_pos.render_y = pos_data[3]
