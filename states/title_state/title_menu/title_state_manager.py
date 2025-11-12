"""Orchestrator for the image-driven title state."""

from __future__ import annotations

from typing import Dict, List, Optional

import pygame

from services.asset_loader.title_menu import get_title_font
from .button_sprite import ButtonSprite
from .menu_layout import MenuButtonSpec, TitleMenu
from ..title_runes import RuneField
from ..state_helper import base_mouse_pos, map_event_to_base, scale_value


class TitleStateManager:
    TITLE_TEXT = "The Dark Lord of Crafting"

    def __init__(self, game, display) -> None:
        self.game = game
        self.display = display
        self._menu: Optional[TitleMenu] = None
        self._buttons: Dict[str, ButtonSprite] = {}
        self._title_surface: Optional[pygame.Surface] = None
        self._last_size: Optional[tuple[int, int]] = None
        self._rune_field = RuneField(display)

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        self._ensure_menu()
        if self._menu is None:
            return
        for event in events:
            self._menu.handle_event(map_event_to_base(self.display, event))

    def update(self, dt: float) -> None:
        self._ensure_menu()
        if self._menu is None:
            return
        self._relayout_if_needed()
        self._menu.update_hover(base_mouse_pos(self.display))
        self._rune_field.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        self._rune_field.draw(surface)
        if self._menu is not None:
            self._menu.draw(surface)

    def _ensure_menu(self) -> None:
        if self._menu is not None:
            return
        self._title_surface = self._render_title_surface()
        specs = [
            MenuButtonSpec("continue", "CONTINUE", self._noop, enabled=False),
            MenuButtonSpec("new", "NEW", self._on_new_game),
            MenuButtonSpec("load", "LOAD", self._noop, enabled=False),
            MenuButtonSpec("settings", "SETTINGS", self._noop, enabled=False),
            MenuButtonSpec("quit", "QUIT", self._on_quit),
        ]
        self._menu = TitleMenu(self.display, self._title_surface, specs)
        self._buttons = self._menu.buttons()
        self._last_size = self.display.get_base_surface().get_size()

    def _relayout_if_needed(self) -> None:
        size = self.display.get_base_surface().get_size()
        if size != self._last_size:
            self._last_size = size
            self._title_surface = self._render_title_surface()
            self._menu.set_title_surface(self._title_surface)
        else:
            self._menu.relayout()

    def _render_title_surface(self) -> pygame.Surface:
        font_size = scale_value(30, self.display)
        font = get_title_font(self.display, font_size)
        return font.render(self.TITLE_TEXT, True, (255, 255, 255))

    def _on_new_game(self) -> None:
        from states.play import PlayState

        self.game.states["play"] = PlayState(
            self.game, self.display, self.game.audio_manager, self.game.project_root
        )
        self.game.set_state("play")

    def _on_quit(self) -> None:
        self.game.quit()

    @staticmethod
    def _noop() -> None:
        return
