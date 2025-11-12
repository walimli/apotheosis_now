from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, cast

import pygame

from services.asset_loader.progression_assets import (
    load_progression_text_entries,
    load_progression_visuals,
    progression_font_path,
    progression_text_root,
)
from .input_handlers import handle_icon_click, update_hover_state
from .layout import LayoutManager
from .renderers import draw_currency_panel, draw_icon_progress, draw_tall_card_text
from .state_helpers import (
    apply_visual_scaling,
    base_mouse_pos,
    ensure_ready,
    get_progression,
    remap_event_to_base,
)
from .text_content import TextContent
from .widgets import IconButton, SystemButton


class ProgressionState:
    ICON_LAYOUT = [
        ("might", "Might"),
        ("speed", "Speed"),
        ("health", "Health"),
        ("formula", "Formula"),
        ("fortune", "Fortune"),
        ("octopus", "Octopus"),
    ]

    def __init__(self, game, display) -> None:
        self.game = game
        self.display = display
        self.play_state = None
        self._on_exit: Optional[Callable[[], None]] = None
        self._on_purchase: Optional[Callable[[str], None]] = None

        font_path = progression_font_path()
        self._font_root = font_path.parent
        self._text_root = progression_text_root()

        self._title_font = self.display.get_scaled_font(str(font_path), 32)
        self._small_font = self.display.get_scaled_font(str(font_path), 22)
        self._hud_font = self.display.get_scaled_font(str(font_path), 28)
        self._cost_font = self.display.get_scaled_font(str(font_path), 24)

        visuals = load_progression_visuals(self.ICON_LAYOUT)
        visuals = apply_visual_scaling(self.display, visuals)
        self.landscape_panel = cast(pygame.Surface, visuals["landscape_panel"])
        self.tall_card = cast(pygame.Surface, visuals["tall_card"])
        self.emerald_icon = cast(pygame.Surface, visuals["emerald_icon"])
        self.emerald_icon_small = cast(pygame.Surface, visuals["emerald_icon_small"])
        self.system_button = cast(SystemButton, visuals["system_button"])
        self.icon_buttons = cast(list[IconButton], visuals["icon_buttons"])

        self._layout = LayoutManager()

        entries, icon_map, default_id = load_progression_text_entries(
            self._font_root, self.display, self.ICON_LAYOUT
        )
        self._text_entries: Dict[str, TextContent] = entries
        self._icon_text_map: Dict[str, str] = icon_map
        self._default_text_id: str = default_id
        self._current_text_id: str = default_id

        self.system_button.set_on_click(self._request_exit)

    def enter(
        self,
        play_state,
        *,
        on_exit: Callable[[], None],
        on_purchase: Callable[[str], None],
    ) -> None:
        if play_state is None:
            raise ValueError("play_state is required")
        self.play_state = play_state
        self._on_exit = on_exit
        self._on_purchase = on_purchase
        self._current_text_id = self._default_text_id
        for icon in self.icon_buttons:
            icon.reset()
        self.system_button.reset()
        self._layout.reset()

    def handle_events(self, events) -> None:
        ensure_ready(self.play_state, self._on_exit, self._on_purchase)
        for event in events:
            base_event = remap_event_to_base(self.display, event)
            self.system_button.handle_event(base_event)
            if base_event.type == pygame.MOUSEMOTION:
                self._current_text_id = update_hover_state(
                    self.icon_buttons,
                    self._icon_text_map,
                    self._default_text_id,
                    base_event.pos,
                )
            elif base_event.type == pygame.MOUSEBUTTONDOWN and base_event.button == 1:
                handle_icon_click(
                    self.icon_buttons,
                    base_event.pos,
                    self._can_afford_upgrade,
                    self._require_purchase(),
                )
            elif base_event.type == pygame.KEYDOWN and base_event.key == pygame.K_ESCAPE:
                self._request_exit()

    def update(self, dt: float) -> None:
        ensure_ready(self.play_state, self._on_exit, self._on_purchase)
        size = self.display.get_base_surface().get_size()
        self._layout.ensure(
            size,
            self.landscape_panel,
            self.tall_card,
            self.system_button,
            self.icon_buttons,
        )
        mouse_pos = base_mouse_pos(self.display)
        self._current_text_id = update_hover_state(
            self.icon_buttons,
            self._icon_text_map,
            self._default_text_id,
            mouse_pos,
        )
        for icon in self.icon_buttons:
            icon.update(dt)
        self.system_button.refresh_hover(mouse_pos)

    def render(self, base_surface: pygame.Surface) -> None:
        ensure_ready(self.play_state, self._on_exit, self._on_purchase)
        size = base_surface.get_size()
        self._layout.ensure(
            size,
            self.landscape_panel,
            self.tall_card,
            self.system_button,
            self.icon_buttons,
        )
        base_surface.fill((14, 12, 32))

        square_rect = self._layout.square_rect
        tall_rect = self._layout.tall_rect
        if square_rect is None or tall_rect is None:
            raise RuntimeError("Layout not established")

        base_surface.blit(self.landscape_panel, square_rect)
        base_surface.blit(self.tall_card, tall_rect)

        self.system_button.draw(base_surface)

        progression = get_progression(self.play_state)
        for icon in self.icon_buttons:
            icon.draw(base_surface)
            draw_icon_progress(
                base_surface,
                icon,
                progression,
                self._small_font,
                self._cost_font,
                self.emerald_icon_small,
            )

        draw_currency_panel(
            base_surface, progression, self._hud_font, self.emerald_icon_small
        )
        draw_tall_card_text(
            base_surface,
            self._current_text_id,
            self._text_entries,
            tall_rect,
        )

    def _request_exit(self) -> None:
        if self._on_exit is None:
            raise RuntimeError("Exit handler not bound")
        self._on_exit()

    def _can_afford_upgrade(self, key: str) -> bool:
        progression = get_progression(self.play_state)
        try:
            cost = progression.get_upgrade_cost(key)
        except Exception:
            return False
        return progression.emeralds >= cost

    def _require_purchase(self) -> Callable[[str], None]:
        if self._on_purchase is None:
            raise RuntimeError("Purchase handler not bound")
        return self._on_purchase


__all__ = ["ProgressionState"]
