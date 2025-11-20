"""Mutable snapshot of play input state for a single frame."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .actions import PlayAction


@dataclass
class ButtonState:
    pressed: bool = False
    held: bool = False
    released: bool = False


@dataclass
class PlayInputState:
    frame_id: int = 0
    cursor_pos: Tuple[int, int] = (0, 0)
    cursor_delta: Tuple[int, int] = (0, 0)
    cursor_screen_pos: Tuple[int, int] = (0, 0)
    cursor_screen_delta: Tuple[int, int] = (0, 0)
    scroll_delta: int = 0
    axes: Dict[PlayAction, Tuple[float, float]] = field(default_factory=dict)
    buttons: Dict[PlayAction, ButtonState] = field(default_factory=dict)
    hotbar_scroll: int = 0
    hotbar_select: Optional[int] = None

    def reset_transients(self) -> None:
        self.cursor_delta = (0, 0)
        self.cursor_screen_delta = (0, 0)
        self.scroll_delta = 0
        self.hotbar_scroll = 0
        self.hotbar_select = None
        for button in self.buttons.values():
            button.pressed = False
            button.released = False

    def ensure_button(self, action: PlayAction) -> ButtonState:
        state = self.buttons.get(action)
        if state is None:
            state = ButtonState()
            self.buttons[action] = state
        return state

    def set_button_pressed(self, action: PlayAction, down: bool) -> None:
        state = self.ensure_button(action)
        if down:
            if not state.held:
                state.pressed = True
                state.held = True
        else:
            if state.held:
                state.released = True
            state.held = False

    def accumulate_axis(self, action: PlayAction, dx: float, dy: float) -> None:
        x, y = self.axes.get(action, (0.0, 0.0))
        self.axes[action] = (x + dx, y + dy)

    def get_axis(self, action: PlayAction) -> Tuple[float, float]:
        return self.axes.get(action, (0.0, 0.0))

    def clear_all(self) -> None:
        """Reset axes/buttons so stale input does not persist across state changes."""
        self.axes.clear()
        self.buttons.clear()
        self.scroll_delta = 0
        self.hotbar_scroll = 0
        self.hotbar_select = None
        self.cursor_delta = (0, 0)
        self.cursor_screen_delta = (0, 0)
