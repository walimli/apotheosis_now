from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

TileCoord = Tuple[int, int]


@dataclass(frozen=True)
class ProtectionZone:
    tile: TileCoord
    radius: float

    def contains(self, tile: TileCoord) -> bool:
        dx = abs(self.tile[0] - tile[0])
        dy = abs(self.tile[1] - tile[1])
        return max(dx, dy) <= self.radius

    def to_dict(self) -> dict:
        return {"tile": self.tile, "radius": self.radius}


class ProtectionRegistry:
    """Track placeable-based protection zones (e.g., anti-spawn areas)."""

    def __init__(self) -> None:
        self._zones: Dict[TileCoord, ProtectionZone] = {}

    def add_zone(self, tile: TileCoord, radius: float) -> ProtectionZone:
        zone = ProtectionZone(tile=tile, radius=float(radius))
        self._zones[tile] = zone
        return zone

    def remove_zone(self, tile: TileCoord) -> None:
        self._zones.pop(tile, None)

    def get_zone(self, tile: TileCoord) -> Optional[ProtectionZone]:
        return self._zones.get(tile)

    def zones(self) -> List[ProtectionZone]:
        return list(self._zones.values())

    def is_tile_protected(self, tile: TileCoord) -> bool:
        return any(zone.contains(tile) for zone in self._zones.values())

    def clear(self) -> None:
        self._zones.clear()

    def load_zones(self, zones: Iterable[Tuple[TileCoord, float]]) -> None:
        self.clear()
        for tile, radius in zones:
            self.add_zone(tile, radius)


__all__ = ["ProtectionRegistry", "ProtectionZone"]
