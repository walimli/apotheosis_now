# Entity Classes Usage Examples

This document shows how to use the entity class marker components in your ECS system.

# Create game world
world = World()
entity_manager = EntityManager()
```

## Creating Entities with Class Markers

```python
# Create a player entity
player_entity = entity_manager.create()
world.add(player_entity, Player())
world.add(player_entity, Position(x=100, y=200))
world.add(player_entity, Health(cur=100, max=100))

# Create a mob entity  
mob_entity = entity_manager.create()
world.add(mob_entity, Mob())
world.add(mob_entity, Position(x=300, y=150))
world.add(mob_entity, Health(cur=50, max=50))
world.add(mob_entity, Velocity(vx=10, vy=0))

# Create an NPC entity
npc_entity = entity_manager.create()
world.add(npc_entity, NPC())
world.add(npc_entity, Position(x=500, y=300))

# Create a plant entity
plant_entity = entity_manager.create()
world.add(plant_entity, Plant())
world.add(plant_entity, Position(x=200, y=400))

# Create an environmental object
rock_entity = entity_manager.create()
world.add(rock_entity, Object())
world.add(rock_entity, Position(x=600, y=100))
```

## Querying Entities by Class

### Find All Players
```python
all_players = world.entities_with(Player())
print(f"Found {len(all_players)} players")
```

### Find All Living Entities
```python
living_entities = world.entities_with(Player, Health)
for entity, player_comp, health_comp in world.view(Player, Health):
    print(f"Player entity {entity} has {health_comp.cur} health")
```

### Find Mobile Entities
```python
mobile_entities = world.entities_with(Mob, Velocity)
for entity, mob_comp, velocity_comp in world.view(Mob, Velocity):
    print(f"Mob {entity} moving at ({velocity_comp.vx}, {velocity_comp.vy})")
```

### Find All Entities at Specific Position
```python
entities_at_pos = world.entities_with(Position)
for entity, pos_comp in world.view(Position):
    if pos_comp.x == 100 and pos_comp.y == 200:
        print(f"Found entity {entity} at position (100, 200)")
```

## Systems That Use Entity Classes

### Player Movement System
```python
def player_movement_system(world, input_handler):
    """System that handles player movement only"""
    for entity, player_comp, pos_comp, velocity_comp in world.view(Player, Position, Velocity):
        # Only process player entities
        move_input = input_handler.get_movement(entity)
        velocity_comp.vx = move_input.x * 5.0
        velocity_comp.vy = move_input.y * 5.0
        # Update position based on velocity
        pos_comp.x += velocity_comp.vx
        pos_comp.y += velocity_comp.vy
```

### AI System for Mobs
```python
def mob_ai_system(world, ai_manager):
    """System that handles AI for mob entities only"""
    for entity, mob_comp, pos_comp, velocity_comp in world.view(Mob, Position, Velocity):
        # Only process mob entities
        ai_target = ai_manager.get_target_for_mob(entity, pos_comp)
        if ai_target:
            # Simple chase AI
            dx = ai_target.x - pos_comp.x
            dy = ai_target.y - pos_comp.y
            distance = (dx*dx + dy*dy)**0.5
            
            if distance > 0:
                velocity_comp.vx = (dx / distance) * 2.0
                velocity_comp.vy = (dy / distance) * 2.0
```

### Harvesting System for Plants
```python
def plant_harvest_system(world, interaction_manager):
    """System that handles plant harvesting"""
    for entity, plant_comp, pos_comp in world.view(Plant, Position):
        # Only process plant entities
        if interaction_manager.is_entity_nearby(entity, "player", 50):
            # Plant can be harvested
            harvested_items = interaction_manager.harvest_plant(entity)
            if harvested_items:
                print(f"Harvested {harvested_items} from plant {entity}")
```

## Benefits of Entity Class Markers

1. **Type Safety**: Easy to identify entity types
2. **Performance**: Optimized queries for specific entity types
3. **Flexibility**: Systems can target specific entity classes
4. **Extensibility**: Easy to add new entity classes
5. **Compatibility**: Works with existing ECS patterns

## Integration with Existing Code

These entity class markers work seamlessly with your existing:
- `World` class (uses `entities_with()` and `view()`)
- `EntityManager` for creating entities
- Existing components like `Position`, `Health`, `Velocity`
- Systems that already use component queries

The markers are pure ECS components, so they follow all the same patterns as your existing components.