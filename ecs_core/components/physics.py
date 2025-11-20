"""Physics-related components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Friction:
    """Applies drag to velocity over time."""

    drag: float = 0.1  # Remaining velocity multiplier per second (e.g., 0.1 = 90% loss/sec)
    min_velocity: float = 5.0  # Threshold below which velocity snaps to zero