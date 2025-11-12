from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .worlds.world import World


class System(ABC):
    def __init__(self, world: "World"):
        self.world = world

    @abstractmethod
    def update(self, dt: float) -> None:
        pass
