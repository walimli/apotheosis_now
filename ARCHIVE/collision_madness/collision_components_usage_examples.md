# Collision Components Usage Examples

Comprehensive examples showing how to use the new collision components with your ECS system. These examples demonstrate the patterns used throughout your game architecture.

## Basic Setup

```python
from systems.ecs_core.worlds.world import World
from systems.ecs_core.entities.entities import EntityManager
from components.collision_component import (
    CollisionEnabled, CollisionShape, CollisionLayer, CollisionTemplates,
    add_collision_to_entity, remove_collision_from_entity
)
from components.entity_classes import Player, Mob, NPC, Plant, Object
from systems.ecs_core.components.components import Position, Velocity

# Setup ECS world
world = World()
entity_manager = EntityManager()
```

## Quick Start - Adding Collision to Any Entity

### Method 1: Convenience Function (Recommended)

```python
# Create player entity with collision
player_entity = entity_manager.create()
world.add(player_entity, Position(100, 200))
world.add(player_entity, Velocity(0, 0))

# Add collision using convenience function
add_collision_to_entity(world, player_entity, entity_class=Player, diameter=32)

# Now player participates in collision detection
```

### Method 2: Manual Component Addition

```python
# Create enemy entity with collision
enemy_entity = entity_manager.create()
world.add(enemy_entity, Position(300, 400))
world.add(enemy_entity, Velocity(10, 0))

# Add collision components manually
world.add(enemy_entity, CollisionEnabled())  # Marker component
world.add(enemy_entity, CollisionShape(
    diameter=24,
    layer=CollisionLayers.ENEMIES | CollisionLayers.PLAYER
))
world.add(enemy_entity, CollisionLayer(entity_class=Mob))

# Enemy now participates in collision detection
```

## Entity Type Examples

### Player Entity

```python
# Standard player setup
player = entity_manager.create()
world.add(player, Position(100, 200))
world.add(player, Velocity(0, 0))

# Player collision (collides with enemies and items)
add_collision_to_entity(world, player, entity_class=Player, diameter=32)
```

### Enemy/Mob Entities

```python
# Enemy setup
enemy = entity_manager.create()
world.add(enemy, Position(300, 150))
world.add(enemy, Velocity(15, 0))

# Enemy collision (collides with player and walls)
add_collision_to_entity(world, enemy, entity_class=Mob, diameter=28)

# Alternative: Using templates directly
world.add(enemy, CollisionEnabled())
world.add(enemy, CollisionTemplates.enemy_collision(diameter=28))
```

### Projectile Entities

```python
# Projectile setup
projectile = entity_manager.create()
world.add(projectile, Position(100, 200))
world.add(projectile, Velocity(50, 0))

# Projectile collision (hits enemies and walls)
world.add(projectile, CollisionEnabled())
world.add(projectile, CollisionTemplates.projectile_collision(diameter=8))
```

### Wall/Obstacle Entities

```python
# Wall setup
wall = entity_manager.create()
world.add(wall, Position(500, 300))

# Wall collision (blocks player and enemies)
add_collision_to_entity(world, wall, entity_class=Object, diameter=64)

# Alternative: Using wall template
world.add(wall, CollisionEnabled())
world.add(wall, CollisionTemplates.wall_collision(diameter=64))
```

### Pickup Item Entities

```python
# Item setup
item = entity_manager.create()
world.add(item, Position(250, 400))

# Item collision (detected by player for pickup)
world.add(item, CollisionEnabled())
world.add(item, CollisionTemplates.item_collision(diameter=16))
```

### Trigger Zone Entities

```python
# Trigger setup
trigger = entity_manager.create()
world.add(trigger, Position(400, 200))

# Trigger collision (generates events but doesn't block)
world.add(trigger, CollisionEnabled())
world.add(trigger, CollisionTemplates.trigger_collision(diameter=48))
```

## ECS System Patterns

### Collision Query Systems

```python
def collision_movement_system(world, delta_time):
    """Movement system that handles collision resolution"""
    
    # Get all entities with collision
    for entity, collision_shape, position in world.view(CollisionEnabled, CollisionShape, Position):
        # Get collision settings
        settings = world.get(entity, CollisionSettings)
        
        # Skip if collision disabled
        if settings and not settings.enabled:
            continue
        
        # Get velocity
        velocity = world.get(entity, Velocity)
        if velocity:
            # Update position
            position.x += velocity.vx * delta_time
            position.y += velocity.vy * delta_time
```

