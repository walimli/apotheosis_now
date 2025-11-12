# systems/collision/__init__.py
"""
High-Performance 2D Circle Collision System

A modular collision detection system optimized for games with 10k+ entities.
Features uniform grid spatial partitioning, layer-based filtering, and comprehensive
debugging tools.

Main Classes:
- CollisionSystem: Main collision detection system
- Collider: Immutable circle collider data structure
- CollisionEvent: Collision event data structure
- CollisionDebugVisualizer: Debug visualization tools
- PerformanceProfiler: Performance monitoring tools

Usage:
    from systems.collision import CollisionSystem, Collider, CollisionLayers
    
    # Create collision system
    collision_system = CollisionSystem(world_width=2048, world_height=2048)
    
    # Register entities
    collider = Collider(1, 32, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
    collision_system.register(1, collider, (100, 200))
    
    # Run collision detection
    collisions = collision_system.update()
"""

from .collider import (
    Collider, 
    CollisionEvent, 
    CollisionLayers, 
    ColliderTemplates
)

from .collision_math import (
    circle_collide,
    circle_collision_info,
    resolve_circle_overlap,
    point_in_circle,
    circle_line_intersection,
    raycast_circle,
    SpatialGrid
)

from .collision_system import CollisionSystem

from .debug_visualization import (
    CollisionDebugVisualizer,
    PerformanceProfiler,
    DEBUG_KEYS
)

# Version information
__version__ = "1.0.0"
__author__ = "Collision System Team"
__description__ = "High-Performance 2D Circle Collision Detection System"

# Package metadata
__all__ = [
    # Core classes
    'CollisionSystem',
    'Collider',
    'CollisionEvent',
    
    # Data structures
    'CollisionLayers',
    'ColliderTemplates',
    'SpatialGrid',
    
    # Mathematics
    'circle_collide',
    'circle_collision_info',
    'resolve_circle_overlap',
    'point_in_circle',
    'circle_line_intersection',
    'raycast_circle',
    
    # Debug tools
    'CollisionDebugVisualizer',
    'PerformanceProfiler',
    'DEBUG_KEYS',
    
    # Version info
    '__version__',
    '__author__',
    '__description__'
]

# Convenience imports
CollisionLayers = CollisionLayers
Templates = ColliderTemplates