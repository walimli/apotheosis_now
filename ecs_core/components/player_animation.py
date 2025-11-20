from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlayerAnimationHandle:
    """Component that links an entity to the legacy player animation service."""

    service: Any
