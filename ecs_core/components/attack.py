from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AttackComponent:
    """Defines attack template + cooldown handling for an entity."""

    attack_id: str = "wooden_sword_attack"
    attack_cooldown: float = 0.5
    cooldown_timer: float = 0.0
    spawn_offset: float = 16.0  # Extra distance beyond collider radius
    offset_x: float = 0.0  # Fine-tuning offset along X after facing application
    offset_y: float = 0.0  # Fine-tuning offset along Y after facing application
