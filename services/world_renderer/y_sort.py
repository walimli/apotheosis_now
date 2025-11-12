from __future__ import annotations

from typing import Dict, Tuple


def placeable_baseline(obj: Dict, sprite_height: int, world_top_left_y: float) -> float:
    """Compute a y-sort baseline for a placeable.

    Preference order:
    1) JSON ysort fields (anchor fraction of sprite height, plus px offset)
    2) Collider bottom (aabb[3]) if provided
    3) Bottom of sprite (top + height)
    """
    try:
        anchor = obj.get("ysort_anchor_fraction")
        offset_px = obj.get("ysort_offset_px", 0) or 0
        if anchor is not None:
            return float(world_top_left_y) + float(sprite_height) * float(anchor) + float(
                offset_px
            )
    except Exception:
        pass

    try:
        aabb = obj.get("aabb")
        if isinstance(aabb, (tuple, list)) and len(aabb) == 4:
            return float(aabb[3])
    except Exception:
        pass

    return float(world_top_left_y) + float(sprite_height)


def placeable_sort_key(
    obj: Dict, *, baseline: float, z: int, order: Tuple[int, int] | int | None = None
):
    """Return a stable sort key for placeables.

    - baseline: primary y-sort value (lower draws first)
    - z: secondary z-index
    - order: stable tiebreaker (e.g., tile coords or instance id)
    """
    if order is None:
        tx = int(obj.get("x", 0))
        ty = int(obj.get("y", 0))
        order = (ty, tx)
    return (float(baseline), int(z), order)


__all__ = ["placeable_baseline", "placeable_sort_key"]

