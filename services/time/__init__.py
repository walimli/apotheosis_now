# time_manager/__init__.py
"""Public interface for the time manager package."""

from __future__ import annotations

from typing import Any, Dict, Iterable

# ---------------------------------------------------------------------------
# User-facing constants (single source of truth)
# ---------------------------------------------------------------------------
# Adjust these values to tweak game-time behaviour. All package components
# consume these constants, so edits here automatically propagate everywhere.
GAME_DAWN_HOUR = 6  # Dawn start (24h clock)
GAME_DUSK_HOUR = 18  # Dusk start (24h clock)
SECONDS_PER_GAME_HOUR = 30.0  # Real seconds that make up a game hour


# ---------------------------------------------------------------------------
# Public API metadata
# ---------------------------------------------------------------------------
__version__ = "1.0.0"
__author__ = "Time System Package"

_EXPORTED_NAMES: Dict[str, str] = {
    # Main hub
    "TimeManager": ".time_manager",
    # Core components (spokes)
    "GameClock": ".game_clock",
    "DayNightCycle": ".day_night_cycle",
    "TimeDisplay": ".time_display",
    "GameTimeOverlay": ".time_display",
    "CombinedTimeOverlay": ".time_display",
    # Event system
    "TimeEvent": ".time_events",
    "TimeEventType": ".time_events",
    "TimePhase": ".time_events",
    "TimeState": ".time_events",
}

__all__ = [
    *sorted(_EXPORTED_NAMES.keys()),
    "create_time_manager",
    "GAME_DAWN_HOUR",
    "GAME_DUSK_HOUR",
    "SECONDS_PER_GAME_HOUR",
    "create_simple_display",
    "create_full_display",
]


def __getattr__(name: str) -> Any:
    """Lazy loader for package exports to avoid circular imports."""
    module_path = _EXPORTED_NAMES.get(name)
    if not module_path:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    from importlib import import_module

    module = import_module(f"{__name__}{module_path}")
    try:
        value = getattr(module, name)
    except AttributeError as exc:  # pragma: no cover - defensive branch
        raise AttributeError(f"{module.__name__} does not define {name}") from exc
    globals()[name] = value
    return value


def __dir__() -> Iterable[str]:
    """Support IDE auto-complete."""
    return sorted(set(globals()) | set(__all__))


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------
def create_time_manager(event_callback=None):
    """Factory helper mirroring the previous public API."""
    from .time_manager import TimeManager

    return TimeManager(event_callback=event_callback)


def create_simple_display(time_manager, position=(30, 30)):
    """
    Create a simple time display for quick integration.

    Args:
        time_manager: TimeManager instance
        position: (x, y) position for display

    Returns:
        GameTimeOverlay ready to draw

    Example:
        time_manager = create_time_manager()
        time_manager.resume()
        time_display = create_simple_display(time_manager, (50, 50))

        # In your draw loop
        time_display.draw(screen)
    """
    from .time_display import GameTimeOverlay

    return GameTimeOverlay(time_manager.clock, pos=position)


def create_full_display(time_manager, position=(30, 30)):
    """
    Create a full-featured time display.

    Args:
        time_manager: TimeManager instance
        position: (x, y) position for display
        show_real_time: Always enabled in this helper

    Returns:
        TimeDisplay with all features enabled

    Example:
        time_manager = create_time_manager()
        time_manager.resume()
        time_display = create_full_display(time_manager)

        # In your draw loop
        time_display.draw(screen)
    """
    from .time_display import TimeDisplay

    return TimeDisplay(time_manager.clock, pos=position, show_real_time=True)
