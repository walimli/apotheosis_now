"""Procedural rune animation manager for the title background."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np
import pygame
from noise import pnoise3

from services.asset_loader.title_runes import load_rune_triplets

CELL_SIZE = 16
_LIFETIME = 1.0

_FRAME_PHASES: Sequence[float] = (0.0, 0.36, 0.7, 0.92, 1.0)

_NOISE_SPATIAL_SCALE = 0.07
_NOISE_TIME_SCALE = 0.23
_NOISE_OCTAVES = 2
_NOISE_PERSISTENCE = 0.55
_NOISE_LACUNARITY = 2.05
_NOISE_REPEAT = 512
_NOISE_AMPLITUDE = 0.85

_ACTIVITY_DECAY = 1.8
_ACTIVITY_INJECT = 0.95
_DIFFUSE_FACTOR = 0.28

_SCORE_NOISE_WEIGHT = 0.72
_SCORE_ACTIVITY_WEIGHT = 0.48
_SPAWN_THRESHOLD = 0.48
_COOLDOWN_RANGE = (0.8, 2.4)
_MAX_SPAWNS_PER_TICK = 5


@dataclass(slots=True)
class RuneInstance:
    frames: Tuple[pygame.Surface, pygame.Surface, pygame.Surface]
    position: Tuple[int, int]
    row: int
    col: int
    fade_surface: pygame.Surface
    elapsed: float = 0.0
    duration: float = _LIFETIME

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed < self.duration

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.elapsed / self.duration
        if progress < _FRAME_PHASES[1]:
            surface.blit(self.frames[0], self.position)
            return
        if progress < _FRAME_PHASES[2]:
            surface.blit(self.frames[1], self.position)
            return
        if progress < _FRAME_PHASES[3]:
            surface.blit(self.frames[2], self.position)
            return
        if progress < _FRAME_PHASES[4]:
            fade_window = _FRAME_PHASES[4] - _FRAME_PHASES[3]
            fade_progress = (progress - _FRAME_PHASES[3]) / fade_window
            alpha = max(0, min(255, int(255 * (1.0 - fade_progress))))
            self.fade_surface.set_alpha(alpha)
            surface.blit(self.fade_surface, self.position)


class RuneField:
    """Manage rune sprites that bloom procedurally across the title background."""

    def __init__(self, display) -> None:
        self._display = display
        self._triplets = load_rune_triplets()
        self._rng = random.Random()
        self._array_rng = np.random.default_rng()
        self._noise_origin = (
            self._rng.uniform(0.0, 4096.0),
            self._rng.uniform(0.0, 4096.0),
            self._rng.uniform(0.0, 4096.0),
        )
        self._active: List[RuneInstance] = []
        self._time = 0.0
        self._size: Tuple[int, int] | None = None
        self._grid_shape: Tuple[int, int] = (0, 0)
        self._positions: List[Tuple[int, int]] = []

        self._cooldown = np.zeros((0, 0), dtype=np.float32)
        self._activity = np.zeros((0, 0), dtype=np.float32)
        self._active_mask = np.zeros((0, 0), dtype=bool)
        self._noise_field = np.zeros((0, 0), dtype=np.float32)
        self._smoothed_activity = np.zeros((0, 0), dtype=np.float32)
        self._scores = np.zeros((0, 0), dtype=np.float32)
        self._last_scores = np.zeros((0, 0), dtype=np.float32)
        self._noise_x = np.zeros((0,), dtype=np.float32)
        self._noise_y = np.zeros((0,), dtype=np.float32)

    def update(self, dt: float) -> None:
        if not self._triplets:
            return
        base_surface = self._display.get_base_surface()
        size = base_surface.get_size()
        if self._size != size:
            self._rebuild_grid(size)
        rows, cols = self._grid_shape
        if rows == 0 or cols == 0:
            return
        self._time += dt
        self._update_active(dt)
        self._advance_fields(dt)
        self._spawn_from_scores()
        self._last_scores[...] = self._scores

    def draw(self, surface: pygame.Surface) -> None:
        for rune in self._active:
            rune.draw(surface)

    def _rebuild_grid(self, size: Tuple[int, int]) -> None:
        self._size = size
        cols = size[0] // CELL_SIZE
        rows = size[1] // CELL_SIZE
        self._active.clear()
        if cols <= 0 or rows <= 0:
            self._grid_shape = (0, 0)
            self._positions = []
            self._cooldown = np.zeros((0, 0), dtype=np.float32)
            self._activity = np.zeros((0, 0), dtype=np.float32)
            self._active_mask = np.zeros((0, 0), dtype=bool)
            self._noise_field = np.zeros((0, 0), dtype=np.float32)
            self._smoothed_activity = np.zeros((0, 0), dtype=np.float32)
            self._scores = np.zeros((0, 0), dtype=np.float32)
            self._last_scores = np.zeros((0, 0), dtype=np.float32)
            self._noise_x = np.zeros((0,), dtype=np.float32)
            self._noise_y = np.zeros((0,), dtype=np.float32)
            return

        self._grid_shape = (rows, cols)
        self._positions = [
            (col * CELL_SIZE, row * CELL_SIZE)
            for row in range(rows)
            for col in range(cols)
        ]
        self._cooldown = self._array_rng.uniform(
            _COOLDOWN_RANGE[0], _COOLDOWN_RANGE[1], size=self._grid_shape
        ).astype(np.float32)
        self._activity = np.zeros(self._grid_shape, dtype=np.float32)
        self._active_mask = np.zeros(self._grid_shape, dtype=bool)
        self._noise_field = np.zeros(self._grid_shape, dtype=np.float32)
        self._smoothed_activity = np.zeros(self._grid_shape, dtype=np.float32)
        self._scores = np.zeros(self._grid_shape, dtype=np.float32)
        self._last_scores = np.zeros(self._grid_shape, dtype=np.float32)
        self._noise_x = np.arange(cols, dtype=np.float32) * _NOISE_SPATIAL_SCALE
        self._noise_y = np.arange(rows, dtype=np.float32) * _NOISE_SPATIAL_SCALE

    def _update_active(self, dt: float) -> None:
        if not self._active:
            return
        alive: List[RuneInstance] = []
        for rune in self._active:
            if rune.update(dt):
                alive.append(rune)
                continue
            row, col = rune.row, rune.col
            self._active_mask[row, col] = False
            self._cooldown[row, col] = self._rng.uniform(*_COOLDOWN_RANGE)
        self._active = alive

    def _advance_fields(self, dt: float) -> None:
        np.subtract(self._cooldown, dt, out=self._cooldown)
        np.maximum(self._cooldown, 0.0, out=self._cooldown)

        decay = math.exp(-_ACTIVITY_DECAY * dt)
        self._activity *= decay
        smoothed = self._diffuse_activity()

        z = self._time * _NOISE_TIME_SCALE
        rows, cols = self._grid_shape
        x_offset, y_offset, z_offset = self._noise_origin
        z = z_offset + self._time * _NOISE_TIME_SCALE
        for row in range(rows):
            y_coord = float(self._noise_y[row]) + y_offset
            noise_row = self._noise_field[row]
            for col in range(cols):
                noise_value = pnoise3(
                    float(self._noise_x[col]) + x_offset,
                    y_coord,
                    z,
                    octaves=_NOISE_OCTAVES,
                    persistence=_NOISE_PERSISTENCE,
                    lacunarity=_NOISE_LACUNARITY,
                    repeatx=_NOISE_REPEAT,
                    repeaty=_NOISE_REPEAT,
                )
                noise_row[col] = max(
                    0.0, min(1.0, 0.5 + noise_value * _NOISE_AMPLITUDE)
                )

        np.multiply(self._noise_field, _SCORE_NOISE_WEIGHT, out=self._scores)
        self._scores += _SCORE_ACTIVITY_WEIGHT * smoothed

    def _diffuse_activity(self) -> np.ndarray:
        rows, cols = self._grid_shape
        if rows == 0 or cols == 0:
            return self._smoothed_activity
        padded = np.pad(self._activity, 1, mode="constant")
        center = padded[1:-1, 1:-1]
        neighbors = (
            padded[:-2, 1:-1]
            + padded[2:, 1:-1]
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
            + padded[:-2, :-2]
            + padded[:-2, 2:]
            + padded[2:, :-2]
            + padded[2:, 2:]
        )
        avg_neighbors = neighbors / 8.0
        np.multiply(center, (1.0 - _DIFFUSE_FACTOR), out=self._smoothed_activity)
        self._smoothed_activity += _DIFFUSE_FACTOR * avg_neighbors
        return self._smoothed_activity

    def _spawn_from_scores(self) -> None:
        rows, cols = self._grid_shape
        if rows == 0 or cols == 0:
            return
        eligible_mask = (
            (self._scores >= _SPAWN_THRESHOLD)
            & (self._last_scores < _SPAWN_THRESHOLD)
            & (self._cooldown <= 0.0)
            & (~self._active_mask)
        )
        candidates = np.argwhere(eligible_mask)
        if candidates.size == 0:
            return
        self._array_rng.shuffle(candidates)
        spawn_count = 0
        for row, col in candidates:
            if spawn_count >= _MAX_SPAWNS_PER_TICK:
                break
            self._activate_cell(int(row), int(col))
            spawn_count += 1

    def _activate_cell(self, row: int, col: int) -> None:
        index = row * self._grid_shape[1] + col
        triplet = self._rng.choice(self._triplets)
        fade_surface = triplet[2].copy()
        rune = RuneInstance(
            frames=triplet,
            position=self._positions[index],
            row=row,
            col=col,
            fade_surface=fade_surface,
        )
        self._active.append(rune)
        self._active_mask[row, col] = True
        self._activity[row, col] = max(self._activity[row, col], _ACTIVITY_INJECT)
        self._last_scores[row, col] = 0.0
        self._cooldown[row, col] = 0.0
