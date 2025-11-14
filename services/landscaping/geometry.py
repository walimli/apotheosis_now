from __future__ import annotations

import math
from typing import Any, Optional, Tuple

import pygame

TileCoords = Tuple[int, int]


def screen_to_tile(camera, tile_size: int, screen_pos: Tuple[int, int]) -> TileCoords:
    """Map screen coordinates to tile indices using the active camera."""
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    rect = _camera_rect(camera)
    scale = _camera_scale(camera)
    if scale == 0:
        raise ValueError("camera scale cannot be zero")
    world_x = rect.left + screen_pos[0] / scale
    world_y = rect.top + screen_pos[1] / scale
    tile_x = math.floor(world_x / tile_size)
    tile_y = math.floor(world_y / tile_size)
    return tile_x, tile_y


def player_tile_indices(player, tile_size: int) -> TileCoords:
    """Return the tile indices under the player's center point."""
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    if isinstance(player, tuple):
        cx, cy = player
    else:
        model = getattr(player, "model", None)
        if model is None:
            raise ValueError("player missing model for tile computation")
        width = getattr(model, "w", tile_size)
        height = getattr(model, "h", tile_size)
        cx = getattr(model, "x", 0.0) + width * 0.5
        cy = getattr(model, "y", 0.0) + height * 0.5
    tile_x = math.floor(cx / tile_size)
    tile_y = math.floor(cy / tile_size)
    return tile_x, tile_y


def is_adjacent(a: TileCoords, b: TileCoords) -> bool:
    """True if tiles share an edge (4-neighbour adjacency)."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return dx + dy == 1


def direction_to_tile(player, tile: TileCoords, tile_size: int) -> TileCoords:
    """Return the directional offset from the player's tile to the target tile."""
    px, py = player_tile_indices(player, tile_size)
    return tile[0] - px, tile[1] - py


def _camera_rect(camera: Any) -> pygame.Rect:
    rect = getattr(camera, "rect", None)
    if isinstance(rect, pygame.Rect):
        return rect
    getter = getattr(camera, "get_camera_rect", None)
    if callable(getter):
        rect = getter()
        if isinstance(rect, pygame.Rect):
            return rect
    raise AttributeError("Camera object must expose rect or get_camera_rect()")


def _camera_scale(camera: Any) -> float:
    scale = getattr(camera, "scale", None)
    if scale is not None:
        return float(scale)
    getter = getattr(camera, "get_camera_scale", None)
    if callable(getter):
        try:
            return float(getter())
        except Exception:
            return 1.0
    return 1.0
