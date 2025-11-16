from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggressivePathfindingComponent:
    """Enable aggressive pathfollowing and store desired movement direction."""

    active: bool = True
    dir_x: float = 0.0
    dir_y: float = 0.0


__all__ = ["AggressivePathfindingComponent"]
