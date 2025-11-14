"""Registry for evolvable entity templates backed by JSON metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Optional

from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World

SpawnFactory = Callable[[World, EntityManager], Entity]


class EvolvableEntityRegistry:
    """Tracks evolvable entity IDs and resolves them into spawn factories."""

    def __init__(self, metadata_path: Optional[Path] = None):
        project_root = Path(__file__).resolve().parents[3]
        default_path = project_root / "data" / "entities" / "evolve_registry.json"
        self._metadata_path = metadata_path or default_path
        self._metadata: Dict[str, Dict[str, str]] = self._load_metadata()
        self._factories: Dict[str, SpawnFactory] = {}

    def _load_metadata(self) -> Dict[str, Dict[str, str]]:
        if not self._metadata_path.exists():
            return {}
        try:
            raw = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        if isinstance(raw, dict):
            entries = raw.get("entities", [])
        elif isinstance(raw, list):
            entries = raw
        else:
            entries = []

        metadata: Dict[str, Dict[str, str]] = {}
        for entry in entries:
            entry_id = entry.get("id") if isinstance(entry, dict) else None
            if not entry_id:
                continue
            metadata[entry_id] = {
                "display_name": entry.get("display_name", entry_id),
                "description": entry.get("description", entry_id),
            }
        return metadata

    def register_factory(self, entity_id: str, factory: SpawnFactory) -> None:
        """Register a callable that can spawn the requested entity."""

        if entity_id not in self._metadata:
            raise KeyError(f"Unknown entity id '{entity_id}' in evolve registry")
        self._factories[entity_id] = factory

    def spawn(
        self,
        entity_id: str,
        world: World,
        entity_manager: EntityManager,
    ) -> Entity:
        """Instantiate the requested entity via its registered factory."""

        factory = self._factories.get(entity_id)
        if factory is None:
            raise KeyError(f"No factory registered for entity id '{entity_id}'")
        return factory(world, entity_manager)

    def has_entity(self, entity_id: str) -> bool:
        return entity_id in self._metadata

    def describe(self, entity_id: str) -> Optional[Dict[str, str]]:
        return self._metadata.get(entity_id)


evolvable_registry = EvolvableEntityRegistry()

__all__ = ["evolvable_registry", "EvolvableEntityRegistry"]
