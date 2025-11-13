from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pygame

from services.progression.xp_counter import XPCounter

from .health_bar import HealthCounter
from .inventory_bar import HotbarUI
from .soul_ui import SoulCounter


COUNTER_VERTICAL_PADDING = 16
HEALTH_COUNTER_Y_ADJUST = 0
SOUL_COUNTER_Y_ADJUST = 7


@dataclass
class UIComponents:
    """Container for PlayState UI primitives."""

    hotbar: HotbarUI
    health_counter: HealthCounter
    soul_counter: SoulCounter
    xp_counter: XPCounter


def bootstrap_ui(player: Any, display: Any, lock_state) -> UIComponents:
    """Construct hotbar UI bound to the player's inventory."""
    inventory = getattr(player, "inventory", None)
    if inventory is None:
        raise ValueError("Player missing inventory; cannot bootstrap UI")
    hotbar = HotbarUI(inventory, lock_state, slot_size=48)
    health_counter = HealthCounter(scale=1.3)
    soul_counter = SoulCounter(scale=1.2)
    xp_counter = XPCounter(scale=1.5)
    return UIComponents(
        hotbar=hotbar,
        health_counter=health_counter,
        soul_counter=soul_counter,
        xp_counter=xp_counter,
    )


def update_ui(ps) -> None:
    """Update UI elements that depend on display changes (currently no-op)."""
    _ = ps  # Placeholder for future dynamic layout adjustments


def draw_hud_screen(ps, screen: pygame.Surface) -> None:
    """Draw screen-space HUD elements that should not be scaled with the world."""
    if not _has_ui_bindings(ps):
        return
    display_w, display_h = ps.display.screen_width, ps.display.screen_height

    hotbar = ps.ui.hotbar
    hotbar.draw(screen, display_w, display_h)
    hotbar_x, hotbar_y = hotbar.get_position(display_w, display_h)
    hotbar_width = getattr(hotbar, "total_width", 0)

    health_w, health_h = ps.ui.health_counter.size
    soul_w, soul_h = ps.ui.soul_counter.size
    max_height = max(health_h, soul_h)
    base_top_offset = -max_height - COUNTER_VERTICAL_PADDING
    health_top = base_top_offset + HEALTH_COUNTER_Y_ADJUST
    soul_top = base_top_offset + SOUL_COUNTER_Y_ADJUST

    class _ScreenDisplayAdapter:
        base_width = display_w
        base_height = display_h

    ps.ui.health_counter.draw(
        screen, ps.player, hotbar, _ScreenDisplayAdapter, (0, health_top)
    )
    soul_offset_x = hotbar_width - soul_w
    ps.ui.soul_counter.draw(
        screen, ps.player, hotbar, _ScreenDisplayAdapter, (soul_offset_x, soul_top)
    )

    ps.ui.xp_counter.draw(
        screen, ps.player, _ScreenDisplayAdapter, margin_right=16, margin_top=16
    )

    notifications = getattr(ps, "notifications", None)
    if hasattr(notifications, "draw"):
        notifications.draw(screen)


def _has_ui_bindings(ps: Any) -> bool:
    if ps is None:
        return False
    ui = getattr(ps, "ui", None)
    player = getattr(ps, "player", None)
    display = getattr(ps, "display", None)
    return ui is not None and player is not None and display is not None
