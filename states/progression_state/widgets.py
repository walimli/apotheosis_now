from __future__ import annotations

from typing import Callable, Optional, Tuple

import pygame

from services.audio_package import publish_audio_event


class IconButton:
    FLASH_DURATION = 0.25

    def __init__(
        self,
        key: str,
        title: str,
        base: pygame.Surface,
        hover: pygame.Surface,
        selected: pygame.Surface,
    ) -> None:
        self.key = key
        self.title = title
        self._surfaces = {
            "default": base,
            "hover": hover,
            "select": selected,
        }
        self.rect = base.get_rect()
        self.title_surface: Optional[pygame.Surface] = None
        self.title_rect: Optional[pygame.Rect] = None
        self.hovered = False
        self._flash_timer = 0.0

    def set_title_surface(self, surf: pygame.Surface) -> None:
        self.title_surface = surf
        self._update_title_rect()

    def set_center(self, center: Tuple[int, int]) -> None:
        self.rect = self._surfaces["default"].get_rect()
        self.rect.center = (int(center[0]), int(center[1]))
        self._update_title_rect()

    def _update_title_rect(self) -> None:
        if self.title_surface is None:
            self.title_rect = None
            return
        rect = self.title_surface.get_rect()
        rect.midbottom = (self.rect.centerx, self.rect.top - 12)
        self.title_rect = rect

    def reset(self) -> None:
        self.hovered = False
        self._flash_timer = 0.0

    def set_hovered(self, hovered: bool) -> None:
        previous = self.hovered
        self.hovered = hovered
        if self.hovered and not previous:
            publish_audio_event("ui.button.hover")
        if not hovered:
            return

    def trigger_select(self) -> None:
        publish_audio_event("ui.button.click")
        self._flash_timer = self.FLASH_DURATION

    def update(self, dt: float) -> None:
        if self._flash_timer > 0.0:
            self._flash_timer = max(0.0, self._flash_timer - float(dt))

    def draw(self, surface: pygame.Surface) -> None:
        if self._flash_timer > 0.0:
            surf = self._surfaces["select"]
        elif self.hovered:
            surf = self._surfaces["hover"]
        else:
            surf = self._surfaces["default"]
        surface.blit(surf, self.rect)
        if self.title_surface is not None and self.title_rect is not None:
            surface.blit(self.title_surface, self.title_rect)

    @property
    def width(self) -> int:
        return self.rect.width

    @property
    def height(self) -> int:
        return self.rect.height

    def rescale(self, scale: float) -> None:
        if scale <= 0 or abs(scale - 1.0) < 1e-4:
            return
        center = self.rect.center
        new_surfaces = {}
        for key, surface in self._surfaces.items():
            width = max(1, int(round(surface.get_width() * scale)))
            height = max(1, int(round(surface.get_height() * scale)))
            new_surfaces[key] = pygame.transform.smoothscale(surface, (width, height))
        self._surfaces = new_surfaces
        self.rect = self._surfaces["default"].get_rect()
        self.rect.center = center
        self._update_title_rect()


class SystemButton:
    def __init__(
        self,
        default: pygame.Surface,
        hover: pygame.Surface,
        pressed: pygame.Surface,
    ) -> None:
        self._surfaces = {
            "default": default,
            "hover": hover,
            "pressed": pressed,
        }
        self.rect = default.get_rect()
        self.hovered = False
        self.pressed = False
        self._on_click: Optional[Callable[[], None]] = None

    def set_on_click(self, fn: Callable[[], None]) -> None:
        self._on_click = fn

    def set_rect(self, rect: pygame.Rect) -> None:
        self.rect = rect

    def reset(self) -> None:
        self.hovered = False
        self.pressed = False

    def refresh_hover(self, mouse_pos: Tuple[int, int]) -> None:
        inside = self.rect.collidepoint(mouse_pos)
        if inside and not self.hovered:
            publish_audio_event("ui.button.hover")
        if not inside:
            self.pressed = False
        self.hovered = inside

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.refresh_hover(event.pos)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.hovered = True
                self.pressed = True
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed and self.rect.collidepoint(event.pos)
            self.pressed = False
            if was_pressed:
                if self._on_click is None:
                    raise RuntimeError("System button click handler not bound")
                publish_audio_event("ui.button.click")
                self._on_click()
            return
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN,
            pygame.K_SPACE,
        ):
            if self._on_click is None:
                raise RuntimeError("System button click handler not bound")
            publish_audio_event("ui.button.click")
            self._on_click()

    def draw(self, surface: pygame.Surface) -> None:
        if self.pressed:
            surf = self._surfaces["pressed"]
        elif self.hovered:
            surf = self._surfaces["hover"]
        else:
            surf = self._surfaces["default"]
        surface.blit(surf, self.rect)

    def rescale(self, scale: float) -> None:
        if scale <= 0 or abs(scale - 1.0) < 1e-4:
            return
        center = self.rect.center
        new_surfaces = {}
        for key, surface in self._surfaces.items():
            width = max(1, int(round(surface.get_width() * scale)))
            height = max(1, int(round(surface.get_height() * scale)))
            new_surfaces[key] = pygame.transform.smoothscale(surface, (width, height))
        self._surfaces = new_surfaces
        self.rect = self._surfaces["default"].get_rect()
        if center != (0, 0):
            self.rect.center = center


__all__ = ["IconButton", "SystemButton"]
