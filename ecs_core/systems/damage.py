from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from ecs_core.components import Damage, Health, Drops
from ecs_core.systems.health import HealthSystem
from ecs_core.systems.movement_system import MovementSystem


@dataclass
class _ContactState:
    last_event: Optional[str] = None


class DamageSystem:
    """Apply damage when colliders overlap according to Damage component rules."""

    def __init__(self, world) -> None:
        self.world = world
        self.movement_system: Optional[MovementSystem] = None
        self.health_system: Optional[HealthSystem] = None
        self.time_service = None
        self._active_contacts: Dict[Tuple[int, int], _ContactState] = {}

    def update(self, dt: float) -> None:
        del dt  # damage resolution depends on collision events, not delta time
        if not self.movement_system or not self.health_system:
            self._active_contacts.clear()
            return

        events = getattr(self.movement_system, "collision_events", None)
        if not events:
            self._active_contacts.clear()
            return

        current_contacts: Set[Tuple[int, int]] = set()
        for event in events:
            self._evaluate_direction(event.a, event.b, current_contacts)
            self._evaluate_direction(event.b, event.a, current_contacts)

        self._prune_contacts(current_contacts)

    def _evaluate_direction(
        self, damager_id: int, target_id: int, active_keys: Set[Tuple[int, int]]
    ) -> None:
        damage = self.world.get(damager_id, Damage)
        if damage is None or damage.damage_rating <= 0:
            return

        health = self.world.get(target_id, Health)
        if health is None:
            return

        if damage.target_classes and not self._matches_entity_class(
            target_id, damage.target_classes
        ):
            return

        key = (damager_id, target_id)
        active_keys.add(key)

        if damage.apply_mode == "time_event":
            self._handle_time_event_damage(key, damage, target_id)
        else:
            self._handle_contact_damage(key, damage, target_id)

    def _handle_contact_damage(
        self, key: Tuple[int, int], damage: Damage, target_id: int
    ) -> None:
        if key in self._active_contacts:
            return
        self._apply_damage(target_id, damage.damage_rating)
        self._active_contacts[key] = _ContactState()

    def _handle_time_event_damage(
        self, key: Tuple[int, int], damage: Damage, target_id: int
    ) -> None:
        state = self._active_contacts.get(key)
        if state is None:
            state = _ContactState()
            self._active_contacts[key] = state

        current_event = getattr(self.time_service, "current_event", None)
        target_event = damage.time_event or "HEARTBEAT"
        if current_event is None or current_event != target_event:
            return
        if state.last_event == current_event:
            return

        self._apply_damage(target_id, damage.damage_rating)
        state.last_event = current_event

    def _apply_damage(self, target_id: int, amount: float) -> None:
        if not self.health_system:
            return
        died = self.health_system.take_damage(target_id, int(round(amount)))
        if died:
            # If entity has drops, let DropsSystem handle destruction
            if self.world.get(target_id, Drops):
                return
            self.world.destroy_entity(target_id)

    def _prune_contacts(self, current_keys: Set[Tuple[int, int]]) -> None:
        stale = [key for key in self._active_contacts if key not in current_keys]
        for key in stale:
            del self._active_contacts[key]

    def _matches_entity_class(
        self, entity_id: int, classes: tuple[type, ...]
    ) -> bool:
        for cls in classes:
            if self.world.get(entity_id, cls):
                return True
        return False
