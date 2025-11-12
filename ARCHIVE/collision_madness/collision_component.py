# components/collision_component.py
"""
ECS collision components that bridge the high-performance collision system
with your ECS World architecture.

Components follow the frozen dataclass pattern used throughout your ECS system,
allowing entities to be easily configured for collision detection.
"""

from dataclasses import dataclass
from typing import Optional
from systems.collision import CollisionLayers


# ==================== CORE COLLISION COMPONENTS ====================

@dataclass(frozen=True)
class CollisionEnabled:
    """Marker component that enables collision detection for an entity
    
    Add this component to any entity that should participate in collision detection.
    Combine with CollisionShape to define the collision shape.
    
    Usage:
        world.add(entity, CollisionEnabled())
        world.add(entity, CollisionShape(diameter=32, layer=CollisionLayers.PLAYER))
    """
    pass


@dataclass(frozen=True)
class CollisionShape:
    """Collision shape component for circular colliders
    
    Defines the collision properties for an entity. Used with CollisionEnabled
    to create entities that participate in collision detection.
    
    Args:
        diameter: Collision circle diameter in pixels
        offset_x: Horizontal offset from entity position (for non-centered colliders)
        offset_y: Vertical offset from entity position (for non-centered colliders) 
        layer: Collision layer bitmask (from CollisionLayers)
        is_trigger: If True, generates events but doesn't block movement
        radius_override: Optional radius override (diameter // 2 if not specified)
    
    Usage:
        # Standard player collision
        world.add(entity, CollisionShape(
            diameter=32, 
            layer=CollisionLayers.PLAYER | CollisionLayers.ENEMIES
        ))
        
        # Offset collision box (e.g., for tall entities)
        world.add(entity, CollisionShape(
            diameter=24, 
            offset_y=-8,
            layer=CollisionLayers.PLAYER
        ))
    """
    diameter: int
    layer: int = CollisionLayers.PLAYER | CollisionLayers.ENEMIES
    offset_x: int = 0
    offset_y: int = 0
    is_trigger: bool = False
    radius_override: Optional[int] = None
    
    @property
    def radius(self) -> int:
        """Get collision radius"""
        if self.radius_override is not None:
            return self.radius_override
        return self.diameter // 2
    
    def world_center(self, entity_x: float, entity_y: float) -> tuple[float, float]:
        """Calculate world center position for this collision shape
        
        Args:
            entity_x: Entity's world X position
            entity_y: Entity's world Y position
            
        Returns:
            Tuple of (world_x, world_y) for collision center
        """
        return (entity_x + self.offset_x, entity_y + self.offset_y)


@dataclass(frozen=True)
class CollisionLayer:
    """Collision layer component that integrates with entity_classes
    
    Links an entity's class to collision layers, making collision filtering
    more semantic and easier to manage.
    
    Args:
        entity_class: The entity class (from entity_classes.py)
        custom_layer: Optional custom layer bitmask (defaults based on entity_class)
    
    Usage:
        from components.entity_classes import Player, Mob
        
        # Player uses PLAYER collision layer
        world.add(entity, CollisionLayer(entity_class=Player))
        
        # Mob uses ENEMIES collision layer
        world.add(enemy_entity, CollisionLayer(entity_class=Mob))
        
        # Custom layer combination
        world.add(entity, CollisionLayer(
            entity_class=Player, 
            custom_layer=CollisionLayers.PLAYER | CollisionLayers.WALLS
        ))
    """
    entity_class: object
    custom_layer: Optional[int] = None
    
    def __post_init__(self):
        # Auto-assign collision layer based on entity class if not custom layer
        if self.custom_layer is None:
            from components.entity_classes import Player, Mob, NPC, Plant, Object
            
            if self.entity_class == Player:
                layer = CollisionLayers.PLAYER
            elif self.entity_class == Mob:
                layer = CollisionLayers.ENEMIES
            elif self.entity_class == NPC:
                layer = CollisionLayers.ENEMIES  # NPCs collide like enemies by default
            elif self.entity_class == Plant:
                layer = CollisionLayers.WALLS  # Plants block movement by default
            elif self.entity_class == Object:
                layer = CollisionLayers.WALLS  # Objects block movement by default
            else:
                layer = CollisionLayers.PLAYER  # Default fallback
            
            # Update the custom_layer using object.__setattr__ since it's frozen
            object.__setattr__(self, 'custom_layer', layer)
    
    @property
    def layer(self) -> int:
        """Get the collision layer bitmask"""
        return self.custom_layer or CollisionLayers.PLAYER


