from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple

from ecs_core.components import Position, Velocity
from ecs_core.components.attack import AttackComponent
from ecs_core.components.collider import Collider
from ecs_core.systems_base import System


class AttackSystem(System):
    """Instantiates attack entities for owners with AttackComponent definitions."""

    _FACING_TO_VECTOR = {
        "up": (0.0, -1.0),
        "down": (0.0, 1.0),
        "left": (-1.0, 0.0),
        "right": (1.0, 0.0),
    }

    def __init__(self, world):
        super().__init__(world)
        self._pending: Deque[Tuple[int, Optional[str]]] = deque()
        self.monster_factory = None

    def request_attack(self, entity_id: int, facing: Optional[str] = None) -> bool:
        """Queue an attack for the given entity if cooldown permits."""
        attack = self.world.get(entity_id, AttackComponent)
        if (
            attack is None
            or attack.cooldown_timer > 0.0
            or not attack.attack_id
            or self.monster_factory is None
        ):
            return False
        self._pending.append((entity_id, facing))
        return True

    def update(self, dt: float) -> None:
        """Tick cooldown timers and spawn pending attack entities."""
        for _entity, attack in self.world.view(AttackComponent):
            if attack.cooldown_timer > 0.0:
                attack.cooldown_timer = max(0.0, attack.cooldown_timer - dt)

        if not self._pending or self.monster_factory is None:
            self._pending.clear()
            return

        pending = list(self._pending)
        self._pending.clear()
        for entity_id, facing in pending:
            self._process_attack(entity_id, facing)

    def _process_attack(self, entity_id: int, facing: Optional[str]) -> None:
        attack = self.world.get(entity_id, AttackComponent)
        if (
            attack is None
            or attack.cooldown_timer > 0.0
            or not attack.attack_id
            or self.monster_factory is None
        ):
            return
        spawn_position = self._compute_spawn_position(entity_id, facing, attack)
        if spawn_position is None:
            return
        try:
            self.monster_factory.spawn_attack_entity(attack.attack_id, spawn_position)
        except Exception:
            return
        attack.cooldown_timer = max(attack.attack_cooldown, 0.0)

    def _compute_spawn_position(
        self,
        entity_id: int,
        facing: Optional[str],
        attack: AttackComponent,
    ) -> Optional[Tuple[float, float]]:
        position = self.world.get(entity_id, Position)
        if position is None:
            return None

        base_x = (
            position.render_x if position.render_x is not None else float(position.x)
        )
        base_y = (
            position.render_y if position.render_y is not None else float(position.y)
        )

        dir_x, dir_y = self._direction_vector(entity_id, facing)
        collider = self.world.get(entity_id, Collider)
        collider_radius = float(collider.diameter) * 0.5 if collider else 0.0
        offset = collider_radius + max(0.0, float(attack.spawn_offset))

        spawn_x = base_x + dir_x * offset + float(getattr(attack, "offset_x", 0.0))
        spawn_y = base_y + dir_y * offset + float(getattr(attack, "offset_y", 0.0))
        return (spawn_x, spawn_y)

    def _direction_vector(
        self, entity_id: int, facing: Optional[str]
    ) -> Tuple[float, float]:
        if facing:
            vector = self._FACING_TO_VECTOR.get(facing.lower())
            if vector:
                return vector

        velocity = self.world.get(entity_id, Velocity)
        if velocity:
            vx, vy = float(velocity.vx), float(velocity.vy)
            if abs(vx) > abs(vy) and abs(vx) > 1e-6:
                return (1.0, 0.0) if vx > 0 else (-1.0, 0.0)
            if abs(vy) > 1e-6:
                return (0.0, 1.0) if vy > 0 else (0.0, -1.0)

        return self._FACING_TO_VECTOR["down"]
