"""Base classes for journal screens."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

import pygame

from services.asset_loader.notification_assets import NotificationUIAssets


class JournalScreen(ABC):
    """Common interface for journal sub-screens."""

    def __init__(self, assets: NotificationUIAssets) -> None:
        self.assets = assets
        self._visible = False

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def toggle(self) -> None:
        self._visible = not self._visible

    def is_visible(self) -> bool:
        return self._visible

    @abstractmethod
    def reposition(self, surface_size: Tuple[int, int]) -> None:
        """Adjust layout for the given surface size."""

    @abstractmethod
    def handle_event(self, event) -> object:
        """Process a pygame event and return a screen-specific result."""

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update internal timers/animations."""

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Render the screen to the supplied surface."""


__all__ = ["JournalScreen"]