@dataclass(frozen=True)
class CollisionEvent:
    """Collision event component for reactive collision handling
    
    Created and managed by the collision system. Systems can query for these
    to respond to collision events in real-time.
    
    Args:
        entity_a: First entity in collision
        entity_b: Second entity in collision  
        normal_x: Collision normal X direction (-1.0 to 1.0)
        normal_y: Collision normal Y direction (-1.0 to 1.0)
        penetration: Overlap distance in pixels
        is_trigger: True if this is a trigger collision
        collision_type: Type of collision ("enter", "stay", "exit")
    
    Usage:
        # Systems can query collision events
        for entity, event in world.view(CollisionEvent):
            if event.collision_type == "enter":
                handle_collision_start(event)
            elif event.collision_type == "stay":
                handle_collision_continue(event)
    """
    entity_a: int
    entity_b: int
    normal_x: float
    normal_y: float
    penetration: float
    is_trigger: bool = False
    collision_type: str = "enter"  # "enter", "stay", "exit"


@dataclass(frozen=True)
class CollisionSettings:
    """Optional collision configuration component
    
    Allows per-entity customization of collision behavior.
    
    Args:
        enabled: Whether collision is currently enabled
        collision_callback: Optional callback for collision events
        lod_enabled: Whether LOD optimization is enabled
        lod_distance: Distance threshold for LOD
    
    Usage:
        world.add(entity, CollisionSettings(
            enabled=True,
            lod_enabled=True,
            lod_distance=512
        ))
    """
    enabled: bool = True
    collision_callback: Optional[object] = None
    lod_enabled: bool = True
    lod_distance: int = 512


# ==================== COLLISION COMPONENT TEMPLATES ====================