### Player-Specific System

```python
def player_input_system(world, input_handler):
    """System that handles player movement and collision"""
    
    # Query only players with collision
    for entity, player_marker, position, collision_shape in world.view(Player, CollisionEnabled, Position, CollisionShape):
        # Get player input
        move_input = input_handler.get_movement(entity)
        
        # Update velocity based on input
        velocity = world.get(entity, Velocity)
        if velocity:
            velocity.vx = move_input.x * 100.0  # 100 pixels/sec
            velocity.vy = move_input.y * 100.0

def enemy_ai_system(world):
    """System that handles enemy AI and collision"""
    
    # Query only mobs with collision
    for entity, mob_marker, position, collision_shape in world.view(Mob, CollisionEnabled, Position, CollisionShape):
        # Simple enemy AI
        velocity = world.get(entity, Velocity)
        if velocity:
            # Move toward player
            player_pos = get_nearest_player_position(position)
            if player_pos:
                dx = player_pos.x - position.x
                dy = player_pos.y - position.y
                distance = (dx*dx + dy*dy)**0.5
                
                if distance > 0:
                    velocity.vx = (dx / distance) * 50.0  # 50 pixels/sec
                    velocity.vy = (dy / distance) * 50.0
```

### Collision Event Handling

```python
def collision_event_system(world):
    """System that handles collision events"""
    
    # Query collision events
    for entity, event in world.view(CollisionEvent):
        if event.collision_type == "enter":
            handle_collision_start(event)
        elif event.collision_type == "stay":
            handle_collision_continue(event)
        elif event.collision_type == "exit":
            handle_collision_end(event)
        
        # Remove event after processing (one-time events)
        world.remove(entity, CollisionEvent)

def handle_collision_start(event):
    """Handle collision start events"""
    print(f"Collision detected: {event.entity_a} <-> {event.entity_b}")
    
    # Example: Player picks up item
    if is_player(event.entity_a) and is_item(event.entity_b):
        pickup_item(event.entity_b)
    elif is_enemy(event.entity_a) and is_player(event.entity_b):
        damage_player(event.entity_b)
```

## Advanced Collision Patterns

### Dynamic Entity Creation

```python
def spawn_enemy_with_collision(world, position, enemy_type="basic"):
    """Spawn an enemy with collision components"""
    
    enemy = entity_manager.create()
    world.add(enemy, Position(position.x, position.y))
    world.add(enemy, Velocity(0, 0))
    
    # Add collision based on enemy type
    if enemy_type == "basic":
        add_collision_to_entity(world, enemy, entity_class=Mob, diameter=24)
    elif enemy_type == "boss":
        add_collision_to_entity(world, enemy, entity_class=Mob, diameter=64)
    elif enemy_type == "fast":
        add_collision_to_entity(world, enemy, entity_class=Mob, diameter=16)
    
    return enemy

# Usage
boss = spawn_enemy_with_collision(world, (500, 300), "boss")
```

### Collision Layer Management

```python
def create_team_collision(world, team_a_entities, team_b_entities):
    """Create collision configuration for team vs team"""
    
    # Team A collides with Team B but not within team
    team_a_layer = 1  # CollisionLayers.PLAYER
    team_b_layer = 2  # CollisionLayers.ENEMIES
    
    # Team A setup
    for entity in team_a_entities:
        if world.get(entity, CollisionEnabled):
            shape = world.get(entity, CollisionShape)
            if shape:
                world.remove(entity, CollisionShape)
                world.add(entity, CollisionShape(
                    diameter=shape.diameter,
                    layer=team_a_layer | team_b_layer,  # Collide with team B
                    offset_x=shape.offset_x,
                    offset_y=shape.offset_y
                ))
    
    # Team B setup  
    for entity in team_b_entities:
        if world.get(entity, CollisionEnabled):
            shape = world.get(entity, CollisionShape)
            if shape:
                world.remove(entity, CollisionShape)
                world.add(entity, CollisionShape(
                    diameter=shape.diameter,
                    layer=team_b_layer | team_a_layer,  # Collide with team A
                    offset_x=shape.offset_x,
                    offset_y=shape.offset_y
                ))
```

