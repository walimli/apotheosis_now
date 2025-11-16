from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from systems.collision.json_validator import assert_offset, validate_aabb
from systems.drops.specs import DropSpec


@dataclass
class Stats:
    speed_px_per_s: float
    durability: int
    sight_range_px: float
    attack_range_px: float
    attack_damage: int
    attack_cooldown_s: float


@dataclass
class Capsule:
    width_tiles: float
    height_tiles: float


@dataclass
class AABB:
    width_tiles: float
    height_tiles: float
    offset_x_tiles: float
    offset_y_tiles: float


@dataclass
class Collider:
    anchor: str
    capsule: Capsule
    aabb: AABB


@dataclass
class Assets:
    registry_group_keys: Dict[str, str]
    frame_width: int
    frame_height: int


@dataclass
class Spawn:
    time: List[str]
    attempts_per_heartbeat: int
    spawn_chance: float
    radius_px: Tuple[int, int]
    max_alive: int


@dataclass
class MobSpec:
    id: str
    category: str
    behavior_id: str
    z_index: int
    xp_reward: int
    stats: Stats
    collider: Collider
    assets: Assets
    spawn: Spawn
    drops: Tuple[DropSpec, ...]


def load_spec_from_file(path: str) -> MobSpec:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "Mob spec must be a JSON object"

    # Required top-level fields
    sid = _require_str(data, "id")
    cat = _require_str(data, "category")
    beh = _require_str(data, "behavior_id")
    z = _require_int(data, "z_index")
    xp = _require_int(data, "xp_reward")

    # Stats (pixels + seconds)
    stats_obj = _require_obj(data, "stats")
    stats = Stats(
        speed_px_per_s=float(_require_num(stats_obj, "speed_px_per_s")),
        durability=int(_require_int(stats_obj, "durability")),
        sight_range_px=float(_require_num(stats_obj, "sight_range_px")),
        attack_range_px=float(_require_num(stats_obj, "attack_range_px")),
        attack_damage=int(_require_int(stats_obj, "attack_damage")),
        attack_cooldown_s=float(_require_num(stats_obj, "attack_cooldown_s")),
    )

    # Collider (capsule dims in tiles)
    col_obj = _require_obj(data, "collider")
    anchor = _require_str(col_obj, "anchor")
    cap_obj = _require_obj(col_obj, "capsule")
    cap = Capsule(
        width_tiles=float(_require_num(cap_obj, "width_tiles")),
        height_tiles=float(_require_num(cap_obj, "height_tiles")),
    )
    aabb = _parse_aabb(col_obj.get("aabb"), cap, sid)
    collider = Collider(anchor=anchor, capsule=cap, aabb=aabb)

    # Assets via registry groups
    assets_obj = _require_obj(data, "assets")
    groups = _require_obj(assets_obj, "registry_group_keys")
    _validate_anim_groups(groups)
    fw = _require_int(assets_obj, "frame_width")
    fh = _require_int(assets_obj, "frame_height")
    assets = Assets(registry_group_keys={str(k): str(v) for k, v in groups.items()}, frame_width=int(fw), frame_height=int(fh))

    # Spawn policy (pixels, simple)
    spawn_obj = _require_obj(data, "spawn")
    times = _require_list(spawn_obj, "time")
    assert all(isinstance(t, str) and t for t in times), "spawn.time must be non-empty strings"
    aph = int(_require_int(spawn_obj, "attempts_per_heartbeat"))
    chance = float(_require_num(spawn_obj, "spawn_chance"))
    assert 0.0 <= chance <= 1.0, "spawn.spawn_chance must be between 0 and 1"
    rpx = _require_list(spawn_obj, "radius_px")
    assert len(rpx) == 2, "spawn.radius_px must be [min, max]"
    rmin, rmax = int(rpx[0]), int(rpx[1])
    assert 0 <= rmin <= rmax, "spawn.radius_px must satisfy 0 <= min <= max"
    max_alive = int(_require_int(spawn_obj, "max_alive"))
    spawn = Spawn(time=[str(t) for t in times], attempts_per_heartbeat=aph, spawn_chance=chance, radius_px=(rmin, rmax), max_alive=max_alive)

    return MobSpec(
        id=sid,
        category=cat,
        behavior_id=beh,
        z_index=int(z),
        xp_reward=int(xp),
        stats=stats,
        collider=collider,
        assets=assets,
        spawn=spawn,
        drops=_parse_drops(data, sid),
    )


