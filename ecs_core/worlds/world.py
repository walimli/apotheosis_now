# systems/ecs_core/worlds/world.py
from __future__ import annotations
from typing import Type, TypeVar, Dict, Iterator, Tuple, List, Any
from ..entities.entities import Entity

C = TypeVar("C")


class World:
    def __init__(self):
        # {ComponentType: {Entity: Component}}
        self._storage: Dict[Type, Dict[Entity, Any]] = {}
        self._entities: set[Entity] = set()

    # --- Component CRUD -------------------------------------------------
    def add(self, entity: Entity, component: Any) -> None:
        ctype = type(component)
        store = self._storage.setdefault(ctype, {})
        store[entity] = component
        self._entities.add(entity)

    def remove(self, entity: Entity, ctype: Type[C]) -> None:
        store = self._storage.get(ctype)
        if store and entity in store:
            del store[entity]
            if not store:
                self._storage.pop(ctype, None)
            if entity not in {e for s in self._storage.values() for e in s}:
                self._entities.discard(entity)

    def get(self, entity: Entity, ctype: Type[C]) -> C | None:
        store = self._storage.get(ctype)
        return store.get(entity) if store else None

    # --- Queries --------------------------------------------------------
    def view(self, *ctypes: Type) -> Iterator[Tuple[Entity, ...]]:
        """Yield (entity, comp1, comp2, ...) for entities with ALL ctypes"""
        if not ctypes:
            return
        # Pick smallest storage for speed
        primary = min((self._storage.get(t, {}) for t in ctypes), key=len)
        for entity in primary:
            if all(entity in self._storage.get(t, {}) for t in ctypes):
                yield (entity, *(self._storage[t][entity] for t in ctypes))

    def entities_with(self, *ctypes: Type) -> List[Entity]:
        return [e for e, *_ in self.view(*ctypes)]

    # --- Debug ----------------------------------------------------------
    def clear(self):
        self._storage.clear()
        self._entities.clear()
