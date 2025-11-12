from __future__ import annotations

from typing import Any, Dict

import pygame

from .text_content import TextContent
from .widgets import IconButton


def draw_icon_progress(
    surface: pygame.Surface,
    icon: IconButton,
    progression: Any,
    small_font: pygame.font.Font,
    cost_font: pygame.font.Font,
    emerald_icon_small: pygame.Surface,
) -> None:
    cost = progression.get_upgrade_cost(icon.key)

    cost_surface = cost_font.render(str(cost), True, (255, 255, 255))
    cost_icon_rect = emerald_icon_small.get_rect()
    cost_text_rect = cost_surface.get_rect()
    group_width = cost_icon_rect.width + 6 + cost_text_rect.width
    start_x = icon.rect.centerx - group_width // 2
    cost_icon_rect.topleft = (start_x, icon.rect.bottom + 12)
    cost_text_rect.midleft = (cost_icon_rect.right + 6, cost_icon_rect.centery)
    surface.blit(emerald_icon_small, cost_icon_rect)
    surface.blit(cost_surface, cost_text_rect)


def draw_currency_panel(
    surface: pygame.Surface,
    progression: Any,
    hud_font: pygame.font.Font,
    emerald_icon_small: pygame.Surface,
) -> None:
    emeralds = progression.emeralds
    xp = progression.xp
    hud_margin = 20
    hud_x = hud_margin
    hud_y = hud_margin

    emerald_rect = emerald_icon_small.get_rect()
    emerald_rect.topleft = (hud_x, hud_y)
    surface.blit(emerald_icon_small, emerald_rect)

    emerald_text = hud_font.render(f"{emeralds}", True, (255, 255, 255))
    emerald_text_rect = emerald_text.get_rect()
    emerald_text_rect.midleft = (emerald_rect.right + 10, emerald_rect.centery)
    surface.blit(emerald_text, emerald_text_rect)

    xp_text = hud_font.render(f"XP {xp}", True, (200, 200, 255))
    xp_rect = xp_text.get_rect()
    xp_rect.topleft = (hud_x, emerald_rect.bottom + 12)
    surface.blit(xp_text, xp_rect)


def draw_tall_card_text(
    surface: pygame.Surface,
    current_text_id: str,
    text_entries: Dict[str, TextContent],
    tall_rect: pygame.Rect,
) -> None:
    entry = text_entries.get(current_text_id)
    if entry is None:
        raise RuntimeError(f"Unknown text id '{current_text_id}'")
    entry.draw(surface, tall_rect)


__all__ = [
    "draw_icon_progress",
    "draw_currency_panel",
    "draw_tall_card_text",
]
