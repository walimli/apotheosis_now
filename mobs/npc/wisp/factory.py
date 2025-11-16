from __future__ import annotations

from typing import Tuple

from constants import TILE_SIZE
from systems.mobs.core.species_loader import MobSpec
from .controller import WispController
from .model import WispModel
from .view import WispView


def create_wisp(
    next_id: int,
    spec: MobSpec,
    spawn_pos_px: Tuple[float, float],
    assets=None,
):
    model = WispModel(
        id=next_id,
        species_id=spec.id,
        x=float(spawn_pos_px[0]),
        y=float(spawn_pos_px[1]),
        hp_max=int(spec.stats.durability),
        hp_cur=int(spec.stats.durability),
        speed_px_s=float(spec.stats.speed_px_per_s),
    )
    footprint = (float(spec.assets.frame_width), float(spec.assets.frame_height))
    collider_rect = _resolve_collider_rect(spec, footprint)
    controller = WispController(model, footprint_px=footprint, collider_rect_px=collider_rect)
    view = WispView(
        model,
        (spec.assets.frame_width, spec.assets.frame_height),
        int(getattr(spec, "z_index", 0)),
    )
    return model, controller, view


def _resolve_collider_rect(
    spec: MobSpec,
    footprint: Tuple[float, float],
) -> Tuple[float, float, float, float]:
    collider = getattr(spec, "collider", None)
    if collider is None or getattr(collider, "aabb", None) is None:
        width_px = footprint[0] * 0.5
        height_px = footprint[1] * 0.6
        offset_x = (footprint[0] - width_px) / 2.0
        offset_y = footprint[1] - height_px
        return (width_px, height_px, offset_x, offset_y)

    aabb = collider.aabb
    width_px = float(aabb.width_tiles * TILE_SIZE)
    height_px = float(aabb.height_tiles * TILE_SIZE)
    anchor = getattr(collider, "anchor", "feet")
    if anchor == "feet":
        base_offset_x = (footprint[0] - width_px) / 2.0
        base_offset_y = footprint[1] - height_px
    else:
        base_offset_x = (footprint[0] - width_px) / 2.0
        base_offset_y = (footprint[1] - height_px) / 2.0

    offset_x = base_offset_x + float(aabb.offset_x_tiles * TILE_SIZE)
    offset_y = base_offset_y + float(aabb.offset_y_tiles * TILE_SIZE)
    return (width_px, height_px, offset_x, offset_y)

