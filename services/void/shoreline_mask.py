"""Build screen-space shoreline masks from chunk classifications."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

import numpy as np
import pygame

from systems.world_renderer.chunk_cache import ChunkCache
from systems.world_renderer.tile_renderer import TileRenderData

ChunkKey = Tuple[int, int]


@dataclass
class ShorelineMaskBuilder:
    chunk_cache: ChunkCache
    tile_size: int
    chunk_size: int

    def build(
        self,
        visible_chunks: Iterable[ChunkKey],
        chunks: Mapping[ChunkKey, np.ndarray],
        camera_rect: pygame.Rect,
        screen_size: Tuple[int, int],
        scale: float,
    ) -> Optional[pygame.Surface]:
        width, height = screen_size
        if width <= 0 or height <= 0:
            return None
        mask_surface = pygame.Surface(screen_size, pygame.SRCALPHA)
        mask_surface.fill((0, 0, 0, 0))

        chunk_data_map: Dict[ChunkKey, TileRenderData] = {}
        for key in visible_chunks:
            data = self._ensure_chunk_data(key, chunks)
            if data is None:
                continue
            chunk_data_map[key] = data

        if not chunk_data_map:
            return None

        chunk_pixels = self.chunk_size * self.tile_size
        tile_screen_size = max(1, int(round(self.tile_size * scale)))
        ring_size = max(1, tile_screen_size // 3)

        for key, data in chunk_data_map.items():
            classification = data.classification
            rows, cols = classification.shape
            chunk_world_x = key[0] * chunk_pixels
            chunk_world_y = key[1] * chunk_pixels
            for row in range(rows):
                for col in range(cols):
                    tile_class = int(classification[row, col])
                    if tile_class == 1:
                        continue
                    world_tile_x = key[0] * self.chunk_size + col
                    world_tile_y = key[1] * self.chunk_size + row
                    if not self._has_land_neighbor(world_tile_x, world_tile_y, chunk_data_map):
                        continue
                    world_x = chunk_world_x + col * self.tile_size
                    world_y = chunk_world_y + row * self.tile_size
                    screen_x = int(round((world_x - camera_rect.left) * scale))
                    screen_y = int(round((world_y - camera_rect.top) * scale))
                    rect = pygame.Rect(screen_x, screen_y, tile_screen_size, tile_screen_size)
                    rect.inflate_ip(-tile_screen_size + ring_size, -tile_screen_size + ring_size)
                    mask_surface.fill((255, 255, 255, 200), rect)

        return mask_surface

    def _ensure_chunk_data(
        self,
        key: ChunkKey,
        chunks: Mapping[ChunkKey, np.ndarray],
    ) -> Optional[TileRenderData]:
        data = self.chunk_cache.get_chunk_data(key)
        if data is not None:
            return data
        base_tiles = self.chunk_cache.resolve_base_tiles(key, chunks)
        if base_tiles is None:
            return None
        self.chunk_cache.ensure_chunk(key, base_tiles)
        return self.chunk_cache.get_chunk_data(key)

    def _has_land_neighbor(
        self,
        tile_x: int,
        tile_y: int,
        chunk_data_map: Mapping[ChunkKey, TileRenderData],
    ) -> bool:
        for offset_x, offset_y in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            neighbor_x = tile_x + offset_x
            neighbor_y = tile_y + offset_y
            if self._is_land_tile(neighbor_x, neighbor_y, chunk_data_map):
                return True
        return False

    def _is_land_tile(
        self,
        tile_x: int,
        tile_y: int,
        chunk_data_map: Mapping[ChunkKey, TileRenderData],
    ) -> bool:
        chunk_x = tile_x // self.chunk_size
        chunk_y = tile_y // self.chunk_size
        local_x = tile_x % self.chunk_size
        local_y = tile_y % self.chunk_size
        if local_x < 0:
            chunk_x -= 1
            local_x += self.chunk_size
        if local_y < 0:
            chunk_y -= 1
            local_y += self.chunk_size
        chunk_key = (chunk_x, chunk_y)
        data = chunk_data_map.get(chunk_key)
        if data is None:
            return False
        classification = data.classification
        if local_y >= classification.shape[0] or local_x >= classification.shape[1]:
            return False
        return int(classification[local_y, local_x]) == 1


__all__ = ["ShorelineMaskBuilder"]
