from __future__ import annotations

from typing import Optional, Tuple

import pygame

from services.landscaping.hover import HoverState
from services.asset_loader.tiles import TileSheet

TileCoords = Tuple[int, int]


class HoverOverlay:
    """Draw hover highlights and placement previews."""

    def __init__(self, *, tile_size: int, tile_sheet: TileSheet) -> None:
        self._tile_size = tile_size
        self._tile_sheet = tile_sheet
        self._highlight_cache: dict[float, pygame.Surface] = {}
        self._preview_tile = self._tile_sheet.get(2, 2)

    def draw(self, surface: pygame.Surface, camera, hover: HoverState) -> None:
        if hover.harvest_target is not None:
            self._draw_highlight(surface, camera, hover.harvest_target)
        if hover.placement_target is not None:
            self._draw_preview(surface, camera, hover.placement_target)

    def _draw_highlight(
        self, surface: pygame.Surface, camera, tile: TileCoords
    ) -> None:
        rect = self._tile_rect(camera, tile)
        if rect is None:
            return
        highlight = self._highlight_surface(camera)
        surface.blit(highlight, rect.topleft)

    def _draw_preview(self, surface: pygame.Surface, camera, tile: TileCoords) -> None:
        rect = self._tile_rect(camera, tile)
        if rect is None:
            return
        scale = _camera_scale(camera)
        tile_size_scaled = max(1, int(round(self._tile_size * scale)))
        preview = pygame.transform.smoothscale(
            self._preview_tile,
            (tile_size_scaled, tile_size_scaled),
        ).copy()
        preview.set_alpha(160)
        surface.blit(preview, rect.topleft)

    def _tile_rect(self, camera, tile: TileCoords) -> Optional[pygame.Rect]:
        scale = _camera_scale(camera)
        world_x = tile[0] * self._tile_size
        world_y = tile[1] * self._tile_size
        screen_x, screen_y = _world_to_screen(camera, (world_x, world_y))
        width = max(1, int(round(self._tile_size * scale)))
        height = width
        return pygame.Rect(int(round(screen_x)), int(round(screen_y)), width, height)

    def _highlight_surface(self, camera) -> pygame.Surface:
        scale = _camera_scale(camera)
        if scale <= 0:
            scale = 1.0
        key = scale
        cached = self._highlight_cache.get(key)
        if cached is not None:
            return cached
        size = max(1, int(round(self._tile_size * scale)))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 160, 140))
        pygame.draw.rect(surf, (255, 255, 255, 200), surf.get_rect(), 2)
        self._highlight_cache[key] = surf
        return surf


def _camera_scale(camera) -> float:
    scale = getattr(camera, "scale", None)
    if scale is not None:
        return float(scale)
    getter = getattr(camera, "get_camera_scale", None)
    if callable(getter):
        try:
            value = getter()
        except Exception:
            value = 1.0
        return float(value if value else 1.0)
    return 1.0


def _world_to_screen(camera, pos: Tuple[float, float]) -> Tuple[float, float]:
    transform = getattr(camera, "world_to_screen", None)
    if callable(transform):
        try:
            return transform(pos)
        except Exception:
            pass
    # Fallback: derive from camera rect/scale when transform is missing
    rect = getattr(camera, "rect", None)
    if rect is None:
        getter = getattr(camera, "get_camera_rect", None)
        if callable(getter):
            rect = getter()
    scale = _camera_scale(camera)
    if rect is None:
        return pos
    return (
        (pos[0] - rect.left) * scale,
        (pos[1] - rect.top) * scale,
    )
