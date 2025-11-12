# Entity Classes Design Guide

## Overview

The Entity Classes system provides type-safe entity classification for your ECS (Entity Component System) architecture. This guide covers the design patterns, integration points, and best practices for using entity classes effectively.

## Core Architecture

### Entity Class Components

Entity classes are implemented as **marker components** - frozen dataclasses with no data fields. This design choice provides several benefits:

- **Type Safety**: Each entity class is a distinct Python type
- **Performance**: Zero memory overhead beyond the component reference
- **ECS Compatibility**: Works seamlessly with existing World class queries
- **Immutability**: Frozen dataclasses prevent accidental modification
- **Extensibility**: Easy to add new entity classes without breaking changes

### Available Entity Classes

```python
Player    # Player-controlled entities
Mob       # Mobile NPCs, enemies, creatures  
NPC       # Static non-player characters
Plant     # Plants, vegetation, crops
Object    # Static environmental objects
```

## Integration Patterns

### 1. World Class Integration

Entity classes integrate directly with your existing World class:

```python
# Basic class queries
world.entities_with(Player)           # List of all player entities
world.entities_with(Mob, Position)    # Mobs with positions

# Complex queries with multiple components
for entity, player, pos, health in world.view(Player, Position, Health):
    # Process player entities with position and health data
```

### 2. Entity Creation Pattern

Standard pattern for creating entities with class markers:

```python
def create_player(world, entity_manager, x, y):
    entity = entity_manager.create()
    world.add(entity, Player())
    world.add(entity, Position(x, y))
    world.add(entity, Health(100, 100))
    return entity
```

### 3. System Design Patterns

#### Single-Purpose Systems
Design systems to operate on specific entity classes:

```python
def player_input_system(world, input_handler):
    """Only processes Player entities"""
    for entity, player_comp, pos_comp in world.view(Player, Position):
        handle_player_input(entity, pos_comp, input_handler)
```

#### Multi-Class Systems
Systems can handle multiple entity classes when they share behaviors:

```python
def health_system(world):
    """Processes all living entities"""
    for entity, health_comp in world.view(Health):
        if health_comp.cur <= 0:
            remove_dead_entity(entity, world)
```

## Best Practices

### 1. Consistent Naming Conventions

- Use PascalCase for entity class names (Player, Mob, NPC)
- Include descriptive docstrings explaining the class purpose
- Keep class names semantic and game-specific

### 2. Query Optimization

- **Order matters**: Always put the most selective component first in `view()` calls
- **Cache results**: Store frequently queried entity lists at system initialization
- **Batch operations**: Process entities in batches when possible

```python
# Good: Most selective component first
for entity, pos in world.view(Position, Player, Health):

# Avoid: Less selective component first  
for entity, player in world.view(Player, Position):
```

### 3. System Architecture

- **Single Responsibility**: Each system should focus on one aspect of entity behavior
- **Component Dependency**: Systems should only access components they need
- **Clear Interfaces**: Define clear input/output for each system

### 4. Performance Considerations

- **Marker components are free**: No performance penalty beyond the component reference
- **World queries are optimized**: Uses the smallest component storage for efficiency
- **Avoid per-frame entity creation**: Create entities during level loading or setup phases

## Future Extensibility

### Adding New Entity Classes

To add a new entity class:

1. Create the marker component in `components/entity_classes.py`
2. Add appropriate documentation
3. Update this documentation with examples
4. No other changes needed - the new class works immediately with existing systems

### Entity Hierarchies

Future enhancement potential for class hierarchies:

```python
# Future: Class inheritance for specialized entities
@dataclass(frozen=True)
class AggressiveMob(Mob):
    """Specialized mob that attacks players"""
    aggression_radius: float = 50.0
```

### Registry System Integration

The designed registry architecture can be implemented later for performance optimization while maintaining compatibility:

```python
# Future registry integration
from components.entity_registry import EntityRegistry

registry = EntityRegistry(world)
all_players = registry.get_entities_by_class(Player)  # O(1) lookup
```

## Migration Guide

### From Existing Systems

If you have existing entity classification systems, here's how to migrate:

1. **Identify current classifications**: Map existing entity types to new classes
2. **Update entity creation**: Add appropriate class markers when creating entities
3. **Refactor systems**: Update systems to use entity classes instead of custom flags
4. **Test thoroughly**: Ensure all systems still function correctly

### Backward Compatibility

The entity class system is designed to be additive:
- Existing systems continue to work unchanged
- New systems can optionally use entity classes
- Gradual migration is supported

## Testing Patterns

### Unit Testing Systems

Test systems in isolation using mock entities:

```python
def test_player_movement():
    world = World()
    entity = EntityManager().create()
    
    # Setup
    world.add(entity, Player())
    world.add(entity, Position(0, 0))
    world.add(entity, Velocity(0, 0))
    
    # Execute
    player_movement_system(world, mock_input)
    
    # Verify
    pos = world.get(entity, Position)
    assert pos.x > 0  # Player should have moved
```

### Integration Testing

Test entity class queries across multiple systems:

```python
def test_player_mob_interaction():
    # Create player and mob entities
    player = create_player(world, manager, 100, 100)
    mob = create_mob(world, manager, 200, 200)
    
    # Run systems
    player_movement_system(world, player_input)
    mob_ai_system(world, ai_manager)
    
    # Verify correct behavior
    assert are_entities_interacting(player, mob, world)
```

## Debugging Tips

### Entity Inspection

Use the World class to inspect entity composition:

```python
def debug_entity(entity, world):
    """Print all components for debugging"""
    print(f"Entity {entity} components:")
    for comp_type, store in world._storage.items():
        if entity in store:
            print(f"  {comp_type.__name__}: {store[entity]}")
```

### Query Validation

Validate that your queries are working as expected:

```python
# Check if entities have expected components
players = world.entities_with(Player)
for player in players:
    assert world.get(player, Position), f"Player {player} missing Position"
    assert world.get(player, Health), f"Player {player} missing Health"
```

## Conclusion

The Entity Classes system provides a solid foundation for type-safe entity classification in your ECS architecture. By following these patterns and best practices, you can build robust, performant game systems that are easy to maintain and extend.

Key benefits:
- **Type Safety**: Compile-time entity type checking
- **Performance**: Optimized queries through existing ECS infrastructure  
- **Maintainability**: Clear separation of entity types
- **Extensibility**: Easy to add new classes and behaviors
- **Compatibility**: Works with existing ECS patterns and systems

This design positions your codebase for future growth while providing immediate benefits for entity organization and system design.