from __future__ import annotations

from typing import Callable, Optional
from systems.time_manager_package.time_events import TimeEvent, TimePhase


class SoulCosts:
    """Centralized, easily tunable soul economy knobs."""

    # Base activity drains; tweak to rebalance.
    HEARTBEAT: int = 1
    LANDSCAPE_HARVEST: int = 1
    LANDSCAPE_PLACE: int = 1
    FARMING_HARVEST: int = 1
    COMBAT_ATTACK: int = 1

    # Default crafting drain per craft when recipes omit an override.
    CRAFTING_DEFAULT: int = 1


class Soul:
    """Player soul (fatigue) component."""

    def __init__(self, max_soul: int, *, on_changed: Optional[Callable[[], None]] = None) -> None:
        max_value = int(max(0, max_soul))
        self.max_soul: int = max_value
        self.current_soul: int = max_value
        self._on_changed: Optional[Callable[[], None]] = on_changed
        self._depleted_emitted = False

    def set_on_changed(self, callback: Optional[Callable[[], None]]) -> None:
        self._on_changed = callback

    def set_max(self, max_soul: int) -> None:
        self.max_soul = int(max(0, max_soul))
        if self.current_soul > self.max_soul:
            self.current_soul = self.max_soul
        if self.max_soul == 0:
            self.current_soul = 0
        self._maybe_reset_depleted_flag()
        self._emit_changed()

    def restore_full(self) -> None:
        if self.current_soul == self.max_soul:
            return
        self.current_soul = self.max_soul
        self._maybe_reset_depleted_flag()
        self._emit_changed()

    def restore(self, amount: int) -> int:
        if amount <= 0:
            return 0
        before = self.current_soul
        self.current_soul = min(self.max_soul, self.current_soul + int(amount))
        gained = self.current_soul - before
        if gained > 0:
            self._maybe_reset_depleted_flag()
            self._emit_changed()
        return gained

    def can_spend(self, amount: int) -> bool:
        if amount <= 0:
            return True
        return self.current_soul >= int(amount) and self.max_soul > 0

    def consume(self, amount: int) -> bool:
        spend = int(amount)
        if spend <= 0:
            return True
        if not self.can_spend(spend):
            self._emit_depleted()
            return False
        self.current_soul -= spend
        if self.current_soul < 0:
            self.current_soul = 0
        if self.current_soul == 0:
            self._emit_depleted()
        else:
            self._maybe_reset_depleted_flag(clear_only=True)
        self._emit_changed()
        return True

    def is_depleted(self) -> bool:
        return self.current_soul <= 0

    def to_dict(self) -> dict:
        return {
            "cur": int(self.current_soul),
            "max": int(self.max_soul),
        }

    def load_from_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise TypeError("Soul.load_from_dict expects dict")
        cur = int(data.get("cur", 0))
        max_soul = int(data.get("max", 0))
        self.max_soul = max(0, max_soul)
        self.current_soul = max(0, min(cur, self.max_soul))
        self._maybe_reset_depleted_flag()
        self._emit_changed()

    def _emit_changed(self) -> None:
        if self._on_changed is not None:
            try:
                self._on_changed()
            except Exception:
                pass

    def _emit_depleted(self) -> None:
        if not self._depleted_emitted:
            print("[Soul] Player is exhausted: no soul remaining.")
            self._depleted_emitted = True

    def _maybe_reset_depleted_flag(self, *, clear_only: bool = False) -> None:
        if self.current_soul > 0:
            self._depleted_emitted = False
        elif not clear_only and self.current_soul == 0:
            self._depleted_emitted = True

    def announce_blocked(self) -> None:
        """Surface the depleted message without modifying state."""
        self._emit_depleted()


def should_drain_on_heartbeat(event: TimeEvent, *, in_safe_zone: bool = False) -> bool:
    """Determine if the heartbeat should drain soul for the given event."""
    if in_safe_zone:
        return False
    if event is None:
        return True
    phase = getattr(event, "phase", None)
    if phase is None:
        return bool(getattr(event, "is_day", True))
    if isinstance(phase, TimePhase):
        return phase is TimePhase.DAY
    try:
        coerced = TimePhase(str(phase))
    except Exception:
        return bool(getattr(event, "is_day", True))
    return coerced is TimePhase.DAY


__all__ = ["Soul", "SoulCosts", "should_drain_on_heartbeat"]
