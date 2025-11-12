"""Core void damage manager."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Collection, Optional


TileLookup = Callable[[float, float], Optional[int]]
DamageCallback = Callable[[int], None]


@dataclass
class VoidConfig:
    damage_amount: int = 1
    damage_interval: float = 1.0
    void_tiles: Collection[int] = (0,)

    def __post_init__(self) -> None:
        if self.damage_amount <= 0:
            raise ValueError("damage_amount must be positive")
        if self.damage_interval <= 0:
            raise ValueError("damage_interval must be positive")
        if not self.void_tiles:
            raise ValueError("void_tiles must contain at least one tile id")


class VoidManager:
    """Accumulates time spent on void tiles and applies periodic damage."""

    def __init__(self, tile_lookup: TileLookup, damage_callback: DamageCallback, config: VoidConfig) -> None:
        if not callable(tile_lookup):
            raise TypeError("tile_lookup must be callable")
        if not callable(damage_callback):
            raise TypeError("damage_callback must be callable")
        self._tile_lookup = tile_lookup
        self._damage_callback = damage_callback
        self._config = config
        self._enabled = True
        self._accumulator = 0.0

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if not self._enabled:
            self._accumulator = 0.0

    def update(self, dt: float, world_x: float, world_y: float) -> None:
        if not self._enabled:
            return
        if dt <= 0:
            return

        tile_id = self._tile_lookup(world_x, world_y)
        if tile_id not in self._config.void_tiles:
            self._accumulator = 0.0
            return

        self._accumulator += dt
        while self._accumulator >= self._config.damage_interval:
            self._accumulator -= self._config.damage_interval
            self._damage_callback(self._config.damage_amount)


__all__ = ["VoidManager", "VoidConfig", "TileLookup", "DamageCallback"]
