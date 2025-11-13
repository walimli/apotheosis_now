"""Notification history tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .definitions import NotificationDefinition


@dataclass
class TriggeredNotification:
    """Single fired notification instance."""

    definition: NotificationDefinition
    triggered_at: float
    payload: Optional[Dict[str, Any]] = None

    def to_record(self) -> Dict[str, Any]:
        """Convert to a serializable mapping."""
        record = {
            "id": self.definition.id,
            "triggered_at": self.triggered_at,
        }
        if self.payload is not None:
            record["payload"] = self.payload
        return record


class NotificationHistory:
    """Maintains ordered notification instances with a cursor."""

    def __init__(self) -> None:
        self._entries: List[TriggeredNotification] = []
        self._cursor: Optional[int] = None

    def append(self, entry: TriggeredNotification) -> None:
        """Add an entry and focus it."""
        self._entries.append(entry)
        self._cursor = len(self._entries) - 1

    def set_entries(self, entries: List[TriggeredNotification]) -> None:
        """Replace existing entries and position cursor at newest."""
        self._entries = list(entries)
        self._cursor = len(self._entries) - 1 if self._entries else None

    def current(self) -> Optional[TriggeredNotification]:
        """Return the entry at the cursor."""
        if self._cursor is None:
            return None
        return self._entries[self._cursor]

    def latest(self) -> Optional[TriggeredNotification]:
        """Return newest entry and move cursor there."""
        if not self._entries:
            self._cursor = None
            return None
        self._cursor = len(self._entries) - 1
        return self._entries[self._cursor]

    def previous(self) -> Optional[TriggeredNotification]:
        """Move cursor to older entry and return it."""
        if self._cursor is None:
            return None
        if self._cursor == 0:
            return self._entries[0]
        self._cursor -= 1
        return self._entries[self._cursor]

    def records(self) -> List[Dict[str, Any]]:
        """Return a list of serializable records."""
        return [entry.to_record() for entry in self._entries]

    def is_empty(self) -> bool:
        """Whether the history is empty."""
        return not self._entries


__all__ = ["TriggeredNotification", "NotificationHistory"]
