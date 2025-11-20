"""ECS runtime bootstrap utilities for PlayState."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from ecs_core.components import Camera2DComponent
from ecs_core.entities.entities import EntityManager
from ecs_core.systems.aggressive_pathfinding.bootstrap import (
    AggressiveAIService,
    AggressivePathfindingManager,
    setup_aggressive_pathfinding,
)
from ecs_core.systems.animation.animation import AnimationSystem
from ecs_core.systems.attack import AttackSystem
from ecs_core.systems.controller import ControllerSystem
from ecs_core.systems.evolve import EvolveSystem
from ecs_core.systems.damage import DamageSystem
from ecs_core.systems.drops import DropsSystem
from ecs_core.systems.health import HealthSystem
from ecs_core.systems.hit_box import HitBoxSystem
from ecs_core.systems.movement import MovementSystem
from ecs_core.systems.lifeline import LifelineSystem
from ecs_core.systems.player_animation import PlayerAnimationSystem
from ecs_core.systems.pickup import PickupSystem
from ecs_core.systems.render import RenderSystem
from ecs_core.systems.speed import SpeedSystem
from ecs_core.systems.soul.soul import SoulSystem
from ecs_core.worlds.world import World
from services.display.display_system import DisplayService

from .services import PlayServices


@dataclass(frozen=True)
class ECSRuntime:
    """Container for ECS world references used by PlayState."""

    world: World
    entity_manager: EntityManager
    camera_entity: int
    render_system: RenderSystem
    controller_system: ControllerSystem
    animation_system: AnimationSystem
    speed_system: SpeedSystem
    movement_system: MovementSystem
    soul_system: SoulSystem
    evolve_system: EvolveSystem
    health_system: HealthSystem
    damage_system: DamageSystem
    drops_system: DropsSystem
    lifeline_system: LifelineSystem
    hit_box_system: HitBoxSystem
    player_animation_system: PlayerAnimationSystem
    attack_system: AttackSystem
    pickup_system: PickupSystem
    aggressive_pathfinding_manager: AggressivePathfindingManager
    aggressive_ai_service: AggressiveAIService


class _PathfindingPlayStateProxy:
    """Proxy exposing runtime attributes for aggressive pathfinding bootstrap."""

    def __init__(self, base_state: Any, world: World, movement_system: MovementSystem):
        self._base_state = base_state
        self.ecs_world = world
        self.movement_system = movement_system

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base_state, name)


def create_ecs_runtime(
    play_state: Any,
    display: DisplayService,
    services: PlayServices,
) -> ECSRuntime:
    """Construct the ECS runtime for PlayState."""
    world = World()
    entity_manager = EntityManager()

    camera_entity = entity_manager.create()
    camera_rect = pygame.Rect(0, 0, display.base_width, display.base_height)
    world.add(
        camera_entity,
        Camera2DComponent(rect=camera_rect, scale=1.0, scroll=(0.0, 0.0)),
    )

    render_system = RenderSystem(
        display.get_base_surface(),
        camera_entity,
        world,
    )

    controller_system = ControllerSystem()
    controller_system.world = world
    controller_system.input_service = None

    animation_system = AnimationSystem()
    animation_system.world = world

    movement_system = MovementSystem(world)
    speed_system = SpeedSystem(world)
    hit_box_system = HitBoxSystem(world, display=display, camera_entity=camera_entity)
    player_animation_system = PlayerAnimationSystem(
        world=world, camera_entity=camera_entity
    )
    attack_system = AttackSystem(world)
    attack_system.monster_factory = services.monster_factory
    pickup_system = PickupSystem(world)

    health_system = HealthSystem()
    health_system.world = world
    health_system.time_service = services.time_manager
    health_system.audio_service = services.audio_manager

    damage_system = DamageSystem(world)
    damage_system.movement_system = movement_system
    damage_system.health_system = health_system
    damage_system.time_service = services.time_manager

    drops_system = DropsSystem()
    drops_system.world = world
    drops_system.entity_manager = entity_manager
    drops_system.monster_factory = services.monster_factory
    pickup_system.movement_system = movement_system

    proxy = _PathfindingPlayStateProxy(play_state, world, movement_system)
    aggressive_manager, aggressive_service = setup_aggressive_pathfinding(proxy)
    controller_system.ai_service = aggressive_service

    soul_system = SoulSystem(
        world,
        services.time_manager,
        tile_size=getattr(services.world_renderer, "tile_size", 64),
    )

    evolve_system = EvolveSystem()
    evolve_system.world = world
    evolve_system.entity_manager = entity_manager
    evolve_system.time_service = services.time_manager

    lifeline_system = LifelineSystem()
    lifeline_system.world = world

    services.monster_factory.bind_world(world, entity_manager)

    return ECSRuntime(
        world=world,
        entity_manager=entity_manager,
        camera_entity=camera_entity,
        render_system=render_system,
        controller_system=controller_system,
        animation_system=animation_system,
        speed_system=speed_system,
        movement_system=movement_system,
        soul_system=soul_system,
        evolve_system=evolve_system,
        health_system=health_system,
        damage_system=damage_system,
        drops_system=drops_system,
        lifeline_system=lifeline_system,
        hit_box_system=hit_box_system,
        player_animation_system=player_animation_system,
        attack_system=attack_system,
        pickup_system=pickup_system,
        aggressive_pathfinding_manager=aggressive_manager,
        aggressive_ai_service=aggressive_service,
    )
