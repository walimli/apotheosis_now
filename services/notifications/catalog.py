"""Notification definition catalog."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from .definitions import NotificationDefinition


class NotificationCatalog:
    """Loads notification definitions and provides lookups."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self._by_id: Dict[str, NotificationDefinition] = {}
        self._by_trigger: Dict[str, List[NotificationDefinition]] = defaultdict(list)
        self.reload()

    def reload(self) -> None:
        """Reload all JSON definitions from disk."""
        if not self.data_root.exists():
            raise FileNotFoundError(f"Notification data directory missing: {self.data_root}")
        self._by_id.clear()
        self._by_trigger.clear()
        for path in sorted(self.data_root.glob("*.json")):
            definition = NotificationDefinition.from_path(path)
            if definition.id in self._by_id:
                raise ValueError(f"Duplicate notification id: {definition.id}")
            self._by_id[definition.id] = definition
            self._by_trigger[definition.trigger].append(definition)

    def all_definitions(self) -> Iterable[NotificationDefinition]:
        """Return all loaded definitions."""
        return self._by_id.values()

    def get_definition(self, definition_id: str) -> NotificationDefinition:
        """Return a definition by id."""
        try:
            return self._by_id[definition_id]
        except KeyError as exc:
            raise KeyError(f"Unknown notification id: {definition_id}") from exc

    def get_by_trigger(self, trigger: str) -> List[NotificationDefinition]:
        """Return all definitions bound to a trigger name."""
        if trigger not in self._by_trigger:
            raise KeyError(f"No notifications registered for trigger: {trigger}")
        return list(self._by_trigger[trigger])


__all__ = ["NotificationCatalog"]
