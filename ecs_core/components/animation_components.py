from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Animation:
    sheet_path: str
    sheet_w: int
    sheet_h: int
    frame_w: int
    frame_h: int
    row_order: List[str]  # ["idle", "walk", "attack", ...]
    actions: Dict[str, int]  # {"idle": 4, "walk": 8}
    fps: float = 10.0
    flip_x_for_left: bool = True  # Auto-flip for left-facing


@dataclass
class AnimationState:
    current_action: str = "idle"
    frame_idx: int = 0
    timer: float = 0.0
    facing_left: bool = False
