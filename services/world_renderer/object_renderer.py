"""Placeholder object rendering utilities."""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple, List

import pygame
from states.play.render_types import RenderPacket
from .y_sort import placeable_baseline, placeable_sort_key


def render_objects_on_surface(
    surface: pygame.Surface,
    objects: Sequence[Dict],
    sprites: Dict[str, pygame.Surface],
    *,
    chunk_origin: Tuple[int, int],
    tile_size: int,
    camera_rect: pygame.Rect,
    scale: float = 1.0,
    cache: Optional[Dict[Tuple[str, float], pygame.Surface]] = None,
    emit_packets: Optional[List[RenderPacket]] = None,
) -> None:
    """Blit object sprites for a chunk directly onto the destination surface."""
    if tile_size <= 0 or scale <= 0:
        raise ValueError("tile_size and scale must be positive")
    if not objects:
        return

    origin_x, origin_y = chunk_origin
    cam_left = camera_rect.left
    cam_top = camera_rect.top
    screen_width = surface.get_width()
    screen_height = surface.get_height()
    cache_dict = cache if cache is not None else {}
    needs_scaling = abs(scale - 1.0) > 1e-6

    # Render non-placeables immediately, collect placeables either as packets
    # (for unified sorting) or y-sorted jobs (placeables-only) when emit_packets is None.
    placeable_jobs = []  # used only when emit_packets is None
    for obj in objects:
        sprite = sprites.get(obj.get("id"))
        if sprite is None:
            continue
        tile_x = obj.get("x", 0)
        tile_y = obj.get("y", 0)
        offset_x = obj.get("offset_x", 0)
        offset_y = obj.get("offset_y", 0)
        obj_type = obj.get("type")

        if obj_type == "placeable":
            obj_scale = float(obj.get("scale", 1.0))
            center_off_x = (tile_size / 2.0) - (sprite.get_width() / 2.0)
            center_off_y = (tile_size / 2.0) - (sprite.get_height() / 2.0)
            world_x = (
                origin_x
                + tile_x * tile_size
                + center_off_x
                + float(offset_x) * obj_scale
            )
            world_y = (
                origin_y
                + tile_y * tile_size
                + center_off_y
                + float(offset_y) * obj_scale
            )
        else:
            world_x = origin_x + tile_x * tile_size + offset_x
            world_y = origin_y + tile_y * tile_size + offset_y

        screen_x = (world_x - cam_left) * scale
        screen_y = (world_y - cam_top) * scale

        if needs_scaling:
            key = (obj.get("id"), scale)
            scaled = cache_dict.get(key)
            if scaled is None:
                width = max(1, int(round(sprite.get_width() * scale)))
                height = max(1, int(round(sprite.get_height() * scale)))
                scaled = pygame.transform.scale(sprite, (width, height))
                cache_dict[key] = scaled
            draw_sprite = scaled
        else:
            draw_sprite = sprite

        # Cull off-screen
        if (
            screen_x + draw_sprite.get_width() < 0
            or screen_y + draw_sprite.get_height() < 0
            or screen_x > screen_width
            or screen_y > screen_height
        ):
            continue

        if obj_type == "placeable":
            baseline = placeable_baseline(obj, sprite.get_height(), world_y)
            order_hint = (int(tile_y), int(tile_x))
            if emit_packets is not None:
                packet = RenderPacket(
                    float(baseline),
                    int(obj.get("z", 0)),
                    order_hint,
                    draw_sprite,
                    (int(round(screen_x)), int(round(screen_y))),
                )
                emit_packets.append(packet)
            else:
                placeable_jobs.append(
                    (
                        placeable_sort_key(
                            obj,
                            baseline=baseline,
                            z=int(obj.get("z", 0)),
                            order=order_hint,
                        ),
                        int(round(screen_x)),
                        int(round(screen_y)),
                        draw_sprite,
                    )
                )
        else:
            surface.blit(draw_sprite, (int(round(screen_x)), int(round(screen_y))))

    # Draw placeables in y-sorted order
    if placeable_jobs and emit_packets is None:
        for _, sx, sy, spr in sorted(placeable_jobs, key=lambda item: item[0]):
            surface.blit(spr, (sx, sy))
