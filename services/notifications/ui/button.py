"""Generic image button with hover and press states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pygame

from services.asset_loader.notification_assets import ButtonImages


@dataclass
class ButtonState:
    image: pygame.Surface
    rect: pygame.Rect


class ImageButton:
    """Image-backed button supporting hover and pressed visuals."""

    PRESS_DISPLAY_TIME = 0.5  # seconds

    def __init__(self, images: ButtonImages, topleft: Tuple[int, int] = (0, 0)) -> None:
        self._images = images
        self._state_images = {
            "normal": images.normal,
            "hover": images.hover,
            "pressed": images.pressed,
        }
        self._rect = images.normal.get_rect(topleft=topleft)
        self._hovered = False
        self._pressed_timer = 0.0
        self._enabled = True
        self._current_state = "normal"

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    def set_position(self, topleft: Tuple[int, int]) -> None:
        self._rect.topleft = topleft

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def handle_event(self, event) -> bool:
        if not self._enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self._rect.collidepoint(event.pos)
            if self._current_state != "pressed":
                self._current_state = "hover" if self._hovered else "normal"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect.collidepoint(event.pos):
                self._pressed_timer = self.PRESS_DISPLAY_TIME
                self._current_state = "pressed"
                return True
        return False

    def update(self, dt: float) -> None:
        if self._pressed_timer > 0.0:
            self._pressed_timer = max(0.0, self._pressed_timer - dt)
            if self._pressed_timer == 0.0:
                self._current_state = "hover" if self._hovered else "normal"

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._state_images[self._current_state], self._rect)


__all__ = ["ImageButton"]
