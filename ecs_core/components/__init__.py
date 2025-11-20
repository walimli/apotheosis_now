# ECS Components Module
# This module exports all ECS components for easy importing

# Core physics and movement components
from .components import (
    Speed,
    Velocity,
    Position,
)

# Game logic components
from .components import (
    Health,
    Soul,
    Drops,
    PickupComponent,
    Evolve,
    Controller,
    ControllerType,
    Lifeline,
    Damage,
)

# Item and interaction components
from .components import (
    HeldItem,
    Harvestable,
)

# Entity marker components
from .entity_classes import (
    Player,
    Mob,
    NPC,
    Plant,
    Object,
)

# Rendering components
from .rendering_components import (
    Camera2DComponent,
    VoidVisualComponent,
    TerrainChunkComponent,
    RenderableEntityComponent,
)

from .components import Renderable
from .hit_box import HitBox
from .attack import AttackComponent
from .static_body import StaticBody

# Animation components
from .animation_components import (
    Animation,
    AnimationState,
)

# Collision component
from .collider import Collider
from .aggressive_components import AggressivePathfindingComponent
from .player_animation import PlayerAnimationHandle
from ecs_core.systems.soul.safe_zone import SafeZoneComponent
from .protection import ProtectionZoneComponent

# Define what gets exported when using "from ecs_core.components import *"
__all__ = [
    # Core physics and movement
    "Speed",
    "Velocity",
    "Position",
    # Game logic
    "Health",
    "Soul",
    "Drops",
    "PickupComponent",
    "Evolve",
    "Controller",
    "ControllerType",
    "Lifeline",
    "Damage",
    # Items and interaction
    "HeldItem",
    "Harvestable",
    # Entity markers
    "Player",
    "Mob",
    "NPC",
    "Plant",
    "Object",
    # Rendering
    "Camera2DComponent",
    "VoidVisualComponent",
    "TerrainChunkComponent",
    "RenderableEntityComponent",
    "HitBox",
    # Combat
    "AttackComponent",
    # Animation
    "Animation",
    "AnimationState",
    # Collision
    "Collider",
    "PlayerAnimationHandle",
    # Static bodies
    "StaticBody",
    # Aggressive AI
    "AggressivePathfindingComponent",
    # Soul/Safe Zones
    "SafeZoneComponent",
    # Protection
    "ProtectionZoneComponent",
]
