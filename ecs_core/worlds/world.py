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
        self._entity_index: Dict[Entity, set[Type]] = {}

    # --- Component CRUD -------------------------------------------------
    def add(self, entity: Entity, component: Any) -> None:
        ctype = type(component)
        store = self._storage.setdefault(ctype, {})
        store[entity] = component
        self._entities.add(entity)
        self._entity_index.setdefault(entity, set()).add(ctype)

    def remove(self, entity: Entity, ctype: Type[C]) -> None:
        store = self._storage.get(ctype)
        if store and entity in store:
            del store[entity]
            if not store:
                self._storage.pop(ctype, None)
            tracked = self._entity_index.get(entity)
            if tracked and ctype in tracked:
                tracked.discard(ctype)
            if tracked and not tracked:
                self._entity_index.pop(entity, None)
                self._entities.discard(entity)

    def get(self, entity: Entity, ctype: Type[C]) -> C | None:
        store = self._storage.get(ctype)
        return store.get(entity) if store else None

    def destroy_entity(self, entity: Entity) -> None:
        """Remove an entity and all of its components from the world."""
        if entity not in self._entities:
            return
        for ctype in list(self._entity_index.get(entity, ())):
            store = self._storage.get(ctype)
            if store and entity in store:
                del store[entity]
                if not store:
                    self._storage.pop(ctype, None)
        self._entity_index.pop(entity, None)
        self._entities.discard(entity)

    def has_entity(self, entity: Entity) -> bool:
        return entity in self._entities

    def get_component(self, *args):
        """
        Compatibility helper:
        - get_component(entity, ComponentType) -> Component instance or None
        - get_component(ComponentType) -> iterator of (entity, component)
        """
        if len(args) == 2:
            entity, ctype = args
            return self.get(entity, ctype)
        if len(args) == 1:
            (ctype,) = args
            store = self._storage.get(ctype, {})
            return store.items()
        raise TypeError("get_component expects (entity, type) or (type)")

    def get_components(self, *ctypes: Type) -> Iterator[Tuple[Entity, Tuple[Any, ...]]]:
        for entity, *components in self.view(*ctypes):
            yield entity, tuple(components)

    def create_entity_from_template(self, template_id: int):
        raise NotImplementedError(
            "World.create_entity_from_template is not implemented for this build."
        )

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
        self._entity_index.clear()
