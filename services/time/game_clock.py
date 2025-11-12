# time_system/game_clock.py
from __future__ import annotations

from . import GAME_DAWN_HOUR, GAME_DUSK_HOUR, SECONDS_PER_GAME_HOUR
from .time_events import TimePhase, TimeState


class GameClock:
    """Core time calculations and state management."""

    TOTAL_HOURS = 24
    DAWN_DURATION_HOURS = 1
    DUSK_DURATION_HOURS = 1

    # Mirrors of user-editable constants (single source of truth lives in __init__)
    DAWN_HOUR = GAME_DAWN_HOUR % TOTAL_HOURS
    DUSK_HOUR = GAME_DUSK_HOUR % TOTAL_HOURS
    SECONDS_PER_GAME_HOUR = float(SECONDS_PER_GAME_HOUR)

    def __init__(self) -> None:
        self.real_elapsed = 0.0
        self.is_paused = False

        self._dawn_hour = self.DAWN_HOUR
        self._dusk_hour = self.DUSK_HOUR
        self._day_start_hour = self._wrap_hour(
            self._dawn_hour + self.DAWN_DURATION_HOURS
        )
        self._night_start_hour = self._wrap_hour(
            self._dusk_hour + self.DUSK_DURATION_HOURS
        )
        self._day_hours = self._compute_day_hours()
        self._night_hours = (
            self.TOTAL_HOURS
            - self._day_hours
            - self.DAWN_DURATION_HOURS
            - self.DUSK_DURATION_HOURS
        )

    def update(self, dt: float) -> None:
        """Update the clock with delta time."""
        if not self.is_paused:
            self.real_elapsed += dt

    def pause(self) -> None:
        """Pause time progression."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume time progression."""
        self.is_paused = False

    def get_game_elapsed(self) -> float:
        """Get total elapsed game time in hours."""
        return self.real_elapsed / self.SECONDS_PER_GAME_HOUR

    def get_current_game_hour(self) -> int:
        """Get current hour of day (0-23), starting at configured dawn."""
        game_hours = self.get_game_elapsed()
        return int((self._dawn_hour + game_hours) % self.TOTAL_HOURS)

    def get_current_game_day(self) -> int:
        """Get current day number (starts at 1)."""
        game_hours = self.get_game_elapsed()
        return int(game_hours // self.TOTAL_HOURS) + 1

    def get_time_in_current_hour(self) -> float:
        """Get fractional time within current hour (0.0 to 1.0)."""
        return self.get_game_elapsed() % 1.0

    def get_day_start_hour(self) -> int:
        """Hour when full daylight begins."""
        return self._day_start_hour

    def get_night_start_hour(self) -> int:
        """Hour when full night begins."""
        return self._night_start_hour

    def get_noon_hour(self) -> int:
        """Approximate hour marking the midpoint of daylight."""
        if self._day_hours <= 0:
            return self._day_start_hour
        half_span = self._day_hours / 2.0
        return int(self._wrap_hour(self._day_start_hour + half_span))

    def get_daylight_hours(self) -> float:
        """Number of full daylight hours between day start and dusk."""
        return self._day_hours

    def get_night_hours(self) -> float:
        """Number of full night hours between night start and the next dawn."""
        return self._night_hours

    def get_current_phase(self) -> TimePhase:
        """Get current phase of the day/night cycle."""
        hour = self.get_current_game_hour()

        if hour == self._dawn_hour:
            return TimePhase.DAWN
        if self._is_hour_in_range(hour, self._day_start_hour, self._dusk_hour):
            return TimePhase.DAY
        if hour == self._dusk_hour:
            return TimePhase.DUSK
        return TimePhase.NIGHT

    def is_day_time(self) -> bool:
        """Check if it's currently day time (dawn through dusk)."""
        hour = self.get_current_game_hour()
        return self._is_hour_in_range(hour, self._dawn_hour, self._night_start_hour)

    def is_night_time(self) -> bool:
        """Check if it's currently night time (night start through next dawn)."""
        return not self.is_day_time()

    def get_time_until_next_phase(self) -> float:
        """Get real seconds until the next phase change."""
        current_hour = self.get_current_game_hour()
        time_in_hour = self.get_time_in_current_hour()
        current_time = (current_hour + time_in_hour) % self.TOTAL_HOURS

        phase = self.get_current_phase()
        if phase == TimePhase.DAWN:
            next_boundary = self._day_start_hour
        elif phase == TimePhase.DAY:
            next_boundary = self._dusk_hour
        elif phase == TimePhase.DUSK:
            next_boundary = self._night_start_hour
        else:
            next_boundary = self._dawn_hour

        hours_until = self._hours_until(current_time, next_boundary)
        return hours_until * self.SECONDS_PER_GAME_HOUR

    def get_day_progress(self) -> float:
        """Get progress through current day (0.0 = dawn, 1.0 = next dawn)."""
        game_hours = self.get_game_elapsed()
        hours_since_dawn = game_hours % self.TOTAL_HOURS
        return hours_since_dawn / float(self.TOTAL_HOURS)

    def get_daylight_progress(self) -> float:
        """Get progress through daylight hours (0.0 = dawn end, 1.0 = dusk start)."""
        if self.is_night_time():
            current_hour = self.get_current_game_hour()
            if self._is_hour_in_range(current_hour, self._night_start_hour, self._dawn_hour):
                return 0.0
            return 1.0

        hour = self.get_current_game_hour()
        time_in_hour = self.get_time_in_current_hour()

        daylight_hours = self._day_hours or 1.0
        elapsed = self._hours_since(self._day_start_hour, hour, time_in_hour)
        return max(0.0, min(1.0, elapsed / daylight_hours))

    def get_formatted_time(self, use_12_hour: bool = False) -> str:
        """Get formatted time string."""
        hour = self.get_current_game_hour()
        minutes = int(self.get_time_in_current_hour() * 60)

        if use_12_hour:
            if hour == 0:
                display_hour, period = 12, "AM"
            elif hour < 12:
                display_hour, period = hour, "AM"
            elif hour == 12:
                display_hour, period = 12, "PM"
            else:
                display_hour, period = hour - 12, "PM"
            return f"{display_hour}:{minutes:02d} {period}"
        return f"{hour:02d}:{minutes:02d}"

    def get_current_state(self) -> TimeState:
        """Get complete current time state."""
        return TimeState(
            real_elapsed=self.real_elapsed,
            game_elapsed=self.get_game_elapsed(),
            game_hour=self.get_current_game_hour(),
            game_day=self.get_current_game_day(),
            phase=self.get_current_phase(),
            is_day=self.is_day_time(),
            is_paused=self.is_paused,
        )

    def load_state(self, state: TimeState) -> None:
        """Load time state (for save/load systems)."""
        self.real_elapsed = state.real_elapsed
        self.is_paused = state.is_paused

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _wrap_hour(self, hour: float) -> float:
        return hour % self.TOTAL_HOURS

    def _hours_between(self, start: float, end: float) -> float:
        return (end - start) % self.TOTAL_HOURS

    def _hours_until(self, current: float, target: float) -> float:
        delta = (target - current) % self.TOTAL_HOURS
        return delta if delta > 0 else self.TOTAL_HOURS

    def _is_hour_in_range(self, hour: int, start: int, end: int) -> bool:
        span = self._hours_between(start, end)
        if span == 0:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    def _hours_since(self, start: int, current_hour: int, time_in_hour: float) -> float:
        current = (current_hour + time_in_hour) % self.TOTAL_HOURS
        return (current - start) % self.TOTAL_HOURS

    def _compute_day_hours(self) -> float:
        span = self._hours_between(self._day_start_hour, self._dusk_hour)
        if span == 0:
            span = (
                self.TOTAL_HOURS
                - self.DAWN_DURATION_HOURS
                - self.DUSK_DURATION_HOURS
            )
        return span
