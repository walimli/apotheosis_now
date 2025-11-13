"""Journal side panel and supporting UI."""

from __future__ import annotations

from enum import Enum
from typing import List, Tuple

import pygame

from services.asset_loader.notification_assets import ButtonImages, NotificationUIAssets
from .button import ImageButton


class JournalPanelResult(Enum):
    NONE = "none"
    STATS = "stats"
    FORMULAS = "formulas"
    NOTIFICATIONS = "notifications"
    ACHIEVEMENTS = "achievements"


class PanelButton(ImageButton):
    """Panel button with text overlay."""

    TEXT_COLOR = (255, 255, 255)

    def __init__(
        self, label: str, font: pygame.font.Font, images: ButtonImages
    ) -> None:
        self.label = label
        rendered = ButtonImages(
            normal=self._render_label(images.normal, font),
            hover=self._render_label(images.hover, font),
            pressed=self._render_label(images.pressed, font),
        )
        super().__init__(rendered)

    def _render_label(
        self, base: pygame.Surface, font: pygame.font.Font
    ) -> pygame.Surface:
        surface = base.copy()
        text = font.render(self.label, True, self.TEXT_COLOR)
        text_rect = text.get_rect(
            center=(surface.get_width() // 2, surface.get_height() // 2)
        )
        surface.blit(text, text_rect)
        return surface


class JournalPanel:
    """Handles the journal side panel UI."""

    TITLE_COLOR = (255, 255, 255)
    TITLE_SIZE = 42
    BUTTON_SIZE = 28
    BUTTON_SPACING = 20
    TOP_PADDING = 48
    BUTTON_START_OFFSET = 130

    def __init__(self, assets: NotificationUIAssets) -> None:
        self.assets = assets
        self.visible = False
        self.panel_surface = assets.panel_surface
        font_path = assets.font_path()
        self.title_font = pygame.font.Font(str(font_path), self.TITLE_SIZE)
        self.button_font = pygame.font.Font(str(font_path), self.BUTTON_SIZE)
        self.title_surface = self.title_font.render("Journal", True, self.TITLE_COLOR)
        self.title_rect = self.title_surface.get_rect()
        self.panel_rect = self.panel_surface.get_rect()
        self.buttons: List[PanelButton] = []
        self._button_results: dict[PanelButton, JournalPanelResult] = {}
        self._build_buttons()
        self.reposition((self.panel_rect.width, self.panel_rect.height))

    def _build_buttons(self) -> None:
        labels = [
            ("Stats", JournalPanelResult.STATS),
            ("Formulas", JournalPanelResult.FORMULAS),
            ("Notifications", JournalPanelResult.NOTIFICATIONS),
            ("Achievements", JournalPanelResult.ACHIEVEMENTS),
        ]
        self.buttons.clear()
        self._button_results.clear()
        for label, result in labels:
            btn = PanelButton(label, self.button_font, self.assets.panel_button_images)
            self.buttons.append(btn)
            self._button_results[btn] = result

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        """Align panel and its contents against the left edge."""
        width, height = surface_size
        panel = self.panel_surface.get_rect()
        panel.left = 0
        panel.centery = height // 2
        if panel.top < 0:
            panel.top = 0
        if panel.bottom > height:
            panel.bottom = height
        self.panel_rect = panel
        self.title_rect.centerx = panel.centerx
        self.title_rect.top = panel.top + self.TOP_PADDING
        start_y = panel.top + self.BUTTON_START_OFFSET
        for index, button in enumerate(self.buttons):
            button_height = button.rect.height
            y = start_y + index * (button_height + self.BUTTON_SPACING)
            button.set_position((panel.centerx - button.rect.width // 2, y))

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def toggle(self) -> None:
        self.visible = not self.visible

    def handle_event(self, event) -> JournalPanelResult:
        if not self.visible:
            return JournalPanelResult.NONE
        for button in self.buttons:
            if button.handle_event(event):
                return self._button_results.get(button, JournalPanelResult.NONE)
        return JournalPanelResult.NONE

    def update(self, dt: float) -> None:
        if not self.visible:
            return
        for button in self.buttons:
            button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        surface.blit(self.panel_surface, self.panel_rect)
        surface.blit(self.title_surface, self.title_rect)
        for button in self.buttons:
            button.draw(surface)


__all__ = ["JournalPanel", "JournalPanelResult"]
