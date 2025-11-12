"""Load and validate JSON-defined input bindings.

This module parses human-readable binding configs and converts them into
`InputBinding` structures consumable by `PlayInputBus`.

Schema (per docs/inputs_remapping_plan.md):
{
  "ACTION_NAME": [
    {"trigger": ["key"|"key_axis"|"mouse_button"|"mouse_wheel", CODE],
     "value": number | [dx, dy] (optional)
    },
    ...
  ],
  ...
}
CODE may be:
  - for keys: string name like "K_w", "K_ESCAPE" (resolved via pygame), or int keycode
  - for mouse_button: "MOUSE_LEFT"|"MOUSE_MIDDLE"|"MOUSE_RIGHT"|"MOUSE_X1"|"MOUSE_X2" or int
  - for mouse_wheel: "UP"|"DOWN" or 1|-1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import json
import pygame

from .actions import PlayAction
from .bindings import InputBinding


_MOUSE_BUTTONS: Dict[str, int] = {
    "MOUSE_LEFT": 1,
    "MOUSE_MIDDLE": 2,
    "MOUSE_RIGHT": 3,
    "MOUSE_X1": 8,
    "MOUSE_X2": 9,
}
_MOUSE_BUTTONS_REV: Dict[int, str] = {v: k for k, v in _MOUSE_BUTTONS.items()}

_WHEEL_DIR: Dict[str, int] = {"UP": 1, "DOWN": -1}
_WHEEL_DIR_REV: Dict[int, str] = {v: k for k, v in _WHEEL_DIR.items()}

_PYGAME_KEYS: Dict[str, int] | None = None
_PYGAME_KEYS_REV: Dict[int, str] | None = None


class ConfigError(Exception):
    pass


def _init_pygame_keys() -> None:
    global _PYGAME_KEYS, _PYGAME_KEYS_REV
    if _PYGAME_KEYS is not None:
        return
    _PYGAME_KEYS = {
        name: val for name, val in pygame.__dict__.items() if name.startswith("K_")
    }
    _PYGAME_KEYS_REV = {v: k for k, v in _PYGAME_KEYS.items()}


def _ensure_file(path: Path) -> None:
    if not path.exists():
        raise ConfigError(f"Missing bindings config: {path}")


def _resolve_code(trigger_type: str, code) -> int:
    _init_pygame_keys()
    if trigger_type in ("key", "key_axis"):
        if isinstance(code, int):
            return code
        if isinstance(code, str):
            if not code.startswith("K_"):
                raise ConfigError(f"Invalid key code string '{code}' (expected 'K_*')")
            if not hasattr(pygame, code):
                raise ConfigError(f"Unknown pygame key name '{code}'")
            return int(getattr(pygame, code))
        raise ConfigError(f"Invalid key code type: {type(code)}")
    if trigger_type == "mouse_button":
        if isinstance(code, int):
            return code
        if isinstance(code, str):
            if code not in _MOUSE_BUTTONS:
                raise ConfigError(f"Unknown mouse button name '{code}'")
            return _MOUSE_BUTTONS[code]
        raise ConfigError(f"Invalid mouse button code type: {type(code)}")
    if trigger_type == "mouse_wheel":
        if isinstance(code, int):
            if code not in (1, -1):
                raise ConfigError(f"Wheel direction must be 1 or -1, got {code}")
            return code
        if isinstance(code, str):
            if code not in _WHEEL_DIR:
                raise ConfigError(f"Unknown wheel direction '{code}' (use 'UP'|'DOWN')")
            return _WHEEL_DIR[code]
        raise ConfigError(f"Invalid wheel code type: {type(code)}")
    raise ConfigError(f"Unknown trigger type '{trigger_type}'")


def _unresolve_code(trigger_type: str, code: int) -> str | int:
    _init_pygame_keys()
    if trigger_type in ("key", "key_axis"):
        return _PYGAME_KEYS_REV.get(code, code)
    if trigger_type == "mouse_button":
        return _MOUSE_BUTTONS_REV.get(code, code)
    if trigger_type == "mouse_wheel":
        return _WHEEL_DIR_REV.get(code, code)
    return code


def _expect_action_trigger(action: PlayAction, trigger_type: str) -> None:
    if action == PlayAction.MOVE:
        if trigger_type != "key_axis":
            raise ConfigError("MOVE requires 'key_axis' triggers")
        return
    if action == PlayAction.HOTBAR_SCROLL or action == PlayAction.SCROLL:
        if trigger_type != "mouse_wheel":
            raise ConfigError(f"{action.name} requires 'mouse_wheel' triggers")
        return
    if action == PlayAction.HOTBAR_SELECT:
        if trigger_type not in ("key",):
            raise ConfigError("HOTBAR_SELECT requires 'key' triggers")
        return
    # Remaining actions accept button or mouse
    if trigger_type not in ("key", "mouse_button"):
        raise ConfigError(
            f"{action.name} only supports 'key' or 'mouse_button' triggers"
        )


def _parse_value(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if (
        isinstance(val, list)
        and len(val) == 2
        and all(isinstance(v, (int, float)) for v in val)
    ):
        return (float(val[0]), float(val[1]))
    raise ConfigError(f"Invalid value payload: {val}")


def _build_bindings(data: Dict) -> Dict[PlayAction, Tuple[InputBinding, ...]]:
    out: Dict[PlayAction, List[InputBinding]] = {}
    for action_name, entries in data.items():
        try:
            action = PlayAction[action_name]
        except KeyError:
            raise ConfigError(f"Unknown action '{action_name}'")
        if not isinstance(entries, list):
            raise ConfigError(f"Action '{action_name}' must map to a list of bindings")
        lst: List[InputBinding] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ConfigError(f"Binding #{idx} for '{action_name}' must be an object")
            trig = entry.get("trigger")
            if not (isinstance(trig, list) and len(trig) == 2):
                raise ConfigError(f"Binding '{action_name}' missing trigger [type, code]")
            trig_type, trig_code = trig[0], trig[1]
            _expect_action_trigger(action, trig_type)
            code_int = _resolve_code(trig_type, trig_code)
            value = _parse_value(entry.get("value"))
            lst.append(InputBinding(action=action, trigger=(trig_type, code_int), value=value))
        out[action] = tuple(lst)
    return out


def _read_json(path: Path) -> Dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {path}: {e}")


def _deep_merge_bindings(base: Dict, override: Dict) -> Dict:
    # Per action: if override provides a list, it replaces base list entirely.
    merged = dict(base)
    for k, v in override.items():
        merged[k] = v
    return merged


def load_bindings(
    default_path: Path, user_path: Path | None = None
) -> Dict[PlayAction, Tuple[InputBinding, ...]]:
    """Load and validate bindings from JSON files.

    - default_path must exist and be valid.
    - user_path, if provided and exists, replaces per-action lists.
    - Errors are raised as ConfigError (no internal fallbacks).
    """
    _ensure_file(default_path)
    base = _read_json(default_path)
    data = base
    if user_path is not None and user_path.exists():
        override = _read_json(user_path)
        data = _deep_merge_bindings(base, override)
    return _build_bindings(data)


def save_user_bindings(
    user_path: Path, bindings: Dict[PlayAction, Tuple[InputBinding, ...]]
) -> None:
    """Serialize a binding map to a user JSON file."""
    output: Dict[str, List[Dict[str, Any]]] = {}
    for action, binding_tuple in bindings.items():
        output[action.name] = []
        for binding in binding_tuple:
            trig_type, trig_code = binding.trigger
            entry: Dict[str, Any] = {
                "trigger": [trig_type, _unresolve_code(trig_type, trig_code)]
            }
            if binding.value is not None:
                entry["value"] = binding.value
            output[action.name].append(entry)
    with user_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
