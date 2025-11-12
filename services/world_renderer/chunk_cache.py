"""Chunk surface caching backed by the chunk tile renderer."""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Tuple

import numpy as np
import pygame

from services.asset_loader.tiles import TileSheet
from services.world_renderer.tile_renderer.chunk_renderer import ChunkTileRenderer
from services.world_renderer.tile_renderer.chunk_renderer import TileRenderData

ChunkKey = Tuple[int, int]


class ChunkCache:
    """Maintain cached chunk Surfaces and tile metadata."""

    def __init__(
        self,
        tile_sheet: TileSheet,
        *,
        tile_size: int = 64,
        chunk_size: int = 32,
        moss_probability: float = 0.05,
        moss_seed: int = 0,
    ) -> None:
        if tile_size <= 0:
            raise ValueError("tile_size must be a positive integer")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")

        self.tile_size = tile_size
        self.chunk_size = chunk_size

        self.renderer = ChunkTileRenderer(
            tile_sheet,
            tile_size=tile_size,
            chunk_size=chunk_size,
            moss_probability=moss_probability,
            moss_seed=moss_seed,
        )

        self.chunk_surfaces: Dict[ChunkKey, pygame.Surface] = {}
        self.chunk_base_tiles: Dict[ChunkKey, np.ndarray] = {}
        self.chunk_data: Dict[ChunkKey, TileRenderData] = {}

    def get_variant_at(self, tile_x: int, tile_y: int) -> int:
        """Return an encoded variant identifier for a tile."""
        chunk_key = self._chunk_key(tile_x, tile_y)
        data = self.chunk_data.get(chunk_key)
        if data is None:
            raise KeyError(f"Variant data missing for chunk {chunk_key}")

        classification = data.classification
        orientations = data.orientations

        local_x = tile_x % self.chunk_size
        local_y = tile_y % self.chunk_size
        if local_x < 0 or local_y < 0:
            raise ValueError(f"Negative local coordinates for tile ({tile_x}, {tile_y})")
        if local_y >= classification.shape[0] or local_x >= classification.shape[1]:
            raise ValueError(
                f"Tile ({tile_x}, {tile_y}) outside cached bounds for chunk {chunk_key}"
            )

        tile_type = int(classification[local_y, local_x])
        orientation_idx = int(orientations[local_y, local_x])
        return tile_type * 100 + orientation_idx

    def is_moss(self, tile_x: int, tile_y: int) -> bool:
        """Return True if the tile at the given world coordinates is moss-covered."""
        chunk_key = self._chunk_key(tile_x, tile_y)
        data = self.chunk_data.get(chunk_key)
        if data is None:
            raise KeyError(f"Moss data missing for chunk {chunk_key}")

        moss_flags = data.moss_flags

        local_x = tile_x % self.chunk_size
        local_y = tile_y % self.chunk_size
        if local_x < 0 or local_y < 0:
            raise ValueError(f"Negative local coordinates for tile ({tile_x}, {tile_y})")
        if local_y >= moss_flags.shape[0] or local_x >= moss_flags.shape[1]:
            raise ValueError(
                f"Tile ({tile_x}, {tile_y}) outside cached bounds for chunk {chunk_key}"
            )
        return bool(moss_flags[local_y, local_x])

    def resolve_base_tiles(
        self,
        key: ChunkKey,
        chunks: Mapping[ChunkKey, np.ndarray],
    ) -> Optional[np.ndarray]:
        if key in chunks:
            base = np.array(chunks[key], dtype=np.int8, copy=True)
            self.chunk_base_tiles[key] = base
            return base
        return self.chunk_base_tiles.get(key)

    def ensure_chunk(self, key: ChunkKey, base_tiles: np.ndarray) -> pygame.Surface:
        stored_base = self.chunk_base_tiles.get(key)
        stored_surface = self.chunk_surfaces.get(key)
        existing_data = self.chunk_data.get(key)
        needs_refresh = (
            stored_surface is None
            or stored_base is None
            or not np.array_equal(stored_base, base_tiles)
        )
        if needs_refresh:
            base_copy = np.array(base_tiles, dtype=np.int8, copy=True)
            self.chunk_base_tiles[key] = base_copy
            existing_moss = existing_data.moss_flags if existing_data else None
            render_data = self.renderer.render(
                key,
                base_copy,
                existing_moss=existing_moss,
            )
            self.chunk_surfaces[key] = render_data.surface
            self.chunk_data[key] = render_data
        return self.chunk_surfaces[key]

    def update_chunk(
        self,
        key: ChunkKey,
        tiles: np.ndarray,
        modified_tiles=None,
    ) -> None:
        base_copy = np.array(tiles, dtype=np.int8, copy=True)
        self.chunk_base_tiles[key] = base_copy
        existing_data = self.chunk_data.get(key)
        existing_moss = existing_data.moss_flags if existing_data else None
        render_data = self.renderer.render(
            key,
            base_copy,
            existing_moss=existing_moss,
        )
        self.chunk_surfaces[key] = render_data.surface
        self.chunk_data[key] = render_data

    def _chunk_key(self, tile_x: int, tile_y: int) -> ChunkKey:
        return tile_x // self.chunk_size, tile_y // self.chunk_size

    def get_chunk_data(self, key: ChunkKey) -> Optional[TileRenderData]:
        """Return cached TileRenderData for a chunk if available."""
        return self.chunk_data.get(key)


__all__ = ["ChunkCache"]
