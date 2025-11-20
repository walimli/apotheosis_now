from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerAttackService:
    """Bridges input events to the AttackSystem for the player entity."""

    attack_system: object
    animation_service: object
    player_entity: int

    def handle_primary_attack(self) -> bool:
        """Trigger a basic sword swing if cooldown allows."""
        if self.attack_system is None:
            return False
        direction = self._facing_direction()
        request = getattr(self.attack_system, "request_attack", None)
        if not callable(request):
            return False
        if not request(self.player_entity, direction):
            return False
        swing = getattr(self.animation_service, "play_sword_swing", None)
        if callable(swing):
            swing()
        return True

    def _facing_direction(self) -> str:
        getter = getattr(self.animation_service, "get_facing_direction", None)
        if callable(getter):
            return getter()
        return "down"
