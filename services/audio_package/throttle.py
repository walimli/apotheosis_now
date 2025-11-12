from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EventThrottle:
    """Track last-play timestamps and enforce cooldowns for audio events."""

    cooldowns: Dict[str, float]
    _last_played: Dict[str, float] = field(default_factory=dict)

    def allow(self, event_key: str) -> bool:
        cooldown = self.cooldowns.get(event_key)
        if cooldown is None:
            return True
        now = time.monotonic()
        last = self._last_played.get(event_key)
        if last is not None and (now - last) < cooldown:
            return False
        self._last_played[event_key] = now
        return True

    def reset(self, event_key: str) -> None:
        self._last_played.pop(event_key, None)

    def clear(self) -> None:
        self._last_played.clear()


__all__ = ["EventThrottle"]
