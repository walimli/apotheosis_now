from __future__ import annotations

from typing import Callable, Dict, Sequence, Tuple

from .widgets import IconButton


def update_hover_state(
    icon_buttons: Sequence[IconButton],
    icon_text_map: Dict[str, str],
    default_text_id: str,
    mouse_pos: Tuple[int, int],
) -> str:
    hovered_key: str | None = None
    for icon in icon_buttons:
        hit = icon.rect.collidepoint(mouse_pos)
        icon.set_hovered(hit)
        if hit:
            hovered_key = icon.key
    if hovered_key is None:
        return default_text_id
    text_id = icon_text_map.get(hovered_key)
    if text_id is None:
        raise RuntimeError(f"No text mapped for icon '{hovered_key}'")
    return text_id


def handle_icon_click(
    icon_buttons: Sequence[IconButton],
    mouse_pos: Tuple[int, int],
    can_purchase: Callable[[str], bool],
    on_purchase: Callable[[str], None],
) -> bool:
    for icon in icon_buttons:
        if icon.rect.collidepoint(mouse_pos):
            icon.trigger_select()
            if not can_purchase(icon.key):
                return False
            on_purchase(icon.key)
            return True
    return False


__all__ = ["update_hover_state", "handle_icon_click"]