### Dynamic Collision Enabling/Disabling

```python
def toggle_collision_for_entity(world, entity_id, enabled):
    """Enable or disable collision for an entity"""
    
    if enabled:
        # Enable collision
        world.add(entity_id, CollisionEnabled())
    else:
        # Disable collision
        world.remove(entity_id, CollisionEnabled)
        # Remove collision events too
        world.remove(entity_id, CollisionEvent)

def make_entity_ghost(world, entity_id):
    """Make entity pass through everything (like going through walls)"""
    
    # Remove collision components
    remove_collision_from_entity(world, entity_id)
    
    # Alternative: Modify layer to collide with nothing
    shape = world.get(entity_id, CollisionShape)
    if shape:
        world.remove(entity_id, CollisionShape)
        world.add(entity_id, CollisionShape(
            diameter=shape.diameter,
            layer=0,  # Collides with nothing
            offset_x=shape.offset_x,
            offset_y=shape.offset_y
        ))
```

### Component Queries for Performance

```python
def efficient_collision_system(world):
    """Efficient collision system using targeted queries"""
    
    # Get only entities that have collision and position
    for entity, collision_enabled, position in world.view(CollisionEnabled, Position):
        # Process entity...
        pass
    
    # Get only players with collision
    for entity, player, position in world.view(Player, CollisionEnabled, Position):
        # Process player...
        pass
    
    # Get collision events
    for entity, event in world.view(CollisionEvent):
        # Handle event...
        pass
    
    # Get entities that can be queried (fast lookup)
    from components.collision_component import get_entities_with_collision
    collision_entities = get_entities_with_collision(world)
    print(f"Found {len(collision_entities)} entities with collision")
```

## Integration with Existing Systems

### Renderer Integration

```python
def collision_renderer_system(world, renderer):
    """Render collision shapes for debugging"""
    
    # Render collision circles for all collision-enabled entities
    for entity, collision_shape, position in world.view(CollisionEnabled, CollisionShape, Position):
        # Draw collision circle (debug visualization)
        if renderer.debug_mode:
            center = collision_shape.world_center(position.x, position.y)
            renderer.draw_circle(center[0], center[1], collision_shape.radius, (255, 0, 0))
```

### Physics Integration

```python
def physics_collision_system(world, physics_world):
    """Integrate collision with existing physics system"""
    
    # Query all collision-enabled entities
    for entity, collision_shape, position in world.view(CollisionEnabled, CollisionShape, Position):
        # Update physics world with collision data
        physics_world.update_entity_collision(
            entity, 
            collision_shape,
            position
        )
```

### Sound Integration

```python
def sound_collision_system(world, sound_manager):
    """Play sounds based on collision events"""
    
    # Query collision events
    for entity, event in world.view(CollisionEvent):
        if event.collision_type == "enter":
            # Play collision sound
            if is_player_hitting_wall(event):
                sound_manager.play_sound("player_wall_hit")
            elif is_enemy_hitting_player(event):
                sound_manager.play_sound("enemy_attack")
        
        # Remove processed event
        world.remove(entity, CollisionEvent)
```

## Cleanup and Best Practices

```python
def cleanup_destroyed_entities(world, destroyed_entities):
    """Clean up collision components when entities are destroyed"""
    
    for entity_id in destroyed_entities:
        # Remove all collision-related components
        remove_collision_from_entity(world, entity_id)

def optimize_collision_world(world):
    """Optimize collision system performance"""
    
    # Remove entities without Position component
    collision_entities = world.entities_with(CollisionEnabled)
    for entity in collision_entities:
        if not world.get(entity, Position):
            remove_collision_from_entity(world, entity)
            continue
        
        # Clean up disabled collisions
        settings = world.get(entity, CollisionSettings)
        if settings and not settings.enabled:
            remove_collision_from_entity(world, entity)
```

## Performance Tips

1. **Use Targeted Queries**: Always query specific components you need
2. **Batch Operations**: Process multiple entities in one system
3. **Remove Unused Components**: Clean up collision from destroyed entities
4. **Leverage Layer Filtering**: Use collision layers to reduce unnecessary checks
5. **Profile Collision Counts**: Monitor how many collision events are generated

This collision component system seamlessly integrates with your existing ECS patterns while providing the high-performance collision detection you need.