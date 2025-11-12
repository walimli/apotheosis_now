# systems/controller.py
from typing import Dict, Callable
from components.components import Controller


class ControllerSystem:
    def __init__(self):
        self.world = None
        self.input_service = None
        self.ai_service = None
        self.entity_to_handler: Dict[int, Callable[[int, float], None]] = {}  # eid → callable(eid, dt)

    def register_entity(self, eid: int, controller: Controller):
        """Called once when entity is created with Controller component."""
        if controller.type == "player_input":
            self.entity_to_handler[eid] = self._player_input_handler
        elif controller.type == "mob_aggressive":
            self.entity_to_handler[eid] = (
                lambda eid, dt: self.ai_service.update_aggressive(eid, dt)
            )
        elif controller.type == "mob_passive":
            self.entity_to_handler[eid] = (
                lambda eid, dt: self.ai_service.update_passive(eid, dt)
            )
        elif controller.type == "npc":
            self.entity_to_handler[eid] = lambda eid, dt: self.ai_service.update_npc(
                eid, dt
            )

    def update(self, dt: float):
        # Only call pre-registered handlers — O(1) per entity, no type checks
        for eid, handler in self.entity_to_handler.items():
            if eid in self.world.components:  # Still alive
                handler(eid, dt)

    def _player_input_handler(self, eid: int, dt: float):
        # Same as before: read input, move, animate
        pass
