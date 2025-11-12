"""Placeholder entity rendering helpers."""
from __future__ import annotations

from typing import Dict, Sequence

import pygame


def render_entities(
    screen: pygame.Surface,
    entities: Sequence[Dict],
    camera_x: int,
    camera_y: int,
    tile_size: int = 64,
    sprites: Dict[str, pygame.Surface] | None = None,
) -> None:
    """Render entities directly to the screen using simple blitting."""
    if tile_size <= 0:
        raise ValueError("tile_size must be a positive integer")
    if not entities:
        return

    for entity in sorted(entities, key=lambda data: data.get("z", 0)):
        sprite_key = entity.get("sprite_id") or entity.get("id")
        sprite = sprites.get(sprite_key) if sprites is not None else entity.get("sprite")
        if sprite is None:
            continue
        world_x = entity.get("x", 0) * tile_size + entity.get("offset_x", 0)
        world_y = entity.get("y", 0) * tile_size + entity.get("offset_y", 0)
        dest_x = int(world_x - camera_x)
        dest_y = int(world_y - camera_y)
        screen.blit(sprite, (dest_x, dest_y))
