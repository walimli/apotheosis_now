from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WispModel:
    id: int
    species_id: str
    x: float
    y: float
    hp_max: int
    hp_cur: int
    speed_px_s: float
    facing: str = "down"
    is_dead: bool = False
    is_moving: bool = False

