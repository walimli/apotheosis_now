"""Lightweight adapter that routes cursor input to the targeting system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import pygame

from .actions import PlayAction
from .adapters import BaseInputAdapter
from .state import PlayInputState

RouteInputFn = Callable[[Any, pygame.event.Event], None]


@dataclass
class TargetingInputAdapter(BaseInputAdapter):
    play_state: Any
    route_input: RouteInputFn

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_move)
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_primary_click)
        self.bus.subscribe(PlayAction.VARIANT_CYCLE, self._on_secondary_click)

    def _on_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action == PlayAction.CURSOR_MOVE:
            self._route_event(pygame.MOUSEMOTION, state)

    def _on_primary_click(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if button and button.pressed:
            self._route_event(pygame.MOUSEBUTTONDOWN, state, button_id=1)

    def _on_secondary_click(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.VARIANT_CYCLE:
            return
        button = state.buttons.get(PlayAction.VARIANT_CYCLE)
        if button and button.pressed:
            self._route_event(pygame.MOUSEBUTTONDOWN, state, button_id=3)

    def _route_event(
        self,
        event_type: int,
        state: PlayInputState,
        *,
        button_id: Optional[int] = None,
    ) -> None:
        if self.dialogue_active():
            return
        event = self._make_event(event_type, state, button_id=button_id)
        if event is None:
            return
        try:
            self.route_input(self.play_state, event)
        except Exception:
            pass

    @staticmethod
    def _make_event(
        event_type: int,
        state: PlayInputState,
        *,
        button_id: Optional[int] = None,
    ) -> Optional[pygame.event.Event]:
        pos = TargetingInputAdapter._coerce_pos(state.cursor_pos)
        if pos is None:
            return None
        payload = {"pos": pos}
        if button_id is not None:
            payload["button"] = button_id
        try:
            return pygame.event.Event(event_type, payload)
        except Exception:
            return None

    @staticmethod
    def _coerce_pos(pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        if pos is None:
            return None
        x, y = pos
        return (int(x), int(y))


__all__ = ["TargetingInputAdapter"]
