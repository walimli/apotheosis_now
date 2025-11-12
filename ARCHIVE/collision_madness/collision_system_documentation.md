# Collision System Documentation

A high-performance, modular 2D circle collision detection system optimized for games with 10k+ entities. Built with Python and designed for seamless integration into ECS systems.

## Overview

The collision system provides:

- **High Performance**: Optimized for 10k+ entities at 60FPS
- **Dual Performance Modes**: Efficient for both sparse (daytime) and dense (nighttime) scenarios
- **Modular Design**: No dependencies on rendering, ECS, or game logic
- **Uniform Grid Spatial Partitioning**: O(n) broad-phase collision detection
- **Layer-Based Filtering**: Bitwise collision filtering for 90%+ performance improvement
- **Comprehensive Debug Tools**: Visualization and performance profiling

## Architecture

```
systems/collision/
├── collider.py                 # Core data structures and templates
├── collision_math.py           # Circle collision mathematics
├── collision_system.py         # Main collision system class
├── debug_visualization.py      # Debug tools and visualization
└── test_collision_system.py    # Comprehensive test suite
```

## Quick Start

### Basic Usage

```python
from systems.collision import CollisionSystem, Collider, CollisionLayers

# Create collision system
collision_system = CollisionSystem(
    world_width=2048,
    world_height=2048,
    cell_size=128,
    max_entities=16384
)

# Register entities
player_collider = Collider(
    entity_id=1,
    diameter=32,
    offset_x=0,
    offset_y=0,
    layer=CollisionLayers.PLAYER | CollisionLayers.ENEMIES,  # Collide with enemies
    is_trigger=False,
    enabled=True
)

collision_system.register(1, player_collider, (100, 200))

# Run collision detection
collisions = collision_system.update()

# Process collisions
for collision in collisions:
    print(f"Collision between {collision.entity_a} and {collision.entity_b}")
```

### Integration with ECS

```python
# In your ECS system
class CollisionSystem:
    def __init__(self):
        self.collision_system = CollisionSystem()
        self.entity_manager = EntityManager()  # Your ECS entity manager
    
    def update(self, world):
        # Batch update entity positions from ECS world
        positions = {}
        for entity_id in self.collision_system.collision_system.get_entity_ids():
            if entity_id in world.positions:
                positions[entity_id] = (world.positions[entity_id].x, 
                                      world.positions[entity_id].y)
        
        self.collision_system.update_positions(positions)
        collisions = self.collision_system.update()
        
        # Process collisions with ECS systems
        for collision in collisions:
            if collision.is_trigger:
                self.handle_trigger_collision(collision)
            else:
                self.handle_physical_collision(collision)
```

## API Reference

### CollisionSystem Class

#### Constructor

```python
CollisionSystem(
    world_width: int = 2048,
    world_height: int = 2048,
    cell_size: int = 128,
    max_entities: int = 16384
)
```

**Parameters:**
- `world_width`, `world_height`: World dimensions in pixels
- `cell_size`: Spatial grid cell size (pixels). Tune for performance - 2-4x average collider diameter
- `max_entities`: Maximum number of entities (for pooling and memory management)

#### Core Methods

##### register(entity_id, collider, position)
Register an entity with the collision system.

**Parameters:**
- `entity_id` (int): Unique entity identifier
- `collider` (Collider): Collision data for the entity
- `position` (Tuple[int, int]): Initial (x, y) position

**Returns:** `bool` - True if registration successful

```python
collider = Collider(1, 32, 0, 0, CollisionLayers.PLAYER)
success = collision_system.register(1, collider, (100, 200))
```

##### unregister(entity_id)
Remove entity from collision system.

**Parameters:**
- `entity_id` (int): Entity to remove

**Returns:** `bool` - True if entity removed successfully

##### update_positions(positions)
Batch update entity positions for efficient processing.

**Parameters:**
- `positions` (Dict[int, Tuple[int, int]]): {entity_id: (x, y)} position updates

```python
position_updates = {
    1: (150, 200),
    2: (300, 400),
    3: (500, 600)
}
collision_system.update_positions(position_updates)
```

##### update()
Main collision detection update. Call once per frame after position updates.

**Returns:** `List[CollisionEvent]` - Collision events detected this frame

```python
collisions = collision_system.update()
for collision in collisions:
    # Handle collision
    pass
```

#### Query Methods

##### query_circle(center, radius, layer_mask=CollisionLayers.ALL)
Query all entities within a circular area.

**Parameters:**
- `center` (Tuple[int, int]): (x, y) center of query circle
- `radius` (int): Radius of query circle
- `layer_mask` (int): Bitmask of layers to include

**Returns:** `Set[int]` - Entity IDs in the query area

