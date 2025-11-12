# time_system/time_manager.py
from typing import Callable, Optional, Dict, Any, List, Tuple
from .game_clock import GameClock
from .day_night_cycle import DayNightCycle
from .time_events import TimeEvent, TimeEventType, TimeState


class TimeManager:
    """
    Hub for the Time Management System.
    Coordinates all time-related functionality in a modular, event-driven architecture.
    """

    def __init__(
        self,
        event_callback: Optional[Callable[[TimeEvent], None]] = None,
    ):
        """
        Initialize the Time Management System.

        Args:
            event_callback: Optional callback for all time events
        """
        # Core components (spokes)
        self.clock = GameClock()
        # Day/night cycle will publish into manager bus via _handle_event
        self.day_night_cycle = DayNightCycle(self.clock, self._handle_event)

        # Event system
        self._global_event_callback = event_callback
        self._event_subscribers: Dict[
            TimeEventType, List[Callable[[TimeEvent], None]]
        ] = {}

        # Scheduler (game-time and real-time)
        self._next_job_id: int = 1
        self._schedules: Dict[int, Dict[str, Any]] = {}

        # Heartbeat (real-time cadence)
        self._heartbeat_interval: float = 5.0
        self._next_heartbeat_real: float = (
            self.clock.real_elapsed + self._heartbeat_interval
        )

        # Statistics and debugging
        self._stats = {
            "total_events_fired": 0,
            "events_by_type": {},
            "cycles_completed": 0,
            "total_game_hours": 0.0,
        }

        # Initialize tracking
        self._last_day = 1

    # Removed string-based game-state handling. Use pause()/resume() instead.

    def update(self, dt: float) -> List[TimeEvent]:
        """
        Update the time system. Call this every frame.

        Args:
            dt: Delta time in seconds

        Returns:
            List of events that occurred this frame
        """
        # Update core clock
        self.clock.update(dt)

        # Update day/night cycle and get events (these will be dispatched via _handle_event)
        events = self.day_night_cycle.update()

        # Run scheduled jobs and append their emitted events
        schedule_events = self._run_schedules()

        # Heartbeat: fixed cadence in real seconds
        heartbeat_events = self._run_heartbeat()

        # Check for day cycle completion
        current_day = self.clock.get_current_game_day()
        if current_day > self._last_day:
            self._stats["cycles_completed"] = current_day - 1
            self._last_day = current_day

        return events + schedule_events + heartbeat_events

    # Convenience control API

    def pause(self) -> None:
        """Pause time progression and emit TIME_PAUSED if changed."""
        if not self.clock.is_paused:
            self.clock.pause()
            self._fire_event(TimeEventType.TIME_PAUSED)

    def resume(self) -> None:
        """Resume time progression and emit TIME_RESUMED if changed."""
        if self.clock.is_paused:
            self.clock.resume()
            self._fire_event(TimeEventType.TIME_RESUMED)

    def subscribe_to_event(
        self, event_type: TimeEventType, handler: Callable[[TimeEvent], None]
    ) -> None:
        """
        Subscribe to specific time events.

        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        if event_type not in self._event_subscribers:
            self._event_subscribers[event_type] = []
        self._event_subscribers[event_type].append(handler)

    def unsubscribe_from_event(
        self, event_type: TimeEventType, handler: Callable[[TimeEvent], None]
    ) -> None:
        """
        Unsubscribe from specific time events.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._event_subscribers:
            try:
                self._event_subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def get_current_state(self) -> TimeState:
        """Get complete current time state."""
        return self.clock.get_current_state()

    def get_stats(self) -> Dict[str, Any]:
        """Get time system statistics."""
        current_state = self.get_current_state()
        self._stats["total_game_hours"] = current_state.game_elapsed

        return {
            **self._stats,
            "current_day": current_state.game_day,
            "current_phase": current_state.phase.value,
            "is_paused": current_state.is_paused,
            "real_elapsed": current_state.real_elapsed,
        }

    def save_state(self) -> Dict[str, Any]:
        """
        Save current time state for save/load systems.

        Returns:
            Dictionary containing all necessary time state data
        """
        return {
            "time_state": self.get_current_state().to_dict(),
            "stats": self._stats.copy(),
            "heartbeat": {
                "interval": self._heartbeat_interval,
                "next_trigger": self._next_heartbeat_real,
            },
            "schedules": [
                {
                    "id": job_id,
                    "use_game_time": job["use_game_time"],
                    "next_trigger": job["next_trigger"],
                    "interval": job.get("interval"),
                    "tag": job.get("tag"),
                    "kind": job.get("kind", "once"),
                }
                for job_id, job in self._schedules.items()
            ],
        }

    def load_state(self, save_data: Dict[str, Any]) -> None:
        """
        Load time state from save data.

        Args:
            save_data: Dictionary containing saved time state
        """
        if "time_state" in save_data:
            time_state = TimeState.from_dict(save_data["time_state"])
            self.clock.load_state(time_state)

            # Reset cycle tracking after loading
            self.day_night_cycle.reset()
            self._last_day = time_state.game_day

        if "stats" in save_data:
            self._stats.update(save_data["stats"])

        # Restore schedules
        self._schedules.clear()
        self._next_job_id = 1
        if "schedules" in save_data:
            for entry in save_data["schedules"]:
                job_id = int(entry.get("id", self._next_job_id))
                self._next_job_id = max(self._next_job_id, job_id + 1)
                self._schedules[job_id] = {
                    "use_game_time": bool(entry.get("use_game_time", True)),
                    "next_trigger": float(entry.get("next_trigger", 0.0)),
                    "interval": (
                        float(entry["interval"])
                        if entry.get("interval") is not None
                        else None
                    ),
                    "tag": entry.get("tag"),
                    "kind": entry.get("kind", "once"),
                }

        self._next_heartbeat_real = self.clock.real_elapsed + self._heartbeat_interval
        if "heartbeat" in save_data:
            heartbeat_data = save_data["heartbeat"]
            if not isinstance(heartbeat_data, dict):
                raise TypeError("TimeManager.load_state: heartbeat must be a dict")
            interval_value = heartbeat_data.get("interval")
            if interval_value is not None:
                interval_value = float(interval_value)
                if interval_value <= 0.0:
                    raise ValueError(
                        "TimeManager.load_state: heartbeat interval must be > 0"
                    )
                self._heartbeat_interval = interval_value
            if "next_trigger" not in heartbeat_data:
                raise KeyError(
                    "TimeManager.load_state: heartbeat missing 'next_trigger'"
                )
            self._next_heartbeat_real = float(heartbeat_data["next_trigger"])

    def reset(self) -> None:
        """Reset time system to initial state."""
        self.clock = GameClock()
        self.day_night_cycle = DayNightCycle(self.clock, self._handle_event)
        self._last_day = 1
        self._stats = {
            "total_events_fired": 0,
            "events_by_type": {},
            "cycles_completed": 0,
            "total_game_hours": 0.0,
        }
        self._event_subscribers.clear()
        self._schedules.clear()
        self._next_job_id = 1
        self._heartbeat_interval = 5.0
        self._next_heartbeat_real = self.clock.real_elapsed + self._heartbeat_interval

    def _fire_event(
        self, event_type: TimeEventType, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Fire a time event manually (goes through manager bus)."""
        current_state = self.get_current_state()
        event = TimeEvent(
            event_type=event_type,
            real_time=current_state.real_elapsed,
            game_time=current_state.game_elapsed,
            game_hour=current_state.game_hour,
            game_day=current_state.game_day,
            is_day=current_state.is_day,
            data=data,
        )
        self._handle_event(event)

    def _handle_event(self, event: TimeEvent) -> None:
        """Central event bus: fan-out to global callback and subscribers, update stats."""
        # Global callback
        if self._global_event_callback:
            try:
                self._global_event_callback(event)
            except Exception:
                pass

        # Subscribers
        handlers = self._event_subscribers.get(event.event_type)
        if handlers:
            for handler in list(handlers):
                try:
                    handler(event)
                except Exception:
                    pass

        # Stats
        self._stats["total_events_fired"] += 1
        name = event.event_type.name
        self._stats["events_by_type"][name] = (
            self._stats["events_by_type"].get(name, 0) + 1
        )

    def _run_heartbeat(self) -> List[TimeEvent]:
        """Emit HEARTBEAT events on the fixed real-time cadence."""
        if self._heartbeat_interval <= 0.0:
            return []

        current_real = self.clock.real_elapsed
        if self._next_heartbeat_real is None:
            self._next_heartbeat_real = current_real + self._heartbeat_interval
            return []

        events: List[TimeEvent] = []
        epsilon = 1e-9
        while current_real + epsilon >= self._next_heartbeat_real:
            state = self.get_current_state()
            event = TimeEvent(
                event_type=TimeEventType.HEARTBEAT,
                real_time=state.real_elapsed,
                game_time=state.game_elapsed,
                game_hour=state.game_hour,
                game_day=state.game_day,
                is_day=state.is_day,
                data={
                    "interval": self._heartbeat_interval,
                },
            )
            self._handle_event(event)
            events.append(event)
            self._next_heartbeat_real += self._heartbeat_interval

        return events

    # ---------------------------
    # Scheduler API (minimal)
    # ---------------------------
    def _now_game_seconds(self) -> float:
        return self.clock.get_game_elapsed() * 3600.0

    def _now_real_seconds(self) -> float:
        return self.clock.real_elapsed

    def _add_job(
        self,
        use_game_time: bool,
        next_trigger: float,
        interval: Optional[float],
        tag: Optional[str],
        kind: str,
    ) -> int:
        job_id = self._next_job_id
        self._next_job_id += 1
        self._schedules[job_id] = {
            "use_game_time": use_game_time,
            "next_trigger": next_trigger,
            "interval": interval,
            "tag": tag,
            "kind": kind,
        }
        return job_id

    # Game-time schedules
    def schedule_in_game(self, minutes: float, tag: Optional[str] = None) -> int:
        """Schedule a one-shot event after N game minutes."""
        next_trigger = self._now_game_seconds() + max(0.0, minutes) * 60.0
        return self._add_job(True, next_trigger, None, tag, "once")

    def schedule_every_game(self, minutes: float, tag: Optional[str] = None) -> int:
        """Schedule a recurring event every N game minutes."""
        interval = max(0.001, minutes) * 60.0
        next_trigger = self._now_game_seconds() + interval
        return self._add_job(True, next_trigger, interval, tag, "recurring")

    def schedule_at_game(
        self, hour: int, minute: int = 0, tag: Optional[str] = None
    ) -> int:
        """Schedule a one-shot event at the next occurrence of HH:MM game time."""
        hour = max(0, min(23, int(hour)))
        minute = max(0, min(59, int(minute)))
        curr_hour = self.clock.get_current_game_hour()
        time_in_hour = self.clock.get_time_in_current_hour()
        curr = curr_hour + time_in_hour
        target = hour + (minute / 60.0)
        delta = (target - curr) % 24.0
        if delta == 0.0:
            delta = 24.0
        next_trigger = (
            self._now_game_seconds() + delta * self.clock.SECONDS_PER_GAME_HOUR
        )
        return self._add_job(True, next_trigger, None, tag, "once_at")

    # Real-time schedules (advance when clock updates)
    def schedule_in_real(self, seconds: float, tag: Optional[str] = None) -> int:
        """Schedule a one-shot event after N real seconds."""
        next_trigger = self._now_real_seconds() + max(0.0, seconds)
        return self._add_job(False, next_trigger, None, tag, "once")

    def schedule_every_real(self, seconds: float, tag: Optional[str] = None) -> int:
        """Schedule a recurring event every N real seconds."""
        interval = max(0.001, seconds)
        next_trigger = self._now_real_seconds() + interval
        return self._add_job(False, next_trigger, interval, tag, "recurring")

    def cancel_schedule(self, job_id: int) -> bool:
        """Cancel a scheduled job by id."""
        return self._schedules.pop(job_id, None) is not None

    def cancel_schedules_by_tag(self, tag: str) -> int:
        """Cancel all scheduled jobs with a given tag."""
        to_remove = [j for j, data in self._schedules.items() if data.get("tag") == tag]
        for j in to_remove:
            self._schedules.pop(j, None)
        return len(to_remove)

    def _run_schedules(self) -> List[TimeEvent]:
        """Check and fire due jobs. Returns list of emitted scheduler events."""
        if not self._schedules:
            return []
        now_game = self._now_game_seconds()
        now_real = self._now_real_seconds()
        emitted: List[TimeEvent] = []
        to_delete: List[int] = []
        for job_id, job in list(self._schedules.items()):
            now = now_game if job["use_game_time"] else now_real
            if now + 1e-9 >= job["next_trigger"]:
                fires = 1
                if job.get("interval"):
                    # Catch up: compute how many intervals have passed
                    interval = job["interval"]
                    if interval > 0:
                        # add enough intervals to exceed now
                        missed = int((now - job["next_trigger"]) // interval)
                        fires += max(0, missed)
                        job["next_trigger"] += fires * interval
                else:
                    to_delete.append(job_id)

                # Emit one event (coalesced) for this job
                data = {
                    "job_id": job_id,
                    "tag": job.get("tag"),
                    "use_game_time": job["use_game_time"],
                    "interval": job.get("interval"),
                    "kind": job.get("kind", "once"),
                    "fires": fires,
                }
                # Use manager bus
                self._fire_event(TimeEventType.SCHEDULE_TRIGGERED, data)

                # Also build event list for return value
                current_state = self.get_current_state()
                emitted.append(
                    TimeEvent(
                        event_type=TimeEventType.SCHEDULE_TRIGGERED,
                        real_time=current_state.real_elapsed,
                        game_time=current_state.game_elapsed,
                        game_hour=current_state.game_hour,
                        game_day=current_state.game_day,
                        is_day=current_state.is_day,
                        data=data,
                    )
                )

        for job_id in to_delete:
            self._schedules.pop(job_id, None)

        return emitted


# Convenience factory functions
def create_time_manager(
    event_callback: Optional[Callable[[TimeEvent], None]] = None,
) -> TimeManager:
    """Create a new TimeManager with default settings."""
    return TimeManager(event_callback=event_callback)
