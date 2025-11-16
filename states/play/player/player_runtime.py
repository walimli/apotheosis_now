"""Player bootstrap helpers for PlayState."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from ecs_core.components import Camera2DComponent, Controller, Health, Position, Soul
from ecs_core.entities.player.player_core import spawn_player
from services.display.display_system import DisplayService
from services.inventory import Inventory
from services.inventory.factory import create_player_inventory
from services.inventory.lock_state import InventoryLockState
from services.notifications import NotificationService
from services.progression import Progression
from services.ui.ui_manager import UIManager

from states.play.bootstrap import ECSRuntime


class HealthView:
    """Adapter exposing legacy health attributes for UI code."""

    def __init__(self, component: Optional[Health]) -> None:
        self._component = component

    @property
    def max_hp(self) -> int:
        return int(self._value("max_health", fallback="max_hp"))

    @property
    def current_hp(self) -> int:
        return int(self._value("current_health", fallback="current_hp"))

    def _value(self, primary: str, *, fallback: Optional[str] = None) -> float:
        component = self._component
        if component is None:
            return 0.0
        if hasattr(component, primary):
            return getattr(component, primary)
        if fallback and hasattr(component, fallback):
            return getattr(component, fallback)
        return 0.0


@dataclass(frozen=True)
class PlayerModelBindings:
    health: HealthView
    soul: Soul | None
    progression: Progression


@dataclass(frozen=True)
class PlayerBindings:
    inventory: Inventory
    lock_state: InventoryLockState
    model: PlayerModelBindings


@dataclass(frozen=True)
class PlayerRuntime:
    player_entity: int
    bindings: PlayerBindings


def spawn_player_runtime(
    *,
    play_state: object,
    ecs_runtime: ECSRuntime,
    display: DisplayService,
    ui_manager: UIManager,
    notifications: Optional[NotificationService] = None,
) -> PlayerRuntime:
    """Create the player entity and bind UI/inventory models."""
    world = ecs_runtime.world
    entity_manager = ecs_runtime.entity_manager

    player_entity = spawn_player(world, entity_manager)
    controller = world.get(player_entity, Controller)
    ecs_runtime.controller_system.register_entity(player_entity, controller)
    ecs_runtime.aggressive_pathfinding_manager.set_player_entity(player_entity)

    player_position = world.get(player_entity, Position)
    if player_position:
        target_x = (
            player_position.render_x
            if player_position.render_x is not None
            else float(player_position.x)
        )
        target_y = (
            player_position.render_y
            if player_position.render_y is not None
            else float(player_position.y)
        )
        display.update_camera((target_x, target_y), 0.0)
        _sync_camera_component_from_display(display, world, ecs_runtime.camera_entity)

    bindings = _create_player_bindings(world, player_entity)
    ui_manager.attach_play_state(
        play_state,
        player=bindings,
        lock_state=bindings.lock_state,
    )
    if notifications is not None:
        notifications.attach_progression(bindings.model.progression)

    return PlayerRuntime(player_entity=player_entity, bindings=bindings)


def _create_player_bindings(world, player_entity: int) -> PlayerBindings:
    inventory = create_player_inventory()
    lock_state = InventoryLockState()
    health_component = world.get(player_entity, Health)
    soul_component = world.get(player_entity, Soul)
    progression = Progression()
    model = PlayerModelBindings(
        health=HealthView(health_component),
        soul=soul_component,
        progression=progression,
    )
    return PlayerBindings(
        inventory=inventory,
        lock_state=lock_state,
        model=model,
    )


def _sync_camera_component_from_display(
    display: DisplayService,
    world,
    camera_entity: int,
) -> None:
    camera_rect: Optional[pygame.Rect] = display.get_camera_rect()
    if camera_rect is None:
        return
    rect = camera_rect.copy()
    scale = display.get_camera_scale()
    world.add(
        camera_entity,
        Camera2DComponent(
            rect=rect,
            scale=scale,
            scroll=(rect.left, rect.top),
        ),
    )
