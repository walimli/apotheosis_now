from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

import pygame


def ensure_ready(
    play_state: Any,
    on_exit: Optional[Callable[[], None]],
    on_purchase: Optional[Callable[[str], None]],
) -> None:
    if play_state is None or on_exit is None or on_purchase is None:
        raise RuntimeError("ProgressionState.enter must be called before use")


def get_progression(play_state: Any):
    if play_state is None:
        raise RuntimeError("PlayState reference missing")
    model = getattr(play_state.player, "model", None)
    if model is None:
        raise AttributeError("PlayState player missing model")
    progression = getattr(model, "progression", None)
    if progression is None:
        raise AttributeError("Player model missing progression component")
    return progression


def map_screen_to_base(display, pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Convert screen-space coordinates to base-surface coordinates."""
    if pos is None:
        return None
    try:
        scale, off_x, off_y = display.get_present_params()
    except Exception:
        return pos
    denom = max(1, int(scale))
    bx = int((pos[0] - off_x) // denom)
    by = int((pos[1] - off_y) // denom)
    return (bx, by)


def remap_event_to_base(display, event: pygame.event.Event) -> pygame.event.Event:
    """Return a copy of the event whose .pos is mapped into base-space."""
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
        base_rel = map_screen_to_base(display, (screen_pos[0] + rel[0], screen_pos[1] + rel[1]))
        if base_rel is not None:
            attrs["rel"] = (base_rel[0] - base_pos[0], base_rel[1] - base_pos[1])
        else:
            attrs["rel"] = rel
        attrs.setdefault("screen_rel", rel)
    return pygame.event.Event(event.type, attrs)


def base_mouse_pos(display) -> Tuple[int, int]:
    """Read pygame's mouse position and convert it to base-space."""
    screen_pos = pygame.mouse.get_pos()
    base_pos = map_screen_to_base(display, screen_pos)
    if base_pos is None:
        return (0, 0)
    return base_pos


def display_scale(display) -> float:
    sw = max(1, int(getattr(display, "screen_width", 1)))
    sh = max(1, int(getattr(display, "screen_height", 1)))
    bw = max(1, int(getattr(display, "base_width", sw)))
    bh = max(1, int(getattr(display, "base_height", sh)))
    return min(bw / sw, bh / sh)


def apply_visual_scaling(display, visuals: dict) -> dict:
    """Scale legacy progression art to fit the current base surface."""
    scale = display_scale(display)
    if abs(scale - 1.0) < 1e-4:
        return visuals

    def _scale_surface(surface: pygame.Surface) -> pygame.Surface:
        width = max(1, int(round(surface.get_width() * scale)))
        height = max(1, int(round(surface.get_height() * scale)))
        return pygame.transform.smoothscale(surface, (width, height))

    for key in ("landscape_panel", "tall_card", "emerald_icon", "emerald_icon_small"):
        surf = visuals.get(key)
        if isinstance(surf, pygame.Surface):
            visuals[key] = _scale_surface(surf)

    system_button = visuals.get("system_button")
    if hasattr(system_button, "rescale"):
        system_button.rescale(scale)

    icon_buttons = visuals.get("icon_buttons") or []
    for icon in icon_buttons:
        if hasattr(icon, "rescale"):
            icon.rescale(scale)

    return visuals


def scale_ui_value(value: int, display, *, minimum: int = 1) -> int:
    scale = display_scale(display)
    return max(minimum, int(round(value * scale)))


__all__ = [
    "ensure_ready",
    "get_progression",
    "map_screen_to_base",
    "remap_event_to_base",
    "base_mouse_pos",
    "apply_visual_scaling",
    "display_scale",
    "scale_ui_value",
]