class CollisionTemplates:
    """Collision component templates following your existing patterns
    
    Provides convenient factory methods for common collision configurations.
    Similar to how your ECS system provides convenient component creation.
    """
    
    @staticmethod
    def player_collision(diameter: int = 32) -> CollisionShape:
        """Create collision shape for player entities
        
        Args:
            diameter: Collision diameter (default: 32px)
            
        Returns:
            CollisionShape configured for player collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=CollisionLayers.PLAYER | CollisionLayers.ENEMIES
        )
    
    @staticmethod
    def enemy_collision(diameter: int = 24) -> CollisionShape:
        """Create collision shape for enemy/mob entities
        
        Args:
            diameter: Collision diameter (default: 24px)
            
        Returns:
            CollisionShape configured for enemy collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=CollisionLayers.ENEMIES | CollisionLayers.PLAYER
        )
    
    @staticmethod
    def projectile_collision(diameter: int = 8) -> CollisionShape:
        """Create collision shape for projectiles
        
        Args:
            diameter: Collision diameter (default: 8px)
            
        Returns:
            CollisionShape configured for projectile collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=CollisionLayers.PROJECTILES | CollisionLayers.ENEMIES
        )
    
    @staticmethod
    def wall_collision(diameter: int = 64) -> CollisionShape:
        """Create collision shape for walls/obstacles
        
        Args:
            diameter: Collision diameter (default: 64px)
            
        Returns:
            CollisionShape configured for wall collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=CollisionLayers.WALLS
        )
    
    @staticmethod
    def item_collision(diameter: int = 16) -> CollisionShape:
        """Create collision shape for pickable items
        
        Args:
            diameter: Collision diameter (default: 16px)
            
        Returns:
            CollisionShape configured for item collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=CollisionLayers.ITEMS | CollisionLayers.PLAYER
        )
    
    @staticmethod
    def trigger_collision(diameter: int = 32, layer: int = CollisionLayers.TRIGGERS) -> CollisionShape:
        """Create collision shape for trigger zones
        
        Args:
            diameter: Collision diameter (default: 32px)
            layer: Trigger collision layer (default: TRIGGERS)
            
        Returns:
            CollisionShape configured for trigger collisions
        """
        return CollisionShape(
            diameter=diameter,
            layer=layer,
            is_trigger=True
        )
    
    @staticmethod
    def from_entity_class(entity_class: object, **kwargs) -> CollisionShape:
        """Create collision shape based on entity class
        
        Args:
            entity_class: Entity class from entity_classes.py
            **kwargs: Additional collision shape parameters
            
        Returns:
            CollisionShape configured for the entity class
        """
        from components.entity_classes import Player, Mob, NPC, Plant, Object
        
        if entity_class == Player:
            return CollisionTemplates.player_collision(**kwargs)
        elif entity_class in [Mob, NPC]:
            return CollisionTemplates.enemy_collision(**kwargs)
        elif entity_class == Plant:
            return CollisionTemplates.wall_collision(**kwargs)
        elif entity_class == Object:
            return CollisionTemplates.wall_collision(**kwargs)
        else:
            # Default fallback
            return CollisionShape(
                diameter=kwargs.get('diameter', 32),
                layer=kwargs.get('layer', CollisionLayers.PLAYER),
                offset_x=kwargs.get('offset_x', 0),
                offset_y=kwargs.get('offset_y', 0),
                is_trigger=kwargs.get('is_trigger', False)
            )


# ==================== CONVENIENCE FUNCTIONS ====================

def add_collision_to_entity(world, entity, entity_class=None, diameter: int = 32, **kwargs):
    """Convenience function to add collision to any entity
    
    Args:
        world: ECS World instance
        entity: Entity to add collision to
        entity_class: Entity class from entity_classes.py (optional)
        diameter: Collision diameter (default: 32px)
        **kwargs: Additional collision parameters
    """
    # Add collision enabled marker
    world.add(entity, CollisionEnabled())
    
    # Add collision shape
    if entity_class:
        collision_shape = CollisionTemplates.from_entity_class(entity_class, diameter=diameter, **kwargs)
    else:
        collision_shape = CollisionShape(diameter=diameter, **kwargs)
    
    world.add(entity, collision_shape)
    
    # Add collision layer if entity class provided
    if entity_class:
        world.add(entity, CollisionLayer(entity_class=entity_class))


def remove_collision_from_entity(world, entity):
    """Convenience function to remove all collision components from an entity
    
    Args:
        world: ECS World instance
        entity: Entity to remove collision from
    """
    from systems.ecs_core.worlds.world import World
    
    if isinstance(world, World):
        world.remove(entity, CollisionEnabled)
        world.remove(entity, CollisionShape)
        world.remove(entity, CollisionLayer)
        world.remove(entity, CollisionSettings)
        world.remove(entity, CollisionEvent)


# ==================== ECS SYSTEM INTEGRATION HELPERS ====================

def get_entities_with_collision(world):
    """Get all entities that have collision enabled
    
    Args:
        world: ECS World instance
        
    Returns:
        List of entity IDs with collision enabled
    """
    from systems.ecs_core.worlds.world import World
    
    if isinstance(world, World):
        return world.entities_with(CollisionEnabled, CollisionShape)
    return []


def get_collision_shape_for_entity(world, entity):
    """Get collision shape for a specific entity
    
    Args:
        world: ECS World instance
        entity: Entity ID
        
    Returns:
        CollisionShape component or None
    """
    from systems.ecs_core.worlds.world import World
    
    if isinstance(world, World):
        return world.get(entity, CollisionShape)
    return None


# Export all components and templates
__all__ = [
    # Core components
    'CollisionEnabled',
    'CollisionShape', 
    'CollisionLayer',
    'CollisionEvent',
    'CollisionSettings',
    
    # Templates
    'CollisionTemplates',
    
    # Convenience functions
    'add_collision_to_entity',
    'remove_collision_from_entity',
    'get_entities_with_collision',
    'get_collision_shape_for_entity'
]