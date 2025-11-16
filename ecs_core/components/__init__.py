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
    Evolve,
    Controller,
    ControllerType,
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

from .components import (
    Renderable,
)

# Animation components
from .animation_components import (
    Animation,
    AnimationState,
)

# Collision component
from .collider import Collider
from .aggressive_components import AggressivePathfindingComponent

from ecs_core.systems.soul.safe_zone import SafeZoneComponent

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
    "Evolve",
    "Controller",
    "ControllerType",
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
    # Animation
    "Animation",
    "AnimationState",
    # Collision
    "Collider",
    # Aggressive AI
    "AggressivePathfindingComponent",
    # Soul/Safe Zones
    "SafeZoneComponent",
]
