"""Adapters related to inventory, hotbar, and crafting interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import pygame

from .actions import PlayAction
from .state import PlayInputState
from .adapters import BaseInputAdapter


@dataclass
class CraftingInputAdapter(BaseInputAdapter):
    system: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)
        self.bus.subscribe(PlayAction.VARIANT_CYCLE, self._on_variant_cycle)
        self.bus.subscribe(PlayAction.CRAFT_TOGGLE, self._on_toggle_action)

    def _system(self) -> Any:
        sys = self.system
        if sys is None and self.context is not None:
            sys = getattr(self.context, "crafting_system", None)
        return sys

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE:
            return
        system = self._system()
        if system is not None:
            system.handle_cursor_move(self._base_cursor_pos(state))
        self._update_button_hover(state)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        system = self._system()
        if system is None:
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if button and button.pressed:
            if self._handle_button_click(state, mouse_button=1, system=system):
                return
            system.handle_primary_action(self._base_cursor_pos(state))

    def _on_variant_cycle(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.VARIANT_CYCLE:
            return
        system = self._system()
        if system is None or not getattr(system, "active", False):
            return
        button = state.buttons.get(PlayAction.VARIANT_CYCLE)
        if button and button.pressed:
            system.handle_secondary_action(self._base_cursor_pos(state))

    def _on_toggle_action(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CRAFT_TOGGLE:
            return
        system = self._system()
        if system is None:
            return
        button = state.buttons.get(PlayAction.CRAFT_TOGGLE)
        if button and button.pressed:
            system.toggle()

    def _display_size(self) -> Optional[Tuple[int, int]]:
        display = getattr(self.context, "display", None)
        if display is None:
            return None
        width = getattr(display, "screen_width", None)
        height = getattr(display, "screen_height", None)
        if width is None or height is None:
            return None
        return (int(width), int(height))

    def _button(self):
        system = self._system()
        if system is None:
            return None
        return getattr(system, "button", None)

    def _update_button_hover(self, state: PlayInputState) -> None:
        button = self._button()
        surface_size = self._display_size()
        pos = getattr(state, "cursor_screen_pos", None)
        if button is None or surface_size is None or pos is None:
            return
        button.reposition(surface_size)
        event = pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos})
        try:
            button.handle_event(event)
        except Exception:
            pass

    def _handle_button_click(
        self,
        state: PlayInputState,
        mouse_button: int,
        *,
        system: Any | None = None,
    ) -> bool:
        button = self._button()
        surface_size = self._display_size()
        pos = getattr(state, "cursor_screen_pos", None)
        system = system or self._system()
        if (
            button is None
            or surface_size is None
            or pos is None
            or system is None
            or mouse_button != 1
        ):
            return False
        button.reposition(surface_size)
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": mouse_button}
        )
        try:
            handled = button.handle_event(event)
        except Exception:
            handled = False
        if handled:
            system.toggle()
        return handled

    def _base_cursor_pos(self, state: PlayInputState) -> Optional[Tuple[int, int]]:
        pos = getattr(state, "cursor_screen_pos", None)
        return self._map_screen_to_base(pos)

    def _map_screen_to_base(
        self, pos: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        if pos is None:
            return None
        display = getattr(self.context, "display", None)
        if display is None:
            return pos
        try:
            scale, off_x, off_y = display.get_present_params()
        except Exception:
            scale, off_x, off_y = 1, 0, 0
        denom = max(1, int(scale))
        bx = int((pos[0] - off_x) // denom)
        by = int((pos[1] - off_y) // denom)
        return (bx, by)


@dataclass
class HotbarInputAdapter(BaseInputAdapter):
    inventory: Any
    hotbar_ui: Any | None = None

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.HOTBAR_SCROLL, self._on_scroll)
        self.bus.subscribe(PlayAction.HOTBAR_SELECT, self._on_select)
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_primary_click)
        self.bus.subscribe(PlayAction.VARIANT_CYCLE, self._on_secondary_click)

    def _on_scroll(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.HOTBAR_SCROLL:
            return
        delta = state.hotbar_scroll
        if delta == 0:
            return
        slots = len(getattr(self.inventory, "slots", []))
        if slots <= 0:
            return
        current = int(self.inventory.get_selected_index())
        new_index = (current - delta) % slots
        self.inventory.set_selected_index(new_index)

    def _on_select(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.HOTBAR_SELECT:
            return
        index = state.hotbar_select
        if index is None:
            return
        slots = len(getattr(self.inventory, "slots", []))
        if slots <= 0:
            return
        if 0 <= index < slots:
            self.inventory.set_selected_index(index)

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE:
            return
        hotbar = self.hotbar_ui
        pos = getattr(state, "cursor_screen_pos", None)
        hotbar_origin = self._hotbar_origin()
        if hotbar is None or pos is None or hotbar_origin is None:
            return
        hotbar.handle_mouse_motion(pos, *hotbar_origin)

    def _on_primary_click(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if not (button and button.pressed):
            return
        self._handle_pointer_click(state, mouse_button=1)

    def _on_secondary_click(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.VARIANT_CYCLE:
            return
        button = state.buttons.get(PlayAction.VARIANT_CYCLE)
        if not (button and button.pressed):
            return
        self._handle_pointer_click(state, mouse_button=3)

    def _display_size(self) -> Optional[Tuple[int, int]]:
        display = getattr(self.context, "display", None)
        if display is None:
            return None
        width = getattr(display, "screen_width", None)
        height = getattr(display, "screen_height", None)
        if width is None or height is None:
            return None
        return (int(width), int(height))

    def _hotbar_origin(self) -> Optional[Tuple[int, int]]:
        hotbar = self.hotbar_ui
        surface = self._display_size()
        if hotbar is None or surface is None:
            return None
        width, height = surface
        try:
            return hotbar.get_position(width, height)
        except Exception:
            return None

    def _handle_pointer_click(self, state: PlayInputState, mouse_button: int) -> None:
        hotbar = self.hotbar_ui
        pos = getattr(state, "cursor_screen_pos", None)
        origin = self._hotbar_origin()
        if hotbar is None or pos is None or origin is None:
            return
        try:
            hotbar.handle_mouse_button(pos, mouse_button, *origin)
        except Exception:
            pass


__all__ = [
    "CraftingInputAdapter",
    "HotbarInputAdapter",
]
