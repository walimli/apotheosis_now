from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

TileCoord = Tuple[int, int]


@dataclass(frozen=True)
class SafeZone:
    """Descriptor for a tile-based safe zone."""

    tile: TileCoord
    radius: float

    def contains(self, tile: TileCoord) -> bool:
        dx = abs(self.tile[0] - tile[0])
        dy = abs(self.tile[1] - tile[1])
        return max(dx, dy) <= self.radius


class SafeZoneRegistry:
    """Track active safe zones that pause soul drain."""

    def __init__(self) -> None:
        self._zones: Dict[TileCoord, SafeZone] = {}

    def add_zone(self, tile: TileCoord, radius: float) -> SafeZone:
        zone = SafeZone(tile=tile, radius=float(radius))
        self._zones[tile] = zone
        return zone

    def remove_zone(self, tile: TileCoord) -> None:
        self._zones.pop(tile, None)

    def clear(self) -> None:
        self._zones.clear()

    def contains(self, tile: TileCoord) -> bool:
        return any(zone.contains(tile) for zone in self._zones.values())

    def to_iterable(self) -> Iterable[SafeZone]:
        return tuple(self._zones.values())


SAFE_ZONE_DEFAULTS: Dict[str, float] = {
    "glow_tree": 2.0,
    "skull_candle": 2.0,
    "skull_shrine": 2.0,
}


def resolve_safe_zone_radius(
    dataset_name: Optional[str],
    record_safe_zone_radius: Optional[float],
) -> float:
    """Determine the safe zone radius for a placeable record."""
    if record_safe_zone_radius is not None:
        return float(record_safe_zone_radius)
    if dataset_name is None:
        return 0.0
    return float(SAFE_ZONE_DEFAULTS.get(dataset_name, 0.0))


__all__ = ["SafeZone", "SafeZoneRegistry", "SAFE_ZONE_DEFAULTS", "resolve_safe_zone_radius"]
