"""Registry for evolvable entity templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Optional

from ecs_core.entities.entities import Entity, EntityManager
from ecs_core.worlds.world import World

SpawnFactory = Callable[[World, EntityManager], Entity]


class EvolvableEntityRegistry:
    """Tracks evolvable entity IDs and resolves them into spawn factories."""

    def __init__(self, metadata_path: Optional[Path] = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        default_path = project_root / "data" / "entities" / "monster_manual.json"
        self._metadata_path = metadata_path or default_path
        self._metadata: Dict[str, Dict[str, str]] = {}
        self._metadata.update(self._load_metadata_file(self._metadata_path))
        self._merge_additional_metadata(project_root / "data" / "entities" / "attacks.json")
        self._factories: Dict[str, SpawnFactory] = {}

    def _load_metadata_file(self, path: Path) -> Dict[str, Dict[str, str]]:
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        entries = raw.get("entities", []) if isinstance(raw, dict) else raw
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

    def _merge_additional_metadata(self, path: Path) -> None:
        extra = self._load_metadata_file(path)
        for key, value in extra.items():
            self._metadata.setdefault(key, value)

    def register_factory(self, entity_id: str, factory: SpawnFactory) -> None:
        if entity_id not in self._metadata:
            # Keep fallback metadata so code-defined entities remain usable.
            self._metadata[entity_id] = {
                "display_name": entity_id,
                "description": entity_id,
            }
        self._factories[entity_id] = factory

    def spawn(
        self,
        entity_id: str,
        world: World,
        entity_manager: EntityManager,
    ) -> Entity:
        factory = self._factories.get(entity_id)
        if factory is None:
            raise KeyError(f"No factory registered for entity id '{entity_id}'")
        return factory(world, entity_manager)

    def has_entity(self, entity_id: str) -> bool:
        return entity_id in self._metadata

    def describe(self, entity_id: str) -> Optional[Dict[str, str]]:
        return self._metadata.get(entity_id)


evolvable_registry = EvolvableEntityRegistry()

__all__ = ["EvolvableEntityRegistry", "evolvable_registry"]
