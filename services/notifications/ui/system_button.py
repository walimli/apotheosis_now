"""System button that summons the journal panel."""

from __future__ import annotations

from typing import Tuple

import pygame

from services.asset_loader.notification_assets import NotificationUIAssets
from .button import ImageButton


class SystemButton(ImageButton):
    """Persistent bottom-left button to open the system journal."""

    def __init__(
        self, assets: NotificationUIAssets, margin: Tuple[int, int] = (16, 16)
    ) -> None:
        super().__init__(assets.system_button_images)
        self._margin = margin

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        """Place the button using the configured margins."""
        width, height = surface_size
        button_width, button_height = self.rect.size
        x = self._margin[0]
        y = height - button_height - self._margin[1]
        self.set_position((x, y))

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)


__all__ = ["SystemButton"]
