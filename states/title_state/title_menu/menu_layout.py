"""Layout management for the custom title menu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

import pygame

from services.asset_loader.title_menu import load_button_images
from .button_sprite import ButtonSprite
from ..state_helper import display_scale, scale_value

BUTTON_GAP = 16


@dataclass(slots=True)
class MenuButtonSpec:
    key: str
    label: str
    callback: Callable[[], None]
    enabled: bool = True


class TitleMenu:
    def __init__(
        self,
        display,
        title_surface: pygame.Surface,
        button_specs: Iterable[MenuButtonSpec],
    ) -> None:
        self._display = display
        self._title_surface = title_surface
        self._button_specs = list(button_specs)
        self._buttons: Dict[str, ButtonSprite] = {}
        self._order: List[str] = []
        self._title_rect = pygame.Rect(0, 0, 0, 0)
        self._last_size: Tuple[int, int] | None = None
        self._scale = display_scale(display)
        self._build_buttons()
        self.relayout(force=True)

    def _build_buttons(self) -> None:
        self._buttons.clear()
        self._order.clear()
        for spec in self._button_specs:
            images = load_button_images(spec.key, spec.label)
            button = ButtonSprite(spec.key, images, callback=spec.callback)
            button.rescale(self._scale)
            if not spec.enabled:
                button.set_enabled(False)
            self._buttons[spec.key] = button
            self._order.append(spec.key)

    def set_title_surface(self, surface: pygame.Surface) -> None:
        self._title_surface = surface
        self.relayout(force=True)

    def relayout(self, force: bool = False) -> None:
        base = self._display.get_base_surface()
        size = base.get_size()
        if not force and self._last_size == size:
            return
        current_scale = display_scale(self._display)
        if abs(current_scale - self._scale) > 1e-4:
            self._scale = current_scale
            for button in self._buttons.values():
                button.rescale(self._scale)
        self._last_size = size
        center_x = size[0] // 2
        total_content_height = sum(
            self._buttons[key].content_height for key in self._order
        )
        gap = max(8, int(round(BUTTON_GAP * self._scale)))
        total_gap = gap * max(len(self._order) - 1, 0)
        total_height = total_content_height + total_gap
        start_y = size[1] / 2 - total_height / 2
        current_y = start_y
        for key in self._order:
            button = self._buttons[key]
            content_height = button.content_height
            content_center_y = current_y + content_height / 2
            button.position_content_center((center_x, content_center_y))
            current_y += content_height + gap
        min_title_gap = scale_value(80, self._display)
        title_y = start_y - max(min_title_gap, self._title_surface.get_height())
        self._title_rect = self._title_surface.get_rect(
            center=(center_x, int(round(title_y)))
        )

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._title_surface, self._title_rect)
        for key in self._order:
            self._buttons[key].draw(surface)

    def handle_event(self, event: pygame.event.Event) -> None:
        for key in self._order:
            self._buttons[key].handle_event(event)

    def update_hover(self, mouse_pos: Tuple[int, int]) -> None:
        for key in self._order:
            self._buttons[key].update_hover(mouse_pos)

    def get_button(self, key: str) -> ButtonSprite:
        return self._buttons[key]

    def buttons(self) -> Dict[str, ButtonSprite]:
        return self._buttons
