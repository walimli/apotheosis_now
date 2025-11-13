from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Optional, Tuple

TileCoord = Tuple[int, int]
Vec2 = Tuple[float, float]


@dataclass(frozen=True)
class SafeZoneComponent:
    """Component that marks an entity as emitting a safe zone."""

    radius_tiles: float
    enabled: bool = True
    anchor_offset: Vec2 = (0.0, 0.0)
    tile_override: Optional[TileCoord] = None

    def contains_tile(self, center: TileCoord, tile: TileCoord) -> bool:
        if not self.enabled or self.radius_tiles <= 0.0:
            return False
        dx = abs(center[0] - tile[0])
        dy = abs(center[1] - tile[1])
        return max(dx, dy) <= self.radius_tiles


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


def tile_coord_from_world(position: Vec2, tile_size: float) -> TileCoord:
    """Convert a world-space position to an integer tile coordinate."""
    size = max(1.0, float(tile_size or 1.0))
    x, y = position
    return (int(math.floor(x / size)), int(math.floor(y / size)))


def safe_zone_contains_position(
    zone: SafeZoneComponent,
    zone_position: Vec2,
    target_position: Vec2,
    *,
    tile_size: float,
) -> bool:
    """Check if the target position lies within the component's safe zone."""
    if not zone.enabled or zone.radius_tiles <= 0.0:
        return False
    center_tile = zone.tile_override or tile_coord_from_world(
        (zone_position[0] + zone.anchor_offset[0], zone_position[1] + zone.anchor_offset[1]),
        tile_size,
    )
    target_tile = tile_coord_from_world(target_position, tile_size)
    return zone.contains_tile(center_tile, target_tile)


__all__ = [
    "SafeZoneComponent",
    "SAFE_ZONE_DEFAULTS",
    "resolve_safe_zone_radius",
    "tile_coord_from_world",
    "safe_zone_contains_position",
]