```python
# Find all enemies within 100 pixels of player
enemies_nearby = collision_system.query_circle(
    (player_x, player_y), 
    100, 
    CollisionLayers.ENEMIES
)
```

##### raycast(start, direction, max_distance, layer_mask=CollisionLayers.ALL)
Raycast for line-of-sight and target detection.

**Parameters:**
- `start` (Tuple[int, int]): (x, y) starting position
- `direction` (Tuple[float, float]): (dx, dy) normalized direction vector
- `max_distance` (float): Maximum distance to cast
- `layer_mask` (int): Bitmask of layers to include

**Returns:** `Optional[Tuple[int, float, Tuple[int, int]]]` - None if no hit, otherwise (entity_id, distance, hit_point)

```python
# Line-of-sight check
hit = collision_system.raycast(
    (player_x, player_y), 
    (1.0, 0.0),  # Right direction
    200,          # 200 pixel range
    CollisionLayers.WALLS
)

if hit:
    entity_id, distance, hit_point = hit
    print(f"Hit wall {entity_id} at distance {distance}")
```

#### Configuration Methods

##### add_collision_callback(callback)
Add callback for collision events.

```python
def on_collision(event):
    print(f"Collision: {event.entity_a} <-> {event.entity_b}")

collision_system.add_collision_callback(on_collision)
```

##### set_resolution_enabled(enabled)
Enable or disable collision resolution.

```python
collision_system.set_resolution_enabled(True)
```

##### set_resolution_callback(callback)
Set collision resolution callback.

```python
def resolve_collision(entity_id, force_x, force_y):
    # Apply resolution forces to entity
    entity = get_entity_by_id(entity_id)
    entity.position.x += force_x
    entity.position.y += force_y

collision_system.set_resolution_callback(resolve_collision)
```

### Collider Class

Immutable circle collider component.

```python
Collider(
    entity_id: int,
    diameter: int,
    offset_x: int,
    offset_y: int,
    layer: int,
    is_trigger: bool = False,
    enabled: bool = True
)
```

