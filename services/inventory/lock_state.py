"""Toggleable state for locking hotbar interactions."""

from __future__ import annotations

from typing import Callable, List


class InventoryLockState:
    """Tracks whether hotbar interactions should only select slots."""

    def __init__(self) -> None:
        self._enabled = False
        self._listeners: List[Callable[[bool], None]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        value = bool(value)
        if self._enabled == value:
            return
        self._enabled = value
        self._notify()

    def toggle(self) -> None:
        self.set_enabled(not self._enabled)

    def add_listener(self, callback: Callable[[bool], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[bool], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback(self._enabled)
            except Exception:
                continue


__all__ = ["InventoryLockState"]
