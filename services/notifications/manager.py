"""Runtime notification manager."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .catalog import NotificationCatalog
from .history import NotificationHistory, TriggeredNotification


class NotificationManager:
    """Coordinates definition loading and history tracking."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.catalog = NotificationCatalog(data_root)
        self.history = NotificationHistory()

    def reload(self) -> None:
        """Reload definitions from disk."""
        self.catalog.reload()

    def trigger(self, trigger: str, payload: Optional[Dict[str, Any]] = None) -> List[TriggeredNotification]:
        """Fire all notifications bound to a trigger."""
        try:
            definitions = self.catalog.get_by_trigger(trigger)
        except KeyError:
            return []
        timestamp = time.time()
        fired: List[TriggeredNotification] = []
        for definition in definitions:
            entry = TriggeredNotification(definition=definition, triggered_at=timestamp, payload=payload)
            self.history.append(entry)
            fired.append(entry)
        return fired

    def current(self) -> Optional[TriggeredNotification]:
        """Return the currently selected entry."""
        return self.history.current()

    def latest(self) -> Optional[TriggeredNotification]:
        """Return the newest entry and select it."""
        return self.history.latest()

    def previous(self) -> Optional[TriggeredNotification]:
        """Step to the previous entry, if any."""
        return self.history.previous()

    def serialize_history(self) -> List[Dict[str, Any]]:
        """Return history for persistence."""
        return self.history.records()

    def load_history(self, records: Iterable[Dict[str, Any]]) -> None:
        """Restore history from persisted data."""
        entries: List[TriggeredNotification] = []
        for record in records:
            if "id" not in record or "triggered_at" not in record:
                raise ValueError("History record missing required fields")
            definition = self.catalog.get_definition(str(record["id"]))
            triggered_at = float(record["triggered_at"])
            payload = record.get("payload")
            entries.append(TriggeredNotification(definition, triggered_at, payload))
        self.history.set_entries(entries)

    def clear_history(self) -> None:
        """Remove all history entries."""
        self.history.set_entries([])


__all__ = ["NotificationManager", "TriggeredNotification"]
