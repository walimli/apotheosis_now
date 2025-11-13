"""Stats viewer screen for player progression."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

import pygame

from services.progression import Progression
from services.asset_loader.notification_assets import ButtonImages, NotificationUIAssets
from ..button import ImageButton
from .base import JournalScreen


class StatsScreenResult(Enum):
    NONE = "none"
    CLOSE = "close"


class StatsScreen(JournalScreen):
    """Displays a read-only snapshot of the player's progression stats."""

    TITLE_COLOR = (255, 255, 255)
    LABEL_COLOR = (255, 255, 255)
    VALUE_COLOR = (200, 230, 255)
    TITLE_FONT_SIZE = 42
    ROW_FONT_SIZE = 28
    COLUMN_SPACING = 220
    ROW_SPACING = 14
    TOP_PADDING = 48
    COLUMN_TOP_OFFSET = 130
    EMERALD_TOP_OFFSET = 320

    LEFT_KEYS = ("might", "speed", "health")
    RIGHT_KEYS = ("formula", "fortune", "octopus")
    LABELS = {
        "might": "Might",
        "speed": "Speed",
        "health": "Health",
        "formula": "Formulas",
        "fortune": "Fortune",
        "octopus": "Octopus",
        "emeralds": "Emeralds",
    }

    def __init__(self, assets: NotificationUIAssets) -> None:
        super().__init__(assets)
        self._font_path = str(assets.font_path())
        self.background = assets.panel_surface
        self.background_rect = self.background.get_rect()
        self._surface_size: Tuple[int, int] = (
            self.background_rect.width,
            self.background_rect.height,
        )

        self.title_font = pygame.font.Font(self._font_path, self.TITLE_FONT_SIZE)
        self.row_font = pygame.font.Font(self._font_path, self.ROW_FONT_SIZE)
        self.title_surface = self.title_font.render("Stats", True, self.TITLE_COLOR)
        self.title_rect = self.title_surface.get_rect()

        self.close_button = self._make_close_button()

        self._values: Dict[str, str] = {
            key: "Current Level" for key in self.LEFT_KEYS + self.RIGHT_KEYS
        }
        self._values["emeralds"] = "Current Number"
        self._left_rows: list[
            Tuple[pygame.Surface, pygame.Surface, pygame.Rect, pygame.Rect]
        ] = []
        self._right_rows: list[
            Tuple[pygame.Surface, pygame.Surface, pygame.Rect, pygame.Rect]
        ] = []
        self._emerald_row: (
            Tuple[pygame.Surface, pygame.Surface, pygame.Rect, pygame.Rect] | None
        ) = None

        self._progression: Optional[Progression] = None
        self._last_snapshot: Dict[str, str] = {}

        self._rebuild_rows()
        self.reposition(self._surface_size)

    def _make_close_button(self) -> ImageButton:
        base = self.assets.exit_icon
        hover = self._apply_tint(base, add=50)
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

    def attach_progression(self, progression: Progression) -> None:
        self._progression = progression
        self.refresh()

    def refresh(self) -> None:
        self._refresh_from_progression()

    def _refresh_from_progression(self) -> None:
        if self._progression is None:
            return
        snapshot = {
            "might": str(self._progression.get_upgrade_level("might")),
            "speed": str(self._progression.get_upgrade_level("speed")),
            "health": str(self._progression.get_upgrade_level("health")),
            "formula": str(self._progression.get_upgrade_level("formula")),
            "fortune": str(self._progression.get_upgrade_level("fortune")),
            "octopus": str(self._progression.get_upgrade_level("octopus")),
            "emeralds": str(self._progression.emeralds),
        }
        if snapshot != self._last_snapshot:
            self._last_snapshot = snapshot
            self.set_display_values(snapshot)

    def set_display_values(self, values: Dict[str, str]) -> None:
        self._values.update(values)
        self._rebuild_rows()
        self.reposition(self._surface_size)

    def _rebuild_rows(self) -> None:
        self._left_rows.clear()
        self._right_rows.clear()
        for column, keys in (
            (self._left_rows, self.LEFT_KEYS),
            (self._right_rows, self.RIGHT_KEYS),
        ):
            for key in keys:
                label_surface = self.row_font.render(
                    f"{self.LABELS[key]}:", True, self.LABEL_COLOR
                )
                value_surface = self.row_font.render(
                    str(self._values.get(key, "")), True, self.VALUE_COLOR
                )
                column.append(
                    (
                        label_surface,
                        value_surface,
                        label_surface.get_rect(),
                        value_surface.get_rect(),
                    )
                )
        emerald_label = self.row_font.render(
            f"{self.LABELS['emeralds']}:", True, self.LABEL_COLOR
        )
        emerald_value = self.row_font.render(
            str(self._values.get("emeralds", "")), True, self.VALUE_COLOR
        )
        self._emerald_row = (
            emerald_label,
            emerald_value,
            emerald_label.get_rect(),
            emerald_value.get_rect(),
        )

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        self._surface_size = surface_size
        width, height = surface_size
        rect = self.background.get_rect()
        rect.left = 0
        rect.centery = height // 2
        rect.clamp_ip(pygame.Rect(0, 0, width, height))
        self.background_rect = rect

        self.title_rect.centerx = rect.centerx
        self.title_rect.top = rect.top + self.TOP_PADDING

        column_x = rect.centerx - self.COLUMN_SPACING // 2
        column_y = rect.top + self.COLUMN_TOP_OFFSET
        for index, (label, value, label_rect, value_rect) in enumerate(self._left_rows):
            y = column_y + index * (label_rect.height + self.ROW_SPACING)
            label_rect.topright = (column_x - 20, y)
            value_rect.topleft = (column_x, y)

        right_column_x = rect.centerx + self.COLUMN_SPACING // 2
        for index, (label, value, label_rect, value_rect) in enumerate(
            self._right_rows
        ):
            y = column_y + index * (label_rect.height + self.ROW_SPACING)
            label_rect.topright = (right_column_x - 20, y)
            value_rect.topleft = (right_column_x, y)

        if self._emerald_row is not None:
            label_surface, value_surface, label_rect, value_rect = self._emerald_row
            emerald_y = rect.top + self.EMERALD_TOP_OFFSET
            label_rect.topright = (rect.centerx - 20, emerald_y)
            value_rect.topleft = (rect.centerx, emerald_y)

        self.close_button.set_position(
            (rect.right - self.close_button.rect.width - 20, rect.top + 20)
        )

    def handle_event(self, event) -> StatsScreenResult:
        if not self.is_visible():
            return StatsScreenResult.NONE
        if self.close_button.handle_event(event):
            return StatsScreenResult.CLOSE
        return StatsScreenResult.NONE

    def update(self, dt: float) -> None:
        if not self.is_visible():
            return
        self.close_button.update(dt)
        if self._progression is not None:
            self._refresh_from_progression()

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_visible():
            return
        surface.blit(self.background, self.background_rect)
        surface.blit(self.title_surface, self.title_rect)
        for label, value, label_rect, value_rect in self._left_rows:
            surface.blit(label, label_rect)
            surface.blit(value, value_rect)
        for label, value, label_rect, value_rect in self._right_rows:
            surface.blit(label, label_rect)
            surface.blit(value, value_rect)
        if self._emerald_row is not None:
            label, value, label_rect, value_rect = self._emerald_row
            surface.blit(label, label_rect)
            surface.blit(value, value_rect)
        self.close_button.draw(surface)


__all__ = ["StatsScreen", "StatsScreenResult"]
