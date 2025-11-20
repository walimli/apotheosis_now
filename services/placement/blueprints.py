"\"\"\"Placement blueprint definitions and helpers.\"\"\""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from ecs_core.entities.crafted.glow_tree import GLOW_TREE_STAGES
from ecs_core.entities.crafted.crystal_colony import CRYSTAL_STAGES
from ecs_core.entities.crafted.skull_candle import CONFIG as SKULL_CANDLE_CONFIG
from ecs_core.entities.crafted.skull_shrine import CONFIG as SKULL_SHRINE_CONFIG
from ecs_core.entities.flora.sprout_common import SPRITE_ROOT


@dataclass(frozen=True)
class AnimationSpec:
    sheet_path: str
    columns: int
    rows: int
    frame_width: int
    frame_height: int
    fps: float = 6.0


@dataclass(frozen=True)
class PlacementBlueprint:
    """Static data describing how to visualize/place an item."""

    item_id: str
    entity_id: Optional[str]
    sprite_path: str
    scale: float = 1.0
    anchor: Tuple[float, float] = (0.5, 0.5)
    offset: Tuple[int, int] = (0, 0)
    animation: Optional[AnimationSpec] = None
    requires_player_tile: bool = False
    ignore_occupancy: bool = False
    placement_radius: int = 2


def _absolute(path: Path | str, project_root: Path) -> str:
    base = Path(path)
    if not base.is_absolute():
        base = project_root / base
    return str(base.resolve())


def _animation_from_stage(stage_anim, project_root: Path) -> Optional[AnimationSpec]:
    if stage_anim is None:
        return None
    frame_w, frame_h = stage_anim.frame_dimensions
    return AnimationSpec(
        sheet_path=_absolute(stage_anim.sheet_rel_path, project_root),
        columns=stage_anim.columns,
        rows=stage_anim.rows,
        frame_width=frame_w,
        frame_height=frame_h,
        fps=stage_anim.fps,
    )


def build_default_blueprints(project_root: Path) -> Dict[str, PlacementBlueprint]:
    """Return the default placement blueprints keyed by inventory item id."""

    root = Path(project_root)
    blueprints: Dict[str, PlacementBlueprint] = {}

    # Glow spores -> glow tree seedling
    glow_seedling = GLOW_TREE_STAGES["glow_seedling"]
    blueprints["glow_spore_coin"] = PlacementBlueprint(
        item_id="glow_spore_coin",
        entity_id=glow_seedling.entity_id,
        sprite_path=_absolute(glow_seedling.sprite_rel_path, root),
        scale=float(glow_seedling.scale),
        anchor=(0.5, 0.5),
        animation=_animation_from_stage(glow_seedling.animation, root),
        placement_radius=2,
    )

    # Crystal spores -> colony seed
    crystal_seedling = CRYSTAL_STAGES["crystal_seedling"]
    blueprints["crystal_coin"] = PlacementBlueprint(
        item_id="crystal_coin",
        entity_id=crystal_seedling.entity_id,
        sprite_path=_absolute(crystal_seedling.sprite_rel_path, root),
        scale=float(crystal_seedling.scale),
        anchor=(0.5, 0.7),
        animation=_animation_from_stage(crystal_seedling.animation, root),
        placement_radius=2,
    )

    # Skull wards
    blueprints["skull_candle_coin"] = PlacementBlueprint(
        item_id="skull_candle_coin",
        entity_id="skull_candle",
        sprite_path=_absolute(SKULL_CANDLE_CONFIG.sprite_rel_path, root),
        scale=float(SKULL_CANDLE_CONFIG.scale),
        anchor=(0.5, 0.7),
        animation=AnimationSpec(
            sheet_path=_absolute(SKULL_CANDLE_CONFIG.sprite_rel_path, root),
            columns=SKULL_CANDLE_CONFIG.columns,
            rows=SKULL_CANDLE_CONFIG.rows,
            frame_width=SKULL_CANDLE_CONFIG.sheet_size[0]
            // SKULL_CANDLE_CONFIG.columns,
            frame_height=SKULL_CANDLE_CONFIG.sheet_size[1]
            // SKULL_CANDLE_CONFIG.rows,
            fps=SKULL_CANDLE_CONFIG.fps,
        ),
        placement_radius=2,
    )

    blueprints["skull_shrine_coin"] = PlacementBlueprint(
        item_id="skull_shrine_coin",
        entity_id="skull_shrine",
        sprite_path=_absolute(SKULL_SHRINE_CONFIG.sprite_rel_path, root),
        scale=float(SKULL_SHRINE_CONFIG.scale),
        anchor=(0.5, 0.7),
        animation=AnimationSpec(
            sheet_path=_absolute(SKULL_SHRINE_CONFIG.sprite_rel_path, root),
            columns=SKULL_SHRINE_CONFIG.columns,
            rows=SKULL_SHRINE_CONFIG.rows,
            frame_width=SKULL_SHRINE_CONFIG.sheet_size[0]
            // SKULL_SHRINE_CONFIG.columns,
            frame_height=SKULL_SHRINE_CONFIG.sheet_size[1]
            // SKULL_SHRINE_CONFIG.rows,
            fps=SKULL_SHRINE_CONFIG.fps,
        ),
        placement_radius=2,
    )

    # Bedlam spores -> sprout entity (non-crafted)
    blueprints["spore_coin"] = PlacementBlueprint(
        item_id="spore_coin",
        entity_id="sprout",
        sprite_path=_absolute(SPRITE_ROOT / "flower_1.png", root),
        scale=1.0,
        anchor=(0.5, 0.5),
        placement_radius=2,
    )

    return blueprints


__all__ = ["PlacementBlueprint", "AnimationSpec", "build_default_blueprints"]
