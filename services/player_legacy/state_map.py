"""Animation state to asset mapping and timing controls."""

from __future__ import annotations

from typing import Dict

from .image_loader import SpriteSheetSlice

DIRECTIONS = ("down", "down_left", "left", "up_left", "up")
DIR_TO_ROW = {direction: index for index, direction in enumerate(DIRECTIONS)}

BASE_ACTION_SHEETS = {
    "idle": ("player_idle.png", 8),
    "walk": ("player_walk.png", 6),
    "interact": ("player_interact.png", 3),
    "hurt": ("player_hurt.png", 2),
    "die": ("player_die.png", 6),
}

PICK_ACTION_SHEETS = {
    "idle": ("player_idle_pick.png", 8),
    "walk": ("player_walk_pick.png", 6),
    "interact": ("player_interact_pick.png", 3),
    "hurt": ("player_hurt_pick.png", 2),
    "swing": ("player_swing_pick.png", 6),
}

SWORD_ACTION_SHEETS = {
    "idle": ("player_idle_sword.png", 8),
    "walk": ("player_walk_sword.png", 6),
    "interact": ("player_interact_sword.png", 3),
    "hurt": ("player_hurt_sword.png", 2),
    "swing": ("player_swing_sword.png", 6),
}

ACTION_FRAME_TIME = {
    "idle": 0.12,
    "walk": 0.1,
    "interact": 0.12,
    "hurt": 0.12,
    "die": 0.16,
    "swing": 0.08,
}

ACTION_LOOPING = {
    "idle": True,
    "walk": True,
    "interact": False,
    "hurt": False,
    "die": False,
    "swing": False,
}

DEFAULT_FRAME_TIME = 0.1

STATE_FILES: Dict[str, SpriteSheetSlice] = {}
STATE_FRAME_TIME: Dict[str, float] = {}
STATE_LOOPING: Dict[str, bool] = {}
STATE_ACTION: Dict[str, str] = {}
STATE_VARIANT: Dict[str, str] = {}
STATE_DIRECTION: Dict[str, str] = {}


def _register(
    action: str,
    direction: str,
    sheet: str,
    frames: int,
    *,
    variant: str = "",
) -> None:
    suffix = f"_{variant}" if variant else ""
    state_name = f"{action}_{direction}{suffix}"
    spec = SpriteSheetSlice(filename=sheet, row=DIR_TO_ROW[direction], frames=frames)
    STATE_FILES[state_name] = spec
    STATE_ACTION[state_name] = action
    STATE_FRAME_TIME[state_name] = ACTION_FRAME_TIME.get(action, DEFAULT_FRAME_TIME)
    STATE_LOOPING[state_name] = ACTION_LOOPING.get(action, False)
    STATE_VARIANT[state_name] = variant
    STATE_DIRECTION[state_name] = direction


def _alias_state(
    alias: str,
    target: str,
    *,
    direction: str | None = None,
    variant: str | None = None,
) -> None:
    STATE_FILES[alias] = STATE_FILES[target]
    STATE_ACTION[alias] = STATE_ACTION[target]
    STATE_FRAME_TIME[alias] = STATE_FRAME_TIME[target]
    STATE_LOOPING[alias] = STATE_LOOPING[target]
    if variant is None:
        variant = STATE_VARIANT.get(target, "")
    STATE_VARIANT[alias] = variant or ""
    STATE_DIRECTION[alias] = direction if direction is not None else STATE_DIRECTION[target]


for action, (sheet, frame_count) in BASE_ACTION_SHEETS.items():
    for direction in DIRECTIONS:
        _register(action, direction, sheet, frame_count, variant="")

for action, (sheet, frame_count) in PICK_ACTION_SHEETS.items():
    for direction in DIRECTIONS:
        _register(action, direction, sheet, frame_count, variant="pick")

for action, (sheet, frame_count) in SWORD_ACTION_SHEETS.items():
    for direction in DIRECTIONS:
        _register(action, direction, sheet, frame_count, variant="sword")

for direction in DIRECTIONS:
    base_state = f"die_{direction}"
    pick_state = f"{base_state}_pick"
    if pick_state not in STATE_FILES and base_state in STATE_FILES:
        _alias_state(pick_state, base_state, direction=direction, variant="pick")
    sword_state = f"{base_state}_sword"
    if sword_state not in STATE_FILES and base_state in STATE_FILES:
        _alias_state(sword_state, base_state, direction=direction, variant="sword")

_MIRROR_TARGETS = {
    "left": "right",
    "down_left": "down_right",
    "up_left": "up_right",
}

for state_name, direction in list(STATE_DIRECTION.items()):
    mirror_dir = _MIRROR_TARGETS.get(direction)
    if mirror_dir is None:
        continue
    action = STATE_ACTION[state_name]
    variant = STATE_VARIANT.get(state_name, "")
    suffix = f"_{variant}" if variant else ""
    alias_name = f"{action}_{mirror_dir}{suffix}"
    if alias_name in STATE_FILES:
        continue
    _alias_state(alias_name, state_name, direction=mirror_dir, variant=variant)

# Existing attack_* names temporarily alias to the pickaxe swing animations.
_ATTACK_ALIAS_MAP = {
    "attack_down_pick": "swing_down_pick",
    "attack_up_pick": "swing_up_pick",
    "attack_left_pick": "swing_left_pick",
    "attack_right_pick": "swing_left_pick",
    "attack_down_sword": "swing_down_sword",
    "attack_up_sword": "swing_up_sword",
    "attack_left_sword": "swing_left_sword",
    "attack_right_sword": "swing_left_sword",
}

for alias_name, target in _ATTACK_ALIAS_MAP.items():
    parts = alias_name.split("_")
    direction = parts[1]
    variant = parts[2] if len(parts) > 2 else None
    _alias_state(alias_name, target, direction=direction, variant=variant)
