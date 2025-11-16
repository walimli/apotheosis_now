"""Bootstrap utilities for constructing PlayState service dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.asset_loader import load_tilesheet
from services.audio_package import AudioManager
from services.display.display_system import DisplayService
from services.monster_factory import MonsterFactoryService
from services.notifications import NotificationService
from services.time import TimeManager
from services.ui.ui_manager import UIManager
from services.world_builder import WorldBuilder
from services.world_renderer import WorldRenderer


@dataclass(frozen=True)
class PlayServices:
    """Grouped dependencies required by PlayState."""

    tile_sheet: Any
    world_builder: WorldBuilder
    world_renderer: WorldRenderer
    monster_factory: MonsterFactoryService
    time_manager: TimeManager
    ui_manager: UIManager
    notifications: NotificationService
    audio_manager: AudioManager


def build_services(
    display: DisplayService,
    audio_manager: AudioManager,  # noqa: ARG001 - reserved for future wiring
    project_root: Path,
) -> PlayServices:
    """
    Construct the service layer used by PlayState.

    Returns a PlayServices dataclass so callers can copy assignments back to the
    PlayState instance without re-ordering initialization steps.
    """

    tile_sheet = load_tilesheet(asset_root=project_root / "assets" / "tiles")

    world_builder = WorldBuilder(seed=42, chunk_size=32)

    base_surface = display.get_base_surface()
    world_renderer = WorldRenderer(
        screen=base_surface,
        tile_sheet=tile_sheet,
        tile_size=64,
        chunk_size=32,
        world_builder=world_builder,
    )

    monster_factory = MonsterFactoryService(
        project_root=project_root,
        chunk_size=world_builder.chunk_size,
        tile_size=world_renderer.tile_size,
    )
    world_renderer.add_chunk_listener(monster_factory.handle_chunk_created)

    time_manager = TimeManager()
    monster_factory.attach_time_manager(time_manager)

    font_path = str(project_root / "assets" / "ui" / "fonts" / "system.ttf")
    ui_manager = UIManager(
        display,
        font_path=font_path,
        time_manager=time_manager,
    )

    notifications = NotificationService(
        project_root=project_root,
        display=display,
    )

    return PlayServices(
        tile_sheet=tile_sheet,
        world_builder=world_builder,
        world_renderer=world_renderer,
        monster_factory=monster_factory,
        time_manager=time_manager,
        ui_manager=ui_manager,
        notifications=notifications,
        audio_manager=audio_manager,
    )