**Properties:**
- `radius` (int): Circle radius (diameter // 2)
- `world_center(entity_x, entity_y)` (Tuple[int, int]): Calculate world center position
- `check_layer_compatible(other_layer)` (bool): Check layer compatibility

### CollisionEvent

Lightweight collision event data structure.

```python
CollisionEvent(
    entity_a: int,
    entity_b: int,
    normal_x: float,
    normal_y: float,
    penetration: float,
    is_trigger: bool = False
)
```

### Collision Layers

Bitmasks for layer-based collision filtering:

```python
CollisionLayers.PLAYER = 1
CollisionLayers.ENEMIES = 2
CollisionLayers.PROJECTILES = 4
CollisionLayers.WALLS = 8
CollisionLayers.ITEMS = 16
CollisionLayers.TRIGGERS = 32
CollisionLayers.ALL = 0xFFFFFFFF
```

**Usage:**
```python
# Entity that collides with enemies and walls
collider = Collider(1, 32, 0, 0, CollisionLayers.ENEMIES | CollisionLayers.WALLS)

# Check specific layer compatibility
if collider.check_layer_compatible(CollisionLayers.PLAYER):
    # This collider can collide with players
    pass
```

## Performance Optimization

### Configuration Tuning

**Cell Size:**
- **Small entities (8-16px)**: Use cell_size = 32-64
- **Medium entities (16-32px)**: Use cell_size = 64-128
- **Large entities (32px+)**: Use cell_size = 128-256

**General Rule:** Cell size should be 2-4x the average collider diameter.

### Performance Monitoring

```python
stats = collision_system.get_performance_stats()
print(f"Entities: {stats['entities_count']}")
print(f"Collision checks: {stats['collision_checks']}")
print(f"Collisions found: {stats['collisions_found']}")
print(f"Total time: {stats['last_frame_time']*1000:.2f}ms")
print(f"Broad phase: {stats['broad_phase_time']*1000:.2f}ms")
print(f"Narrow phase: {stats['narrow_phase_time']*1000:.2f}ms")
```

### Batch Operations

Always use batch operations for better performance:

```python
# Good - batch position updates
position_updates = {entity_id: (x, y) for entity_id, (x, y) in entity_positions.items()}
collision_system.update_positions(position_updates)

# Less efficient - individual updates
for entity_id, (x, y) in entity_positions.items():
    collision_system.update_positions({entity_id: (x, y)})
```

## Integration Patterns

### ECS Integration

```python
from systems.collision import CollisionSystem, Collider
from systems.ecs_core.worlds.world import World

class CollisionECS:
    def __init__(self, world: World):
        self.world = world
        self.collision_system = CollisionSystem()
        
        # Register collision callback
        self.collision_system.add_collision_callback(self.handle_collision)
    
    def update(self):
        # Extract positions from ECS world
        positions = {}
        for entity, position in self.world.view(Position):
            entity_id = entity  # Use entity as ID
            positions[entity_id] = (position.x, position.y)
        
        # Update collision system
        self.collision_system.update_positions(positions)
        self.collision_system.update()
    
    def handle_collision(self, event):
        # Process collision with ECS systems
        if event.is_trigger:
            self.handle_trigger(event)
        else:
            self.handle_physics(event)
```

### Game State Integration

```python
class GameState:
    def __init__(self):
        self.collision_system = CollisionSystem()
        self.resolution_callbacks = []
        
        # Enable collision resolution
        self.collision_system.set_resolution_enabled(True)
        self.collision_system.set_resolution_callback(self.apply_resolution)
    
    def register_entity(self, entity_id, entity_type, position, size):
        # Create appropriate collider based on entity type
        if entity_type == "player":
            collider = Collider(entity_id, size, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
        elif entity_type == "enemy":
            collider = Collider(entity_id, size, 0, 0, CollisionLayers.ENEMIES | CollisionLayers.PLAYER)
        elif entity_type == "wall":
            collider = Collider(entity_id, size, 0, 0, CollisionLayers.WALLS)
        
        self.collision_system.register(entity_id, collider, position)
    
    def apply_resolution(self, entity_id, force_x, force_y):
        # Apply resolution to game entity
        entity = self.get_entity(entity_id)
        if entity and hasattr(entity, 'position'):
            entity.position.x += force_x
            entity.position.y += force_y
```

### Pygame Integration

```python
import pygame
from systems.collision import CollisionSystem, CollisionDebugVisualizer

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()
        
        self.collision_system = CollisionSystem()
        self.debug_visualizer = CollisionDebugVisualizer(
            self.collision_system, 
            self.screen
        )
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            # Handle debug input
            if self.debug_visualizer.handle_debug_input(event):
                continue
        
        return True
    
    def render(self):
        self.debug_visualizer.render()
        pygame.display.flip()
    
    def update(self):
        # Update collision system
        self.collision_system.update()
        
        # Render debug visualization
        self.render()
        
        return True
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.clock.tick(60)  # 60 FPS
```

## Debugging

### Debug Visualization

Enable debug visualization to see:
- Entity collision shapes
- Spatial grid lines
- Active collision pairs
- Performance metrics overlay

**Keyboard Shortcuts:**
- **G**: Toggle grid visualization
- **C**: Toggle collider shapes
- **P**: Toggle performance stats
- **H**: Toggle collision highlighting

```python
# Enable debug visualization
debug_visualizer = CollisionDebugVisualizer(collision_system, screen)

# In your game loop
debug_visualizer.render()
```

### Performance Profiling

```python
from systems.collision.debug_visualization import PerformanceProfiler

profiler = PerformanceProfiler()

# In your game loop
profiler.start_frame()
# ... game logic and collision detection ...
profiler.end_frame()

# Get performance metrics
fps = profiler.get_fps()
operation_stats = profiler.get_operation_stats("collision_update")
collision_stats = profiler.get_collision_stats()
```

## Testing

Run the comprehensive test suite:

```bash
python -m systems.collision.test_collision_system
```

The test suite includes:
- Unit tests for all components
- Integration tests for collision detection
- Performance benchmarks for 10k+ entities
- Edge case testing (zero radius, out of bounds, etc.)

## Best Practices

1. **Use Layer Filtering**: Always set appropriate collision layers to avoid unnecessary checks
2. **Batch Operations**: Use `update_positions()` for batch updates instead of individual calls
3. **Optimize Cell Size**: Tune cell size based on average entity size (2-4x diameter)
4. **Monitor Performance**: Use `get_performance_stats()` to monitor system performance
5. **Enable Debug Mode**: Use debug visualization during development to verify behavior
6. **Handle Callbacks**: Set up collision callbacks for responsive game logic
7. **Clean Up**: Unregister entities when they're removed from the game

## Troubleshooting

### Common Issues

**Poor Performance:**
- Check if cell_size is appropriate for entity sizes
- Verify layer filtering is working correctly
- Monitor collision check counts

**Missing Collisions:**
- Verify entity positions are being updated correctly
- Check if entities are outside world bounds
- Ensure collision layers are compatible

**Incorrect Collision Responses:**
- Verify collision resolution callback is working
- Check if entities have sufficient mass/size differences
- Ensure trigger entities are properly configured

## Examples

See the comprehensive examples in the test suite and documentation for detailed usage patterns.

This collision system provides a solid foundation for 2D game physics while maintaining the flexibility to integrate with any game architecture.