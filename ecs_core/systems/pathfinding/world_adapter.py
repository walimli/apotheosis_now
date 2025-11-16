"""World adapter exposing live chunk data to the legacy pathfinding grid."""

from __future__ import annotations

from constants import CHUNK_SIZE_TILES, TILE_SIZE


class _ProtectionStub:
    def is_tile_protected(self, _tile) -> bool:
        return False


class _PlaceablesStub:
    def __init__(self) -> None:
        self.protection = _ProtectionStub()


class PathfindingWorldView:
    """Minimal world object exposing chunk/tile metadata for pathfinding."""

    def __init__(self, world_renderer) -> None:
        if world_renderer is None:
            raise ValueError("PathfindingWorldView requires a world renderer")
        self._renderer = world_renderer
        self.tile_size = int(getattr(world_renderer, "tile_size", TILE_SIZE))
        self.chunk_size = int(getattr(world_renderer, "chunk_size", CHUNK_SIZE_TILES))
        self.placeables = _PlaceablesStub()

    @property
    def chunks(self):
        chunk_cache = getattr(self._renderer, "chunk_cache", None)
        if chunk_cache is None:
            return {}
        return chunk_cache.chunk_base_tiles

