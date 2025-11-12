# time_system/day_night_cycle.py
from typing import Callable, Optional, List, Tuple
from .time_events import TimeEvent, TimeEventType, TimePhase
from .game_clock import GameClock


class DayNightCycle:
    """Manages day/night cycle transitions and events."""
    
    def __init__(self, clock: GameClock, event_callback: Optional[Callable[[TimeEvent], None]] = None):
        self.clock = clock
        self.event_callback = event_callback
        self._recalculate_cycle_hours()
        
        # Track previous states to detect transitions
        self._last_game_hour = -1
        self._last_phase = None
        self._last_day = 0
        self._last_second = -1
        self._last_minute = -1
        
        # No internal event bus; events route through TimeManager via event_callback
    
    def update(self) -> List[TimeEvent]:
        """Update cycle and return any events that occurred."""
        if self.clock.is_paused:
            return []
            
        events = []
        current_state = self.clock.get_current_state()
        
        # Check for second transitions
        current_second = int(current_state.real_elapsed)
        if current_second != self._last_second:
            events.append(self._create_event(TimeEventType.SECOND_PASSED, current_state))
            self._last_second = current_second
        
        # Check for minute transitions (real time)
        current_minute = int(current_state.real_elapsed / 60)
        if current_minute != self._last_minute:
            events.append(self._create_event(TimeEventType.MINUTE_PASSED, current_state))
            self._last_minute = current_minute
        
        # Check for game hour transitions
        if current_state.game_hour != self._last_game_hour:
            events.append(self._create_event(TimeEventType.GAME_HOUR_PASSED, current_state))
            
            # Check for specific hour events
            hour_events = self._check_special_hours(current_state.game_hour)
            events.extend([self._create_event(event_type, current_state) for event_type in hour_events])
            
            self._last_game_hour = current_state.game_hour
        
        # Check for phase transitions
        if current_state.phase != self._last_phase:
            phase_event = self._get_phase_event(current_state.phase)
            if phase_event:
                events.append(self._create_event(phase_event, current_state))
            self._last_phase = current_state.phase
        
        # Check for day transitions
        if current_state.game_day != self._last_day:
            self._last_day = current_state.game_day
        
        # Send events to manager callback
        for event in events:
            if self.event_callback:
                self.event_callback(event)
        
        return events
    
    def _create_event(self, event_type: TimeEventType, state) -> TimeEvent:
        """Create a TimeEvent from current state."""
        return TimeEvent(
            event_type=event_type,
            real_time=state.real_elapsed,
            game_time=state.game_elapsed,
            game_hour=state.game_hour,
            game_day=state.game_day,
            is_day=state.is_day,
        )

    def _check_special_hours(self, hour: int) -> List[TimeEventType]:
        """Check for special hour-based events."""
        events = []

        if hour == self._dawn_hour:
            events.append(TimeEventType.DAWN_STARTED)
        if hour == self._day_start_hour and self._day_start_hour != self._dawn_hour:
            events.append(TimeEventType.DAY_STARTED)
        if self._daylight_hours > 0 and hour == self._noon_hour:
            events.append(TimeEventType.NOON_REACHED)
        if hour == self._dusk_hour:
            events.append(TimeEventType.DUSK_STARTED)
        if hour == self._night_start_hour and self._night_start_hour != self._dusk_hour:
            events.append(TimeEventType.NIGHT_STARTED)
        if hour == 0:
            events.append(TimeEventType.MIDNIGHT_REACHED)
            
        return events
    
    def _get_phase_event(self, phase: TimePhase) -> Optional[TimeEventType]:
        """Get event type for phase transition."""
        # We rely on hour-based events for most transitions
        # This could be used for additional phase-specific logic
        return None
    
    # No _notify_handlers; event delivery handled by TimeManager
    
    def get_lighting_factor(self) -> float:
        """Get lighting factor for rendering (0.0 = full dark, 1.0 = full bright)."""
        phase = self.clock.get_current_phase()
        time_in_hour = self.clock.get_time_in_current_hour()
        
        if phase == TimePhase.DAWN:
            # Dawn fades linearly from night brightness to full day
            return self._lerp(self._night_brightness(), self._day_brightness(), time_in_hour)
        elif phase == TimePhase.DAY:
            return self._day_brightness()
        elif phase == TimePhase.DUSK:
            # Dusk returns linearly from day brightness down to night level
            return self._lerp(self._day_brightness(), self._night_brightness(), time_in_hour)
        else:  # Night
            return self._night_brightness()
    
    def get_ambient_color(self) -> Tuple[int, int, int]:
        """Get ambient color tint for rendering."""
        phase = self.clock.get_current_phase()
        time_in_hour = self.clock.get_time_in_current_hour()
        
        # Color values (R, G, B)
        if phase == TimePhase.DAWN:
            # Dawn colors: transition from night blue to warm orange
            night_color = (100, 120, 180)  # Cool blue
            dawn_color = (255, 200, 150)   # Warm orange
            t = time_in_hour
            return (
                int(night_color[0] + (dawn_color[0] - night_color[0]) * t),
                int(night_color[1] + (dawn_color[1] - night_color[1]) * t),
                int(night_color[2] + (dawn_color[2] - night_color[2]) * t)
            )
        elif phase == TimePhase.DAY:
            return (255, 255, 255)  # Pure white daylight
        elif phase == TimePhase.DUSK:
            # Dusk colors: transition from white to deep orange/red
            day_color = (255, 255, 255)    # White
            dusk_color = (255, 150, 100)   # Orange/red
            t = time_in_hour
            return (
                int(day_color[0] + (dusk_color[0] - day_color[0]) * t),
                int(day_color[1] + (dusk_color[1] - day_color[1]) * t),
                int(day_color[2] + (dusk_color[2] - day_color[2]) * t)
            )
        else:  # Night
            return (80, 100, 160)  # Cool night blue
    
    def get_phase_description(self) -> str:
        """Get human-readable description of current phase."""
        phase = self.clock.get_current_phase()
        hour = self.clock.get_current_game_hour()
        
        descriptions = {
            TimePhase.DAWN: "The sun rises on the eastern horizon",
            TimePhase.DAY: "The sun shines brightly overhead" if 11 <= hour <= 15 else "Daylight illuminates the land",
            TimePhase.DUSK: "The sun sets in the western sky",
            TimePhase.NIGHT: "Darkness blankets the land" if 22 <= hour or hour <= 4 else "The night grows deep"
        }
        
        return descriptions.get(phase, "Time passes")
    
    def reset(self) -> None:
        """Reset cycle tracking (useful when loading saves)."""
        self._last_game_hour = -1
        self._last_phase = None
        self._last_day = 0
        self._last_second = -1
        self._last_minute = -1
        self._recalculate_cycle_hours()

    def _recalculate_cycle_hours(self) -> None:
        """Cache commonly used cycle boundaries for quick comparisons."""
        self._dawn_hour = self.clock.DAWN_HOUR
        self._day_start_hour = self.clock.get_day_start_hour()
        self._dusk_hour = self.clock.DUSK_HOUR
        self._night_start_hour = self.clock.get_night_start_hour()
        self._noon_hour = self.clock.get_noon_hour()
        self._daylight_hours = self.clock.get_daylight_hours()

    @staticmethod
    def _lerp(start: float, end: float, t: float) -> float:
        t = max(0.0, min(1.0, t))
        return start + (end - start) * t

    @staticmethod
    def _day_brightness() -> float:
        return 1.0

    @staticmethod
    def _night_brightness() -> float:
        return 0.2
