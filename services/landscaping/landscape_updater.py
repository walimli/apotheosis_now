from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple, TYPE_CHECKING

import numpy as np

ChunkKey = Tuple[int, int]
TileCoords = Tuple[int, int]
LocalCoords = Tuple[int, int]

if TYPE_CHECKING:
    from services.landscaping.manager import LandscapingSystem


@dataclass
class TileMutation:
    chunk_key: ChunkKey
    local_coords: LocalCoords
    new_value: int


class LandscapeUpdater:
    """Authoritative tile read/write utilities bound to a PlayState."""

    def __init__(
        self,
        *,
        chunks: Dict[ChunkKey, np.ndarray],
        chunk_size: int,
        tile_size: int,
        world_renderer,
    ) -> None:
        self._chunks = chunks
        self._chunk_size = chunk_size
        self._tile_size = tile_size
        self._world_renderer = world_renderer

    def get_tile_value(self, tile_x: int, tile_y: int) -> Optional[int]:
        """Return tile code at world tile indices, or None if chunk is missing."""
        resolution = self._resolve_tile(tile_x, tile_y)
        if resolution is None:
            return None
        chunk, local = resolution
        return int(chunk[local[1], local[0]])

    def set_tile_value(
        self, tile_x: int, tile_y: int, new_value: int
    ) -> Optional[TileMutation]:
        """Set tile code and notify renderer. Returns mutation descriptor or None."""
        resolution = self._resolve_tile(tile_x, tile_y)
        if resolution is None:
            return None
        chunk, local = resolution
        row, col = local[1], local[0]
        if chunk[row, col] == new_value:
            return TileMutation(self._chunk_key(tile_x, tile_y), local, int(new_value))
        chunk[row, col] = new_value
        mutation = TileMutation(self._chunk_key(tile_x, tile_y), local, int(new_value))
        self._world_renderer.update_chunk(
            mutation.chunk_key[0],
            mutation.chunk_key[1],
            chunk,
            modified_tiles=[(row, col)],
        )
        return mutation

    def apply_mutations(self, mutations: Iterable[TileMutation]) -> None:
        """Batch refresh chunks after external mutations."""
        refreshed: Dict[ChunkKey, list[Tuple[int, int]]] = {}
        for mutation in mutations:
            refreshed.setdefault(mutation.chunk_key, []).append(
                (mutation.local_coords[1], mutation.local_coords[0])
            )
        for chunk_key, modified in refreshed.items():
            chunk = self._chunks.get(chunk_key)
            if chunk is None:
                continue
            self._world_renderer.update_chunk(
                chunk_key[0], chunk_key[1], chunk, modified_tiles=modified
            )

    def pixel_to_tile(self, world_x: float, world_y: float) -> TileCoords:
        """Convert world pixel coordinates to integer tile indices."""
        tile_x = int(world_x // self._tile_size)
        tile_y = int(world_y // self._tile_size)
        return tile_x, tile_y

    def _chunk_key(self, tile_x: int, tile_y: int) -> ChunkKey:
        return tile_x // self._chunk_size, tile_y // self._chunk_size

    def _resolve_tile(
        self, tile_x: int, tile_y: int
    ) -> Optional[Tuple[np.ndarray, LocalCoords]]:
        chunk_key = self._chunk_key(tile_x, tile_y)
        chunk = self._chunks.get(chunk_key)
        if chunk is None:
            return None
        local_x = tile_x % self._chunk_size
        local_y = tile_y % self._chunk_size
        if local_x < 0 or local_y < 0:
            return None
        if local_y >= chunk.shape[0] or local_x >= chunk.shape[1]:
            return None
        return chunk, (local_x, local_y)


@dataclass
class LandscapeSystemsRuntime:
    updater: LandscapeUpdater
    landscaping: "LandscapingSystem"


def bootstrap_land_systems(play_state) -> LandscapeSystemsRuntime:
    """Bootstrap the landscaping runtime for the active PlayState."""
    from services.landscaping.manager import LandscapingSystem

    world_renderer = getattr(play_state, "world_renderer", None)
    if world_renderer is None:
        raise ValueError("PlayState missing world renderer for landscaping bootstrap")
    chunk_cache = getattr(world_renderer, "chunk_cache", None)
    if chunk_cache is None:
        raise ValueError("World renderer chunk cache missing for landscaping bootstrap")
    chunks = getattr(chunk_cache, "chunk_base_tiles", None)
    if chunks is None:
        chunks = {}
    updater = LandscapeUpdater(
        chunks=chunks,
        chunk_size=getattr(world_renderer, "chunk_size", 32),
        tile_size=getattr(world_renderer, "tile_size", 64),
        world_renderer=world_renderer,
    )

    landscaping = LandscapingSystem(play_state, updater)
    return LandscapeSystemsRuntime(
        updater=updater,
        landscaping=landscaping,
    )
