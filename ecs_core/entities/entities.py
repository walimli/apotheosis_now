# systems/ecs/entities.py
from __future__ import annotations
from typing import NewType

Entity = NewType("Entity", int)


class EntityManager:
    def __init__(self):
        self._next_id = 0

    def create(self) -> Entity:
        eid = Entity(self._next_id)
        self._next_id += 1
        return eid
