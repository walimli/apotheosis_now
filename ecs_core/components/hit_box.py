from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class HitBox:
    """Marker component for entities that expose their collider as a hover outline."""

    color: Tuple[int, int, int] = (255, 0, 0)
    line_width: int = 2
