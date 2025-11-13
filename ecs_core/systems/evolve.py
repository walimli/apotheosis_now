from ecs_core.components.components import Evolve, Position
from ecs_core.worlds.world import World


class EvolveSystem:
    def __init__(self):
        self.world = None
        self.time_service = None  # Set externally

    def update(self, dt: float):
        if not self.time_service:
            return

        current_event = self.time_service.current_event  # e.g., TimeEventType.DAWN

        for eid, evolve in list(self.world.get_component(Evolve)):
            if evolve.time_event == current_event and evolve.stage:
                self._evolve_entity(eid, evolve.stage)

    def _evolve_entity(self, old_eid: int, new_eid_template: int):
        # Preserve position
        old_pos = self.world.get_component(old_eid, Position)
        pos_data = (old_pos.x, old_pos.y) if old_pos else (0, 0)

        # Destroy old entity
        self.world.destroy_entity(old_eid)

        # Create new entity from template
        new_entity = self.world.create_entity_from_template(new_eid_template)

        # Apply preserved position
        new_pos = self.world.get(new_entity, Position)
        if not new_pos:
            return
        new_pos.x, new_pos.y = pos_data
