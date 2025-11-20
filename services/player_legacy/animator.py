from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import pygame

from .anim_state import AnimState
from .image_loader import load_sequence
from .state_map import (
    DEFAULT_FRAME_TIME,
    STATE_DIRECTION,
    STATE_FILES,
    STATE_FRAME_TIME,
    STATE_LOOPING,
)

_MOVEMENT_EPSILON = 0.01
_RIGHT_FACING = {"right", "down_right", "up_right"}
_DIRECTION_SUFFIXES = tuple(sorted(set(STATE_DIRECTION.values()), key=len, reverse=True))


class PlayerAnimator:
    def __init__(self) -> None:
        self.states: Dict[str, AnimState] = {}
        self._load_states()

        self.current_name: str = "idle_down" if "idle_down" in self.states else next(iter(self.states))
        self.last_facing: str = "down"
        self._last_direction: str = "down"
        self._base_action: str = "idle"
        self._equipped_variant: Optional[str] = None

        self._last_pos: Optional[Tuple[float, float]] = None
        self.pos: Optional[Tuple[float, float]] = None
        self._action_name: Optional[str] = None

        self._mirror_cache: Dict[pygame.Surface, pygame.Surface] = {}

    def _load_states(self) -> None:
        for name, resource in STATE_FILES.items():
            frames = load_sequence(resource)
            frame_time = STATE_FRAME_TIME.get(name, DEFAULT_FRAME_TIME)
            loop = STATE_LOOPING.get(name, True)
            self.states[name] = AnimState(frames, frame_time=frame_time, loop=loop)

    def set_position(self, pos_xy: Tuple[float, float]) -> None:
        self.pos = pos_xy

    def set_pick_equipped(self, equipped: bool) -> None:
        """Legacy helper retained for compatibility."""
        self.set_equipped_variant("pick" if equipped else None)

    def set_equipped_variant(self, variant: Optional[str]) -> None:
        normalized = variant or None
        if normalized == self._equipped_variant:
            return
        self._equipped_variant = normalized
        if self._action_name is None:
            state_name = self._resolve_state(
                f"{self._base_action}_{self._last_direction}",
                prefer_variant=self._equipped_variant,
            )
            if state_name and state_name != self.current_name:
                self.current_name = state_name
                self.states[state_name].reset()

    def trigger_action(self, name: str) -> None:
        """Trigger a one-shot animation override."""
        resolved = self._resolve_state(name)
        if not resolved:
            return
        self._action_name = resolved
        self.current_name = resolved
        self.states[resolved].reset()

    def update(self, dt: float) -> None:
        if self.pos is None:
            return
        if self._last_pos is None:
            self._last_pos = self.pos

        lx, ly = self._last_pos
        x, y = self.pos
        dx, dy = (x - lx), (y - ly)
        self._last_pos = (x, y)

        if self._action_name:
            state = self.states.get(self._action_name)
            if state is None:
                self._action_name = None
            else:
                state.update(dt)
                self.current_name = self._action_name
                if state.is_finished:
                    self._action_name = None
                    base_state = self._resolve_state(f"{self._base_action}_{self._last_direction}")
                    if base_state:
                        self.current_name = base_state
                        self.states[base_state].reset()
                return

        moving = abs(dx) > _MOVEMENT_EPSILON or abs(dy) > _MOVEMENT_EPSILON
        direction = self._direction_from_motion(dx, dy)
        self._last_direction = direction

        cardinal = self._cardinal_from_vector(dx, dy)
        if cardinal:
            self.last_facing = cardinal

        self._base_action = "walk" if moving else "idle"
        state_name = self._resolve_state(
            f"{self._base_action}_{direction}",
            prefer_variant=self._equipped_variant,
        )
        if not state_name:
            return

        if state_name != self.current_name:
            self.current_name = state_name
            self.states[state_name].reset()

        self.states[state_name].update(dt)

    def current_surface_and_offset(self) -> Tuple[pygame.Surface, Tuple[int, int]]:
        state = self.states.get(self.current_name)
        if state is None:
            raise RuntimeError(f"Animator state '{self.current_name}' is not loaded")
        frame = state.current()

        direction = STATE_DIRECTION.get(self.current_name, self._last_direction)
        if direction in _RIGHT_FACING:
            frame = self._mirrored_frame(frame)

        return frame, (0, 0)

    def _mirrored_frame(self, surface: pygame.Surface) -> pygame.Surface:
        cached = self._mirror_cache.get(surface)
        if cached is None:
            cached = pygame.transform.flip(surface, True, False)
            self._mirror_cache[surface] = cached
        return cached

    def _resolve_state(
        self,
        name: str,
        *,
        prefer_variant: Optional[str] = None,
    ) -> Optional[str]:
        explicit_variant: Optional[str] = None
        base = name
        for suffix in ("_pick", "_sword"):
            if base.endswith(suffix):
                explicit_variant = suffix[1:]
                base = base[: -len(suffix)]
                break

        if explicit_variant is not None:
            candidate = f"{base}_{explicit_variant}"
            if candidate in self.states:
                return candidate
        elif prefer_variant is None and name in self.states:
            return name

        action, direction = self._split_action_direction(base)
        if direction is None:
            return None

        variant = explicit_variant if explicit_variant is not None else prefer_variant
        return self._resolve_components(action, direction, variant)

    def _resolve_components(
        self,
        action: str,
        direction: str,
        variant: Optional[str],
    ) -> Optional[str]:
        base_name = f"{action}_{direction}"
        candidates = []
        if variant:
            candidates.append(f"{base_name}_{variant}")
        candidates.append(base_name)

        for candidate in candidates:
            if candidate in self.states:
                return candidate
        return None

    @staticmethod
    def _split_action_direction(name: str) -> Tuple[str, Optional[str]]:
        for suffix in _DIRECTION_SUFFIXES:
            marker = f"_{suffix}"
            if name.endswith(marker):
                action = name[: -len(marker)]
                return action, suffix
        return name, None

    def _direction_from_motion(self, dx: float, dy: float) -> str:
        if abs(dx) <= _MOVEMENT_EPSILON and abs(dy) <= _MOVEMENT_EPSILON:
            return self._last_direction

        angle = math.degrees(math.atan2(-dy, dx))
        if -22.5 <= angle < 22.5:
            return "right"
        if 22.5 <= angle < 67.5:
            return "up_right"
        if 67.5 <= angle < 112.5:
            return "up"
        if 112.5 <= angle < 157.5:
            return "up_left"
        if angle >= 157.5 or angle < -157.5:
            return "left"
        if -157.5 <= angle < -112.5:
            return "down_left"
        if -112.5 <= angle < -67.5:
            return "down"
        return "down_right"

    def _cardinal_from_vector(self, dx: float, dy: float) -> Optional[str]:
        if abs(dx) <= _MOVEMENT_EPSILON and abs(dy) <= _MOVEMENT_EPSILON:
            return None
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        return "down" if dy >= 0 else "up"

