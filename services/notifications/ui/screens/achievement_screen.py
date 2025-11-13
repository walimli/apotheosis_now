"""Achievement viewer screen."""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

import pygame

from services.notifications import TriggeredNotification

from services.asset_loader.notification_assets import ButtonImages, NotificationUIAssets
from ..button import ImageButton
from .base import JournalScreen


class AchievementScreenResult(Enum):
    NONE = "none"
    PREVIOUS = "previous"
    CURRENT = "current"
    CLOSE = "close"


class AchievementScreen(JournalScreen):
    """Displays the current achievement with navigation controls."""

    CONTENT_MARGIN = 64
    TITLE_COLOR = (255, 255, 255)
    BODY_COLOR = (255, 255, 255)
    LINE_SPACING = 6
    FOOTER_BUTTON_SCALE = 0.75

    def __init__(self, assets: NotificationUIAssets) -> None:
        super().__init__(assets)
        self.window_surface = assets.notification_window
        self.window_rect = self.window_surface.get_rect()
        self.content_rect = pygame.Rect(0, 0, 0, 0)

        font_path = assets.font_path()
        self._font_path_str = str(font_path)
        self._font_cache: dict[int, pygame.font.Font] = {}

        self._title_surface: Optional[pygame.Surface] = None
        self._body_surface: Optional[pygame.Surface] = None
        self._title_pos = pygame.Vector2()
        self._body_pos = pygame.Vector2()

        self._current_entry: Optional[TriggeredNotification] = None

        self.previous_button = self._make_footer_button("Previous")
        self.current_button = self._make_footer_button("Current")
        self.close_button = self._make_close_button()

        self._empty_text_surface = self._make_placeholder_surface()
        self.set_entry(None)

    def _font(self, size: int) -> pygame.font.Font:
        font = self._font_cache.get(size)
        if font is None:
            font = pygame.font.Font(self._font_path_str, size)
            self._font_cache[size] = font
        return font

    def _make_placeholder_surface(self) -> pygame.Surface:
        font = self._font(28)
        text = "No achievements available yet."
        surface = font.render(text, True, self.BODY_COLOR)
        return surface

    def _make_footer_button(self, label: str) -> ImageButton:
        font = self._font(26)
        images = self.assets.notification_panel_button_images
        labelled = ButtonImages(
            normal=self._label_surface(images.normal, font, label),
            hover=self._label_surface(images.hover, font, label),
            pressed=self._label_surface(images.pressed, font, label),
        )
        labelled = self._scale_button_images(labelled, self.FOOTER_BUTTON_SCALE)
        return ImageButton(labelled)

    def _make_close_button(self) -> ImageButton:
        base = self.assets.exit_icon
        hover = self._apply_tint(base, add=60)
        pressed = self._apply_tint(base, sub=60)
        images = ButtonImages(normal=base, hover=hover, pressed=pressed)
        return ImageButton(images)

    @staticmethod
    def _apply_tint(
        surface: pygame.Surface, *, add: int = 0, sub: int = 0
    ) -> pygame.Surface:
        result = surface.copy()
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if add:
            overlay.fill((add, add, add, 0))
            result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if sub:
            overlay.fill((sub, sub, sub, 0))
            result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        return result

    def _label_surface(
        self, base: pygame.Surface, font: pygame.font.Font, label: str
    ) -> pygame.Surface:
        surface = base.copy()
        text = font.render(label, True, self.BODY_COLOR)
        rect = text.get_rect(
            center=(surface.get_width() // 2, surface.get_height() // 2)
        )
        surface.blit(text, rect)
        return surface

    def _scale_button_images(self, images: ButtonImages, scale: float) -> ButtonImages:
        if scale == 1.0:
            return images

        def _scale(surface: pygame.Surface) -> pygame.Surface:
            w, h = surface.get_size()
            size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
            return pygame.transform.smoothscale(surface, size)

        return ButtonImages(
            normal=_scale(images.normal),
            hover=_scale(images.hover),
            pressed=_scale(images.pressed),
        )

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        width, height = surface_size
        self.window_rect = self.window_surface.get_rect()
        self.window_rect.center = (width // 2, height // 2)
        self.content_rect = self.window_rect.inflate(
            -self.CONTENT_MARGIN * 2, -self.CONTENT_MARGIN * 2
        )
        self.previous_button.set_position(
            (
                self.window_rect.left + 40,
                self.window_rect.bottom - self.previous_button.rect.height - 40,
            )
        )
        self.current_button.set_position(
            (
                self.window_rect.right - self.current_button.rect.width - 40,
                self.window_rect.bottom - self.current_button.rect.height - 40,
            )
        )
        self.close_button.set_position(
            (
                self.window_rect.right - self.close_button.rect.width - 20,
                self.window_rect.top + 20,
            )
        )
        self.set_entry(self._current_entry)

    def _refresh_text_positions(self) -> None:
        base_x = self.content_rect.left
        base_y = self.content_rect.top
        if self._current_entry is not None:
            definition = self._current_entry.definition
            base_x += definition.x_offset
            base_y += definition.y_offset
        self._title_pos.xy = (base_x, base_y)
        body_top = (
            base_y
            + (self._title_surface.get_height() if self._title_surface else 0)
            + 24
        )
        self._body_pos.xy = (base_x, body_top)

    def set_entry(self, entry: Optional[TriggeredNotification]) -> None:
        self._current_entry = entry
        if entry is None:
            self._title_surface = None
            self._body_surface = self._empty_text_surface
            self._refresh_text_positions()
            return

        definition = entry.definition
        title_font = self._font(definition.title_font_size)
        body_font = self._font(definition.body_font_size)
        self._title_surface = title_font.render(
            definition.title, True, definition.text_color
        )
        wrap_width = max(50, min(definition.wrap_width, self.content_rect.width))
        self._body_surface = self._render_body(
            definition.body, body_font, definition.text_color, wrap_width
        )
        self._refresh_text_positions()

    def _render_body(
        self,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        wrap_width: int,
    ) -> pygame.Surface:
        lines = self._wrap_text(text, font, wrap_width)
        line_height = font.get_linesize()
        height = line_height * len(lines)
        surface = pygame.Surface((wrap_width, height), pygame.SRCALPHA)
        y = 0
        for line in lines:
            rendered = font.render(line, True, color)
            surface.blit(rendered, (0, y))
            y += line_height
        return surface

    def _wrap_text(
        self, text: str, font: pygame.font.Font, wrap_width: int
    ) -> list[str]:
        lines: list[str] = []
        current = ""
        for paragraph in text.splitlines() or [text]:
            for word in paragraph.split(" "):
                candidate = (current + " " + word).strip()
                if not candidate:
                    continue
                width, _ = font.size(candidate)
                if width <= wrap_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
                current = ""
            lines.append("")  # Paragraph break
        if lines and lines[-1] == "":
            lines.pop()
        if not lines:
            lines.append("")
        return lines

    def handle_event(self, event) -> AchievementScreenResult:
        if not self.is_visible():
            return AchievementScreenResult.NONE
        if self.previous_button.handle_event(event):
            return AchievementScreenResult.PREVIOUS
        if self.current_button.handle_event(event):
            return AchievementScreenResult.CURRENT
        if self.close_button.handle_event(event):
            return AchievementScreenResult.CLOSE
        return AchievementScreenResult.NONE

    def update(self, dt: float) -> None:
        if not self.is_visible():
            return
        self.previous_button.update(dt)
        self.current_button.update(dt)
        self.close_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_visible():
            return
        surface.blit(self.window_surface, self.window_rect)
        if self._title_surface is not None:
            surface.blit(self._title_surface, self._title_pos)
        if self._body_surface is not None:
            surface.blit(self._body_surface, self._body_pos)
        self.previous_button.draw(surface)
        self.current_button.draw(surface)
        self.close_button.draw(surface)


__all__ = ["AchievementScreen", "AchievementScreenResult"]
