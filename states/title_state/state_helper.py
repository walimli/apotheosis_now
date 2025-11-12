from __future__ import annotations

from typing import Optional, Tuple

import pygame


def display_scale(display) -> float:
    sw = max(1, int(getattr(display, "screen_width", 1)))
    sh = max(1, int(getattr(display, "screen_height", 1)))
    bw = max(1, int(getattr(display, "base_width", sw)))
    bh = max(1, int(getattr(display, "base_height", sh)))
    return min(bw / sw, bh / sh)


def scale_value(value: int, display, *, minimum: int = 1) -> int:
    scale = display_scale(display)
    return max(minimum, int(round(value * scale)))


def map_screen_to_base(display, pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    if pos is None:
        return None
    try:
        scale, off_x, off_y = display.get_present_params()
    except Exception:
        scale, off_x, off_y = 1, 0, 0
    denom = max(1, int(scale))
    bx = int((pos[0] - off_x) // denom)
    by = int((pos[1] - off_y) // denom)
    return (bx, by)


def map_event_to_base(display, event: pygame.event.Event) -> pygame.event.Event:
    if not hasattr(event, "pos"):
        return event
    screen_pos = getattr(event, "pos", None)
    base_pos = map_screen_to_base(display, screen_pos)
    if base_pos is None:
        return event
    attrs = event.dict.copy() if hasattr(event, "dict") else {}
    attrs["pos"] = base_pos
    if "screen_pos" not in attrs:
        attrs["screen_pos"] = screen_pos
    if hasattr(event, "rel"):
        rel = getattr(event, "rel", (0, 0))
        attrs.setdefault("screen_rel", rel)
        attrs["rel"] = rel
    return pygame.event.Event(event.type, attrs)


def base_mouse_pos(display) -> Tuple[int, int]:
    screen_pos = pygame.mouse.get_pos()
    base_pos = map_screen_to_base(display, screen_pos)
    if base_pos is None:
        return (0, 0)
    return base_pos


__all__ = [
    "display_scale",
    "scale_value",
    "map_event_to_base",
    "base_mouse_pos",
]
