"""Shared resources exposed to input adapters."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PlayInputContext:
    hotbar_ui: Optional[Any] = None
    inventory: Optional[Any] = None
    camera: Optional[Any] = None
    crafting_system: Optional[Any] = None
    inventory_lock: Optional[Any] = None
    dialogue_manager: Optional[Any] = None
    display: Optional[Any] = None