def _parse_aabb(value, capsule: Capsule, spec_id: str) -> AABB:
    context = f"mob '{spec_id}' collider.aabb"
    width = capsule.width_tiles
    height = capsule.height_tiles
    offset_x = 0.0
    offset_y = 0.0

    if isinstance(value, dict):
        width = _optional_num(value, "width_tiles", width)
        height = _optional_num(value, "height_tiles", height)
        offset_x = _optional_num(value, "offset_x_tiles", offset_x)
        offset_y = _optional_num(value, "offset_y_tiles", offset_y)

    validate_aabb(width, height, context)
    assert_offset(offset_x, "offset_x_tiles", context)
    assert_offset(offset_y, "offset_y_tiles", context)
    return AABB(
        width_tiles=width,
        height_tiles=height,
        offset_x_tiles=offset_x,
        offset_y_tiles=offset_y,
    )


def _parse_drops(data: dict, spec_id: str) -> Tuple[DropSpec, ...]:
    raw = data.get("drops")
    if raw is None:
        return tuple()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TypeError(f"mob '{spec_id}' drops must be a sequence")

    drops: List[DropSpec] = []
    for entry in raw:
        drops.append(_parse_drop_entry(entry, spec_id))
    return tuple(drops)


def _parse_drop_entry(entry, spec_id: str) -> DropSpec:
    if not isinstance(entry, dict):
        raise TypeError(f"mob '{spec_id}' drop entry must be an object")

    item = entry.get("item")
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"mob '{spec_id}' drop item id must be a non-empty string")
    item_id = item.strip()

    try:
        qty_min = int(entry.get("qty_min", 1))
        qty_max = int(entry.get("qty_max", qty_min))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mob '{spec_id}' drop quantities must be numeric") from exc

    try:
        chance_value = entry.get("chance", 1.0)
        chance = float(chance_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mob '{spec_id}' drop chance must be numeric") from exc

    spec = DropSpec(item_id=item_id, qty_min=qty_min, qty_max=qty_max, chance=chance)
    return spec.normalized()


# --- Validation helpers ---
def _require_obj(obj: dict, key: str) -> dict:
    val = obj.get(key)
    assert isinstance(val, dict), f"Missing or invalid object for key '{key}'"
    return val


def _require_list(obj: dict, key: str) -> List:
    val = obj.get(key)
    assert isinstance(val, list) and len(val) > 0, f"Missing or invalid list for key '{key}'"
    return val


def _require_str(obj: dict, key: str) -> str:
    val = obj.get(key)
    assert isinstance(val, str) and val, f"Missing or invalid string for key '{key}'"
    return val


def _require_int(obj: dict, key: str) -> int:
    val = obj.get(key)
    assert isinstance(val, int), f"Missing or invalid integer for key '{key}'"
    return val


def _require_num(obj: dict, key: str) -> float:
    val = obj.get(key)
    assert isinstance(val, (int, float)), f"Missing or invalid number for key '{key}'"
    return float(val)


def _optional_num(obj: dict, key: str, default: float) -> float:
    val = obj.get(key)
    if val is None:
        return float(default)
    assert isinstance(val, (int, float)), f"Invalid number for key '{key}'"
    return float(val)


def _validate_anim_groups(groups: Dict[str, str]) -> None:
    required = [
        "idle_down",
        "idle_up",
        "idle_left",
        "idle_right",
        "walk_down",
        "walk_up",
        "walk_left",
        "walk_right",
    ]
    for k in required:
        v = groups.get(k)
        assert isinstance(v, str) and v, f"assets.registry_group_keys missing '{k}'"

