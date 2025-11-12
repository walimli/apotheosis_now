"""WorldRenderer orchestrates chunk, object, and entity rendering."""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pygame

from services.asset_loader.tiles import TileSheet
from systems.ecs_core import (
    Camera2DComponent,
    EntityManager,
    VoidVisualComponent,
    World,
)
from services.void import VoidRenderSystem

from .camera import compute_visible_chunks
from .chunk_cache import ChunkCache
from .entity_renderer import render_entities
from .object_renderer import render_objects_on_surface

ChunkKey = Tuple[int, int]


class WorldRenderer:
    """Manage chunk caching and draw the visible world to the screen."""

    def __init__(
        self,
        screen: pygame.Surface,
        tile_sheet: TileSheet,
        *,
        tile_size: int = 64,
        chunk_size: int = 32,
        object_sprites: Optional[Dict[str, pygame.Surface]] = None,
        entity_sprites: Optional[Dict[str, pygame.Surface]] = None,
    ) -> None:
        if tile_size <= 0:
            raise ValueError("tile_size must be a positive integer")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")

        self.screen = screen
        self.tile_size = tile_size
        self.chunk_size = chunk_size
        self.object_sprites = object_sprites or {}
        self.entity_sprites = entity_sprites or {}

        self._object_scale_cache: Dict[Tuple[str, float], pygame.Surface] = {}

        self._last_object_scale: float = 1.0

        self.chunk_cache = ChunkCache(
            tile_sheet,
            tile_size=tile_size,
            chunk_size=chunk_size,
        )

        self.render_world = World()
        self._render_entity_manager = EntityManager()
        self._render_camera_entity = self._render_entity_manager.create()
        initial_rect = pygame.Rect(
            0, 0, self.screen.get_width(), self.screen.get_height()
        )
        self.render_world.add(
            self._render_camera_entity,
            Camera2DComponent(rect=initial_rect.copy(), scale=1.0, scroll=(0.0, 0.0)),
        )
        self.render_world.add(
            self._render_camera_entity,
            VoidVisualComponent(),
        )
        self.void_render_system = VoidRenderSystem(
            self.render_world,
            target_surface=self.screen,
        )

        self.camera_x = 0
        self.camera_y = 0

        # Defer placeable drawing to a unified y-sort compositor when enabled.
        self.defer_placeables: bool = False
        self._placeable_packets: list["RenderPacket"] = []

    def render_visible_chunks(
        self,
        chunks: Mapping[ChunkKey, np.ndarray],
        objects: Mapping[ChunkKey, Sequence[Dict]],
        camera_x: int,
        camera_y: int,
        *,
        entities: Optional[Sequence[Dict]] = None,
        camera=None,
    ) -> None:
        """Render visible chunks, overlay objects, then draw entities."""
        self.camera_x = camera_x
        self.camera_y = camera_y

        scale = 1.0
        camera_rect = pygame.Rect(
            camera_x, camera_y, self.screen.get_width(), self.screen.get_height()
        )
        if camera is not None and hasattr(camera, "rect"):
            camera_rect = camera.rect
            scale = float(getattr(camera, "scale", 1.0))

        if scale <= 0:
            scale = 1.0

        screen_width_world = camera_rect.width
        screen_height_world = camera_rect.height

        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        visible = compute_visible_chunks(
            camera_x,
            camera_y,
            screen_width_world,
            screen_height_world,
            chunk_size=self.chunk_size,
            tile_size=self.tile_size,
        )

        self._sync_camera_component(camera_rect, scale)
        self.void_render_system.set_target_surface(self.screen)
        self.void_render_system.update()

        chunk_pixels = self.chunk_size * self.tile_size
        if abs(scale - self._last_object_scale) > 1e-6:
            self._object_scale_cache.clear()
            self._last_object_scale = scale
        # Clear last frame's placeable packets if deferring
        if self.defer_placeables:
            self._placeable_packets = []

        for key in visible:
            base_tiles = self.chunk_cache.resolve_base_tiles(key, chunks)
            if base_tiles is None:
                continue
            tile_surface = self.chunk_cache.ensure_chunk(key, base_tiles)
            object_list = objects.get(key) or []

            chunk_world_x = key[0] * chunk_pixels
            chunk_world_y = key[1] * chunk_pixels
            chunk_rect = pygame.Rect(
                chunk_world_x, chunk_world_y, chunk_pixels, chunk_pixels
            )
            visible_world_rect = chunk_rect.clip(camera_rect)
            if visible_world_rect.width <= 0 or visible_world_rect.height <= 0:
                continue

            local_rect = pygame.Rect(
                visible_world_rect.left - chunk_world_x,
                visible_world_rect.top - chunk_world_y,
                visible_world_rect.width,
                visible_world_rect.height,
            )

            sub_surface = tile_surface.subsurface(local_rect)
            dest_x = visible_world_rect.left - camera_rect.left
            dest_y = visible_world_rect.top - camera_rect.top

            if abs(scale - 1.0) > 1e-6:
                scaled_surface = pygame.transform.scale(
                    sub_surface,
                    (
                        max(1, int(round(local_rect.width * scale))),
                        max(1, int(round(local_rect.height * scale))),
                    ),
                )
                screen_pos = (
                    int(round(dest_x * scale)),
                    int(round(dest_y * scale)),
                )
                self.screen.blit(scaled_surface, screen_pos)
            else:
                self.screen.blit(sub_surface, (dest_x, dest_y))

            if object_list and self.object_sprites:
                render_objects_on_surface(
                    self.screen,
                    object_list,
                    self.object_sprites,
                    chunk_origin=(chunk_world_x, chunk_world_y),
                    tile_size=self.tile_size,
                    camera_rect=camera_rect,
                    scale=scale,
                    cache=self._object_scale_cache,
                    emit_packets=(
                        self._placeable_packets if self.defer_placeables else None
                    ),
                )

        if entities:
            render_entities(
                self.screen,
                entities,
                camera_x,
                camera_y,
                tile_size=self.tile_size,
                sprites=self.entity_sprites,
            )

    def get_placeable_packets(self):
        try:
            return tuple(self._placeable_packets)
        except Exception:
            return tuple()

    def update_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
        tiles: np.ndarray,
        modified_tiles: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> None:
        """Refresh cached data for a chunk after tile mutations."""
        key = (chunk_x, chunk_y)
        self.chunk_cache.update_chunk(key, tiles, modified_tiles)

    def _sync_camera_component(self, camera_rect: pygame.Rect, scale: float) -> None:
        scroll = (float(camera_rect.left), float(camera_rect.top))
        component = Camera2DComponent(
            rect=camera_rect.copy(),
            scale=scale,
            scroll=scroll,
        )
        self.render_world.add(self._render_camera_entity, component)
