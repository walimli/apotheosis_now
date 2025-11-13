"""HUD/UI manager responsible for drawing overlays for the play state."""

from __future__ import annotations

from typing import Any, Optional

import pygame

from services.time import GameTimeOverlay, TimeManager
from services.display.display_system import DisplayService
from .ui_orchestrator import (
    UIComponents,
    bootstrap_ui,
    draw_hud_screen,
    update_ui,
)


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
        self._play_state: Any | None = None
        self._ui_components: UIComponents | None = None
        if time_manager is not None:
            self._time_overlay = GameTimeOverlay(
                clock=time_manager.clock,
                label=time_overlay_label,
                pos=time_overlay_pos,
                use_12_hour=use_12_hour,
            )

    def attach_play_state(
        self,
        play_state: Any,
        *,
        player: Any | None = None,
        lock_state: Any | None = None,
    ) -> None:
        """Bind orchestrated UI components to the given play state."""
        if play_state is None:
            raise ValueError("play_state is required for UI attachment")
        self._play_state = play_state
        player_obj = player or getattr(play_state, "player", None)
        if player_obj is None:
            self._ui_components = None
            setattr(play_state, "ui", None)
            return
        lock = lock_state or getattr(player_obj, "lock_state", None)
        self._ui_components = bootstrap_ui(player_obj, self._display, lock)
        play_state.ui = self._ui_components
        update_ui(play_state)

    def render_play_hud(
        self,
        screen: pygame.Surface,
        *,
        paused: bool = False,
        play_state: Any | None = None,
    ) -> None:
        """Render HUD elements for the play state."""
        ps = self._ensure_play_state(play_state)
        if ps is not None and self._ui_components is not None:
            draw_hud_screen(ps, screen)
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

    def _ensure_play_state(self, play_state: Any | None) -> Any | None:
        if play_state is not None:
            if self._play_state is not play_state:
                self._play_state = play_state
        return self._play_state
