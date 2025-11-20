from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

TileCoord = Tuple[int, int]


@dataclass(frozen=True)
class ProtectionZoneComponent:
    """Marks an entity as projecting a protection radius that blocks spawns."""

    radius_tiles: float
    enabled: bool = True
    anchor_offset: Tuple[float, float] = (0.0, 0.0)
    tile_override: Optional[TileCoord] = None


__all__ = ["ProtectionZoneComponent"]
