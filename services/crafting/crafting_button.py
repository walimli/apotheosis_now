from __future__ import annotations

from typing import Tuple

import pygame

from services.notifications.ui.button import ImageButton
from .crafting_assets import CraftingAssets


class CraftingButton(ImageButton):
    """Bottom-right persistent button that toggles the crafting UI."""

    def __init__(
        self,
        assets: CraftingAssets,
        margin: Tuple[int, int] = (16, 16),
    ) -> None:
        super().__init__(assets.crafting_button_images)
        self._margin = margin

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        """Place the button along the bottom-right edge using margins."""
        width, height = surface_size
        button_width, button_height = self.rect.size
        x = width - button_width - self._margin[0]
        y = height - button_height - self._margin[1]
        self.set_position((x, y))

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)


__all__ = ["CraftingButton"]
