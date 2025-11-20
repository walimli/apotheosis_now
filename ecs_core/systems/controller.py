from typing import Dict, Callable, Tuple
import math
from ecs_core.components import Controller, Speed, Velocity


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

    def unregister_entity(self, eid: int) -> None:
        self.entity_to_handler.pop(eid, None)

    def update(self, dt: float):
        # Only call pre-registered handlers — O(1) per entity, no type checks
        if not self.world:
            return
        self._sync_controllers()
        for eid, handler in list(self.entity_to_handler.items()):
            if self.world.has_entity(eid):  # Still alive
                handler(eid, dt)

    def _player_input_handler(self, eid: int, dt: float):
        """Handle player input to update entity velocity."""
        if not self.input_service:
            return

        # Get current movement input from input service
        # Following the pattern: input vector in range [-1, 1] for each axis
        movement_input = self.input_service.get_movement_input()
        dx, dy = movement_input

        # Get entity's Speed component for movement speed
        speed = self.world.get_component(eid, Speed)
        if not speed:
            return

        # Normalize movement so diagonals aren't faster
        magnitude = math.hypot(dx, dy)
        if magnitude > 1.0:
            dx /= magnitude
            dy /= magnitude

        # Calculate final velocity based on speed and normalized input
        velocity_x = dx * speed.pixels_per_second
        velocity_y = dy * speed.pixels_per_second

        # Update entity's Velocity component
        velocity = self.world.get_component(eid, Velocity)
        if velocity:
            velocity.vx = velocity_x
            velocity.vy = velocity_y
        else:
            # Create new Velocity component if it doesn't exist
            self.world.add(eid, Velocity(vx=velocity_x, vy=velocity_y))

    def _sync_controllers(self) -> None:
        if not self.world:
            return
        seen = set()
        for entity_id, controller in self.world.view(Controller):
            seen.add(entity_id)
            if entity_id not in self.entity_to_handler:
                self.register_entity(entity_id, controller)
        for entity_id in list(self.entity_to_handler.keys()):
            if entity_id not in seen:
                self.unregister_entity(entity_id)
