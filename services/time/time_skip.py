"""Utility helpers for manipulating game time outside the core manager classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .game_clock import GameClock

if TYPE_CHECKING:
    from .time_manager import TimeManager


def advance_to_next_dawn(time_manager: "TimeManager") -> None:
    """Fast-forward the global clock to the next dawn cycle.

    - Advances the underlying GameClock to the next 6 AM boundary.
    - Resets cached day/night state so subsequent updates emit correct events.
    - Realigns the heartbeat schedule to the new real time baseline.
    """
    clock = time_manager.clock

    current_hours = clock.get_game_elapsed()
    hours_into_day = current_hours % GameClock.TOTAL_HOURS
    delta_hours = GameClock.TOTAL_HOURS - hours_into_day
    if delta_hours <= 1e-6:
        delta_hours = GameClock.TOTAL_HOURS

    new_game_hours = current_hours + delta_hours
    clock.real_elapsed = new_game_hours * GameClock.SECONDS_PER_GAME_HOUR

    # Reset cached transition tracking so dawn events fire correctly next frame.
    time_manager.day_night_cycle.reset()

    # Realign the heartbeat scheduler with the new real time.
    heartbeat_interval = getattr(time_manager, "_heartbeat_interval", 0.0)
    if heartbeat_interval > 0.0:
        time_manager._next_heartbeat_real = clock.real_elapsed + heartbeat_interval
    else:
        time_manager._next_heartbeat_real = None

    # Keep manager stats/day tracking consistent with the new timeline.
    time_manager._last_day = clock.get_current_game_day()
