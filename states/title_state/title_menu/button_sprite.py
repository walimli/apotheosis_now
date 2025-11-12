"""Sprite-like button that swaps surfaces based on interaction state."""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import pygame

from services.audio_package import publish_audio_event
from services.asset_loader.title_menu import button_vertical_bounds


class ButtonSprite:
    def __init__(
        self,
        name: str,
        images: Dict[str, pygame.Surface],
        callback: Callable[[], None],
        position: Tuple[int, int] | None = None,
    ) -> None:
        self.name = name
        self._base_images = {state: surface.copy() for state, surface in images.items()}
        self._images = {state: surface.copy() for state, surface in images.items()}
        self._callback = callback
        topleft = position or (0, 0)
        self._rect = images["normal"].get_rect(topleft=topleft)
        self._pressed = False
        self._hover = False
        self._enabled = True
        self._disabled_surface: Optional[pygame.Surface] = None
        self._content_offset, self._content_height = self._compute_content_metrics()
        self._base_content_offset = self._content_offset
        self._base_content_height = self._content_height
        self._content_center_delta = self._rect.height / 2 - (
            self._content_offset + self._content_height / 2
        )
        self._scale = 1.0

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def content_height(self) -> int:
        return self._content_height

    @property
    def content_offset(self) -> int:
        return self._content_offset

    def set_center(self, center: Tuple[int, int]) -> None:
        self._rect.center = (int(center[0]), int(center[1]))

    def position_content_center(self, center: Tuple[int, float]) -> None:
        center_x, content_center_y = center
        center_y = content_center_y + self._content_center_delta
        self._rect.center = (int(center_x), int(round(center_y)))

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled == enabled:
            return
        self._enabled = enabled
        if not enabled:
            self._hover = False
            self._pressed = False
        else:
            self._disabled_surface = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process pygame mouse events. Return True if the button fired."""
        if not self._enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hover = self._content_rect().collidepoint(event.pos)
            if not self._hover:
                self._pressed = False
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._content_rect().collidepoint(event.pos):
                self._pressed = True
            return False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self._content_rect().collidepoint(event.pos):
                publish_audio_event("ui.button.click")
                self._callback()
                return True
        return False

    def update_hover(self, mouse_pos: Tuple[int, int]) -> None:
        if not self._enabled:
            self._hover = False
            self._pressed = False
            return
        previous = self._hover
        inside = self._content_rect().collidepoint(mouse_pos)
        if inside and not previous:
            publish_audio_event("ui.button.hover")
        if inside != previous:
            self._hover = inside
            if not inside:
                self._pressed = False

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._resolve_surface(), self._rect)

    def _content_rect(self) -> pygame.Rect:
        rect = self._rect.copy()
        rect.y += self._content_offset
        rect.height = self._content_height
        return rect

    def _compute_content_metrics(self) -> Tuple[int, int]:
        top, bottom = button_vertical_bounds(self.name)
        height = max(1, bottom - top + 1)
        return top, height

    def _resolve_surface(self) -> pygame.Surface:
        if not self._enabled:
            return self._get_disabled_surface()
        if self._pressed:
            return self._images["pressed"]
        if self._hover:
            return self._images["hover"]
        return self._images["normal"]

    def _get_disabled_surface(self) -> pygame.Surface:
        if self._disabled_surface is None:
            # Create a dimmed copy to signal disabled state.
            base = self._images["normal"].copy()
            overlay = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            base.blit(overlay, (0, 0))
            self._disabled_surface = base
        return self._disabled_surface

    def rescale(self, scale: float) -> None:
        if scale <= 0 or abs(scale - self._scale) < 1e-4:
            return
        self._scale = scale
        center = self._rect.center
        scaled_images: Dict[str, pygame.Surface] = {}
        for key, surface in self._base_images.items():
            width = max(1, int(round(surface.get_width() * scale)))
            height = max(1, int(round(surface.get_height() * scale)))
            scaled_images[key] = pygame.transform.smoothscale(surface, (width, height))
        self._images = scaled_images
        self._rect = self._images["normal"].get_rect(center=center)
        self._content_offset = max(0, int(round(self._base_content_offset * scale)))
        self._content_height = max(1, int(round(self._base_content_height * scale)))
        self._content_center_delta = self._rect.height / 2 - (
            self._content_offset + self._content_height / 2
        )
        self._disabled_surface = None
