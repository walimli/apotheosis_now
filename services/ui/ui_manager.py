"""HUD/UI manager responsible for drawing overlays for the play state."""

from __future__ import annotations

from typing import Optional

import pygame

from services.time import GameTimeOverlay, TimeManager
from services.display.display_system import DisplayService


class UIManager:
    """Render HUD overlays delegated from game states."""

    def __init__(
        self,
        display: DisplayService,
        *,
        font_path: str,
        time_manager: Optional[TimeManager] = None,
        time_overlay_label: str = "Game Time",
        time_overlay_pos: tuple[int, int] = (30, 30),
        use_12_hour: bool = True,
    ) -> None:
        self._display = display
        self._font_path = font_path
        self._pause_font_size = 16
        self._cached_pause_font: Optional[pygame.font.Font] = None
        self._time_overlay: Optional[GameTimeOverlay] = None
        if time_manager is not None:
            self._time_overlay = GameTimeOverlay(
                clock=time_manager.clock,
                label=time_overlay_label,
                pos=time_overlay_pos,
                use_12_hour=use_12_hour,
            )

    def render_play_hud(self, screen: pygame.Surface, *, paused: bool = False) -> None:
        """Render HUD elements for the play state."""
        if self._time_overlay is not None:
            self._time_overlay.draw(screen)
        if paused:
            pause_font = self._get_pause_font()
            pause_surface = pause_font.render("PAUSED", True, (255, 255, 0))
            text_rect = pause_surface.get_rect(center=screen.get_rect().center)
            screen.blit(pause_surface, text_rect)

    def _get_pause_font(self) -> pygame.font.Font:
        if self._cached_pause_font is None:
            self._cached_pause_font = self._display.get_scaled_font(
                self._font_path,
                self._pause_font_size,
            )
        return self._cached_pause_font
