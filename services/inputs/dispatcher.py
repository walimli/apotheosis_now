"""Input dispatcher that bridges pygame events to play actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pygame

from .actions import PlayAction
from .bindings import DEFAULT_BINDINGS, InputBinding, build_trigger_lookup
from .state import PlayInputState

Subscriber = Callable[[PlayAction, PlayInputState], None]
OnCapturedCallback = Callable[[PlayAction, InputBinding], None]


@dataclass
class RebindContext:
    """State for an active rebinding capture."""

    action: PlayAction
    index: int
    on_captured: OnCapturedCallback | None = None


@dataclass
class PlayInputBus:
    """Central routing object for play-state input events."""

    state: PlayInputState = field(default_factory=PlayInputState)
    bindings: Dict[PlayAction, Tuple[InputBinding, ...]] = field(
        default_factory=lambda: dict(DEFAULT_BINDINGS)
    )
    subscribers: Dict[PlayAction, List[Subscriber]] = field(default_factory=dict)
    _trigger_lookup: Dict[Tuple[str, int], List[InputBinding]] = field(
        init=False, default_factory=dict
    )
    _axis_sources: Dict[Tuple[PlayAction, Tuple[str, int]], Tuple[float, float]] = field(
        init=False, default_factory=dict
    )
    _rebind_context: Optional[RebindContext] = field(
        init=False, default=None, repr=False
    )

    def __post_init__(self) -> None:
        self._rebuild_lookup()

    def _rebuild_lookup(self) -> None:
        self._trigger_lookup = build_trigger_lookup(self.bindings)

    def process(self, events: Iterable[pygame.event.Event]) -> None:
        self.state.frame_id += 1
        self.state.reset_transients()
        for event in events:
            if self._rebind_context:
                captured = self._capture_rebind(event)
                if captured:
                    continue

            if event.type == pygame.KEYDOWN:
                if getattr(event, "repeat", False):
                    continue
                self._handle_key(event.key, True)
            elif event.type == pygame.KEYUP:
                self._handle_key(event.key, False)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_button(event, True)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_button(event, False)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._handle_mouse_wheel(event)

        # Keep axes normalized each frame
        for action in {binding.action for binding in self._axis_binding_iter()}:
            self._update_axis(action)

    def replace_bindings(
        self,
        new_bindings: Dict[PlayAction, Tuple[InputBinding, ...]]
    ) -> None:
        """Atomically replace all bindings and rebuild the lookup."""
        self.bindings = new_bindings
        self._rebuild_lookup()

    def begin_rebind(
        self,
        action: PlayAction,
        index: int,
        on_captured: OnCapturedCallback | None = None,
    ) -> None:
        """Start listening for the next input to replace a binding."""
        self._rebind_context = RebindContext(
            action=action, index=index, on_captured=on_captured
        )

    def cancel_rebind(self) -> None:
        """Cancel an active rebinding."""
        self._rebind_context = None

    def _capture_rebind(self, event: pygame.event.Event) -> bool:
        if not self._rebind_context:
            return False

        new_binding: InputBinding | None = None
        action = self._rebind_context.action
        value = None

        if event.type == pygame.KEYDOWN:
            # For now, axis actions are not rebindable at runtime.
            # This could be expanded by checking action type.
            new_binding = InputBinding(action, ("key", event.key), value)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            new_binding = InputBinding(action, ("mouse_button", event.button), value)
        elif event.type == pygame.MOUSEWHEEL:
            direction = 1 if event.y > 0 else -1
            new_binding = InputBinding(action, ("mouse_wheel", direction), value)

        if new_binding:
            # Update the bindings list for this action
            action_bindings = list(self.bindings.get(action, []))
            if 0 <= self._rebind_context.index < len(action_bindings):
                action_bindings[self._rebind_context.index] = new_binding
            else:
                action_bindings.append(new_binding)

            # Create a new top-level bindings dict and replace atomically
            new_bindings = self.bindings.copy()
            new_bindings[action] = tuple(action_bindings)
            self.replace_bindings(new_bindings)

            # Signal completion and clean up
            if self._rebind_context.on_captured:
                self._rebind_context.on_captured(action, new_binding)
            self._rebind_context = None
            return True
        return False

    def _axis_binding_iter(self):
        for trigger, bindings in self._trigger_lookup.items():
            if trigger[0] == "key_axis":
                yield from bindings
        return []

    def emit(self, action: PlayAction) -> None:
        callbacks = self.subscribers.get(action)
        if not callbacks:
            return
        for callback in callbacks:
            callback(action, self.state)

    def subscribe(self, action: PlayAction, callback: Subscriber) -> None:
        callbacks = self.subscribers.setdefault(action, [])
        if callback not in callbacks:
            callbacks.append(callback)

    def get_movement_input(self) -> Tuple[float, float]:
        """Expose the MOVE axis without requiring systems to read state internals."""
        return self.state.get_axis(PlayAction.MOVE)

    def _handle_key(self, key: int, down: bool) -> None:
        for binding in self._trigger_lookup.get(("key", key), []):
            if binding.action == PlayAction.HOTBAR_SELECT:
                if down:
                    index = int(binding.value or 0)
                    self.state.hotbar_select = index
                    self.emit(binding.action)
                continue
            self.state.set_button_pressed(binding.action, down)
            self.emit(binding.action)

        axis_bindings = self._trigger_lookup.get(("key_axis", key), [])
        if axis_bindings:
            for binding in axis_bindings:
                trigger_key = ("key_axis", key)
                self._set_axis_source(binding.action, trigger_key, binding.value, down)

        # Additional key-based triggers (if defined later) can be handled here.

    def _handle_mouse_button(self, event: pygame.event.Event, down: bool) -> None:
        button = int(getattr(event, "button", 0))
        if button in (4, 5):
            # Wheel up/down are routed via pygame.MOUSEWHEEL; skip click handling.
            return
        pos = getattr(event, "pos", None)
        screen_pos = getattr(event, "screen_pos", pos)
        if pos is not None:
            prev_x, prev_y = self.state.cursor_pos
            x, y = int(pos[0]), int(pos[1])
            self.state.cursor_delta = (x - prev_x, y - prev_y)
            self.state.cursor_pos = (x, y)
            self.emit(PlayAction.CURSOR_MOVE)
        if screen_pos is not None:
            prev_sx, prev_sy = self.state.cursor_screen_pos
            sx, sy = int(screen_pos[0]), int(screen_pos[1])
            self.state.cursor_screen_delta = (sx - prev_sx, sy - prev_sy)
            self.state.cursor_screen_pos = (sx, sy)
        for binding in self._trigger_lookup.get(("mouse_button", button), []):
            self.state.set_button_pressed(binding.action, down)
            self.emit(binding.action)

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        prev_x, prev_y = self.state.cursor_pos
        new_pos = getattr(event, "pos", (prev_x, prev_y))
        self.state.cursor_pos = new_pos
        rel = getattr(event, "rel", (0, 0))
        self.state.cursor_delta = rel
        screen_pos_raw = getattr(event, "screen_pos", new_pos)
        sx, sy = int(screen_pos_raw[0]), int(screen_pos_raw[1])
        self.state.cursor_screen_pos = (sx, sy)
        screen_rel_raw = getattr(event, "screen_rel", rel)
        self.state.cursor_screen_delta = (
            int(screen_rel_raw[0]),
            int(screen_rel_raw[1]),
        )
        self.emit(PlayAction.CURSOR_MOVE)

    def _handle_mouse_wheel(self, event: pygame.event.Event) -> None:
        y = getattr(event, "y", 0)
        if y == 0:
            return
        direction = 1 if y > 0 else -1
        self.state.scroll_delta += y
        trigger = ("mouse_wheel", direction)
        for binding in self._trigger_lookup.get(trigger, []):
            if binding.action == PlayAction.HOTBAR_SCROLL:
                delta = int(binding.value or direction)
                self.state.hotbar_scroll = delta
                self.emit(binding.action)
                self.state.hotbar_scroll = 0
            else:
                self.state.scroll_delta += int(binding.value or 0)
                self.emit(binding.action)

    def _set_axis_source(
        self,
        action: PlayAction,
        trigger: Tuple[str, int],
        value: Tuple[float, float] | None,
        active: bool,
    ) -> None:
        if not isinstance(value, tuple):
            value = (0.0, 0.0)
        key = (action, trigger)
        if active:
            self._axis_sources[key] = value
        else:
            self._axis_sources.pop(key, None)
        self._update_axis(action)

    def _update_axis(self, action: PlayAction) -> None:
        x = 0.0
        y = 0.0
        for (act, _trigger), (dx, dy) in self._axis_sources.items():
            if act == action:
                x += dx
                y += dy
        length_sq = x * x + y * y
        if length_sq > 1.0:
            length = length_sq ** 0.5
            if length > 0:
                x /= length
                y /= length
        self.state.axes[action] = (x, y)
        self.emit(action)
