# systems/collision/collider.py
"""
High-performance collider data structure for 2D circle collision detection.
Optimized for 10k+ entities with minimal memory overhead.
"""

from dataclasses import dataclass
from typing import NamedTuple


# Layer bitmasks for collision filtering
class CollisionLayers:
    """Bitmasks for entity collision layers"""
    PLAYER = 1
    ENEMIES = 2
    PROJECTILES = 4
    WALLS = 8
    ITEMS = 16
    TRIGGERS = 32
    ALL = 0xFFFFFFFF  # All layers


@dataclass(frozen=True)
class Collider:
    """Immutable circle collider component
    
    Optimized for high-performance collision detection with minimal memory overhead.
    Uses named fields for cache-friendly access patterns.
    """
    entity_id: int          # Unique entity ID from game ECS
    diameter: int           # Circle diameter in pixels
    offset_x: int           # Offset from entity position in pixels
    offset_y: int           # Offset from entity position in pixels  
    layer: int              # Bitmask for collision filtering
    is_trigger: bool = False   # Events only, no physical resolution
    enabled: bool = True       # Toggle for LOD/pausing
    
    @property
    def radius(self) -> int:
        """Circle radius in pixels"""
        return self.diameter // 2
    
    def world_center(self, entity_x: int, entity_y: int) -> tuple[int, int]:
        """Calculate world center position of this collider"""
        return (entity_x + self.offset_x, entity_y + self.offset_y)
    
    def check_layer_compatible(self, other_layer: int) -> bool:
        """Check if this collider can collide with the given layer"""
        return bool(self.layer & other_layer)


class CollisionEvent(NamedTuple):
    """Lightweight collision event data structure"""
    entity_a: int
    entity_b: int
    normal_x: float  # Collision normal vector
    normal_y: float
    penetration: float  # How much overlap occurred
    is_trigger: bool = False


# Predefined collider templates for common entity types
class ColliderTemplates:
    """Pre-built collider templates for common game entities"""
    
    @staticmethod
    def player(diameter: int = 32, offset_x: int = 0, offset_y: int = 0) -> Collider:
        return Collider(
            entity_id=-1,  # Template - set entity_id when creating
            diameter=diameter,
            offset_x=offset_x,
            offset_y=offset_y,
            layer=CollisionLayers.PLAYER,
            is_trigger=False,
            enabled=True
        )
    
    @staticmethod
    def enemy(diameter: int = 24, offset_x: int = 0, offset_y: int = 0) -> Collider:
        return Collider(
            entity_id=-1,
            diameter=diameter,
            offset_x=offset_x,
            offset_y=offset_y,
            layer=CollisionLayers.ENEMIES,
            is_trigger=False,
            enabled=True
        )
    
    @staticmethod
    def projectile(diameter: int = 8, offset_x: int = 0, offset_y: int = 0) -> Collider:
        return Collider(
            entity_id=-1,
            diameter=diameter,
            offset_x=offset_x,
            offset_y=offset_y,
            layer=CollisionLayers.PROJECTILES,
            is_trigger=False,
            enabled=True
        )
    
    @staticmethod
    def item(diameter: int = 16, offset_x: int = 0, offset_y: int = 0) -> Collider:
        return Collider(
            entity_id=-1,
            diameter=diameter,
            offset_x=offset_x,
            offset_y=offset_y,
            layer=CollisionLayers.ITEMS,
            is_trigger=False,
            enabled=True
        )
    
    @staticmethod
    def wall(diameter: int = 64, offset_x: int = 0, offset_y: int = 0) -> Collider:
        return Collider(
            entity_id=-1,
            diameter=diameter,
            offset_x=offset_x,
            offset_y=offset_y,
            layer=CollisionLayers.WALLS,
            is_trigger=False,
            enabled=True
        )