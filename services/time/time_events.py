# time_system/events.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, Optional


class TimeEventType(Enum):
    """Time-related event types."""
    # Basic time events
    SECOND_PASSED = auto()
    MINUTE_PASSED = auto()
    GAME_HOUR_PASSED = auto()
    HEARTBEAT = auto()
    
    # Day/Night cycle events
    DAWN_STARTED = auto()
    DAY_STARTED = auto()
    NOON_REACHED = auto()
    DUSK_STARTED = auto()
    NIGHT_STARTED = auto()
    MIDNIGHT_REACHED = auto()
    
    # Time state changes
    TIME_PAUSED = auto()
    TIME_RESUMED = auto()

    # Scheduler
    SCHEDULE_TRIGGERED = auto()


@dataclass
class TimeEvent:
    """Container for time-related events."""
    event_type: TimeEventType
    real_time: float
    game_time: float
    game_hour: int
    game_day: int
    is_day: bool
    data: Optional[Dict[str, Any]] = None
    
    @property
    def formatted_game_time(self) -> str:
        """Returns game time in HH:MM format (24-hour)."""
        hours = int(self.game_time) % 24
        minutes = int((self.game_time % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    @property
    def formatted_game_time_12h(self) -> str:
        """Returns game time in 12-hour format with AM/PM."""
        hours = int(self.game_time) % 24
        minutes = int((self.game_time % 1) * 60)
        
        if hours == 0:
            display_hour = 12
            period = "AM"
        elif hours < 12:
            display_hour = hours
            period = "AM"
        elif hours == 12:
            display_hour = 12
            period = "PM"
        else:
            display_hour = hours - 12
            period = "PM"
            
        return f"{display_hour}:{minutes:02d} {period}"


class TimePhase(Enum):
    """Phases of the day/night cycle."""
    DAWN = "dawn"           # 6:00 AM - 7:00 AM
    DAY = "day"             # 7:00 AM - 7:00 PM  
    DUSK = "dusk"           # 7:00 PM - 8:00 PM
    NIGHT = "night"         # 8:00 PM - 6:00 AM
    
    def __str__(self):
        return self.value


@dataclass
class TimeState:
    """Current time state snapshot."""
    real_elapsed: float
    game_elapsed: float
    game_hour: int
    game_day: int
    phase: TimePhase
    is_day: bool
    is_paused: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for save/load systems."""
        return {
            'real_elapsed': self.real_elapsed,
            'game_elapsed': self.game_elapsed,
            'game_hour': self.game_hour,
            'game_day': self.game_day,
            'phase': self.phase.value,
            'is_day': self.is_day,
            'is_paused': self.is_paused
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeState':
        """Create from dictionary for save/load systems."""
        return cls(
            real_elapsed=data['real_elapsed'],
            game_elapsed=data['game_elapsed'],
            game_hour=data['game_hour'],
            game_day=data['game_day'],
            phase=TimePhase(data['phase']),
            is_day=data['is_day'],
            is_paused=data['is_paused']
        )
