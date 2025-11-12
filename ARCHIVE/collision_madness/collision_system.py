# systems/collision/collision_system.py
"""
High-performance 2D collision system with uniform grid spatial partitioning.
Optimized for 10k+ entities with dual performance modes (sparse/dense scenarios).
"""

import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Callable

from .collider import Collider, CollisionEvent, CollisionLayers
from .collision_math import (
    circle_collide, circle_collision_info, resolve_circle_overlap,
    SpatialGrid, raycast_circle, point_in_circle
)


class CollisionSystem:
    """High-performance 2D circle collision detection system
    
    Features:
    - Uniform grid spatial partitioning for O(n) broad-phase
    - Layer-based collision filtering for performance
    - Support for 10k+ entities at 60FPS
    - Modular design with no rendering/ECS dependencies
    - Optional collision resolution and debug visualization
    """
    
    def __init__(self, world_width: int = 2048, world_height: int = 2048, 
                 cell_size: int = 128, max_entities: int = 16384):
        """Initialize collision system
        
        Args:
            world_width: World width in pixels
            world_height: World height in pixels
            cell_size: Spatial grid cell size (pixels) - tune for performance
            max_entities: Maximum number of entities (for pooling)
        """
        self.world_width = world_width
        self.world_height = world_height
        self.cell_size = cell_size
        self.max_entities = max_entities
        
        # Core data structures
        self.colliders: Dict[int, Collider] = {}  # entity_id -> Collider
        self.entity_positions: Dict[int, Tuple[int, int]] = {}  # entity_id -> (x, y)
        self.entity_layers: Dict[int, int] = {}  # entity_id -> layer_bitmask
        
        # Spatial grid for broad-phase
        self.grid = SpatialGrid(world_width, world_height, cell_size)
        
        # Collision events cache
        self.active_collisions: Set[Tuple[int, int]] = set()  # (entity_a, entity_b) pairs
        self.collision_callbacks: List[Callable[[CollisionEvent], None]] = []
        
        # Performance tracking
        self.performance_stats = {
            'entities_count': 0,
            'collision_checks': 0,
            'collisions_found': 0,
            'last_frame_time': 0.0,
            'grid_rebuild_time': 0.0,
            'broad_phase_time': 0.0,
            'narrow_phase_time': 0.0
        }
        
        # LOD and optimization settings
        self.lod_enabled = True
        self.lod_distance = 512  # Distance threshold for LOD
        self.lod_callback: Optional[Callable[[int, bool], None]] = None
        
        # Collision resolution settings
        self.resolution_enabled = False
        self.resolution_callback: Optional[Callable[[int, int, float, float], None]] = None
        
    def register(self, entity_id: int, collider: Collider, position: Tuple[int, int]) -> bool:
        """Register entity with collision system
        
        Args:
            entity_id: Unique entity identifier
            collider: Collision data for entity
            position: Initial (x, y) position
            
        Returns:
            True if registration successful, False if entity_id already exists
        """
        if entity_id in self.colliders:
            return False  # Entity already registered
            
        if entity_id >= self.max_entities:
            raise ValueError(f"Entity ID {entity_id} exceeds maximum {self.max_entities}")
            
        self.colliders[entity_id] = collider
        self.entity_positions[entity_id] = position
        self.entity_layers[entity_id] = collider.layer
        
        # Add to spatial grid
        center_x, center_y = collider.world_center(position[0], position[1])
        self.grid.add_entity(entity_id, center_x, center_y, collider.radius)
        
        self.performance_stats['entities_count'] = len(self.colliders)
        return True
    
    def unregister(self, entity_id: int) -> bool:
        """Remove entity from collision system
        
        Args:
            entity_id: Entity to remove
            
        Returns:
            True if entity removed, False if not found
        """
        if entity_id not in self.colliders:
            return False
            
        collider = self.colliders[entity_id]
        position = self.entity_positions[entity_id]
        
        # Remove from spatial grid
        center_x, center_y = collider.world_center(position[0], position[1])
        self.grid.remove_entity(entity_id, center_x, center_y, collider.radius)
        
        # Remove from internal data structures
        del self.colliders[entity_id]
        del self.entity_positions[entity_id]
        del self.entity_layers[entity_id]
        
        # Remove from active collisions
        collisions_to_remove = set()
        for pair in self.active_collisions:
            if entity_id in pair:
                collisions_to_remove.add(pair)
        
        self.active_collisions -= collisions_to_remove
        
        self.performance_stats['entities_count'] = len(self.colliders)
        return True
    
    def update_positions(self, positions: Dict[int, Tuple[int, int]]) -> None:
        """Batch update entity positions for efficient processing
        
        Args:
            positions: {entity_id: (x, y)} dictionary of position updates
        """
        start_time = time.perf_counter()
        
        # Update positions
        for entity_id, new_pos in positions.items():
            if entity_id in self.colliders:
                old_pos = self.entity_positions[entity_id]
                if old_pos != new_pos:
                    self.entity_positions[entity_id] = new_pos
                    
                    # Update spatial grid
                    collider = self.colliders[entity_id]
                    old_center_x, old_center_y = collider.world_center(old_pos[0], old_pos[1])
                    new_center_x, new_center_y = collider.world_center(new_pos[0], new_pos[1])
                    
                    if (old_center_x // self.cell_size != new_center_x // self.cell_size or
                        old_center_y // self.cell_size != new_center_y // self.cell_size):
                        
                        # Entity moved to different grid cells - update spatial grid
                        self.grid.remove_entity(entity_id, old_center_x, old_center_y, collider.radius)
                        self.grid.add_entity(entity_id, new_center_x, new_center_y, collider.radius)
        
        self.performance_stats['grid_rebuild_time'] = time.perf_counter() - start_time
    
    def update(self) -> List[CollisionEvent]:
        """Main collision detection update
        
        Process all registered entities for collisions and return collision events.
        Should be called once per frame after all entity positions are updated.
        
        Returns:
            List of collision events detected this frame
        """
        frame_start = time.perf_counter()
        collision_events: List[CollisionEvent] = []
        
        # Early exit if no entities
        if not self.colliders:
            self.performance_stats['last_frame_time'] = time.perf_counter() - frame_start
            return collision_events
        
        broad_phase_start = time.perf_counter()
        
        # Broad-phase: Find potential collision pairs using spatial grid
        potential_pairs = self._find_potential_collisions()
        
        self.performance_stats['broad_phase_time'] = time.perf_counter() - broad_phase_start
        narrow_phase_start = time.perf_counter()
        
        # Narrow-phase: Detailed circle collision detection
        current_collisions = set()
        collision_check_count = 0
        
        for entity_a, entity_b in potential_pairs:
            collision_check_count += 1
            
            # Get collision data
            collider_a = self.colliders[entity_a]
            collider_b = self.colliders[entity_b]
            
            # Layer filtering - skip incompatible layers
            if not collider_a.check_layer_compatible(collider_b.layer):
                continue
                
            if not collider_b.check_layer_compatible(collider_a.layer):
                continue
                
            # Skip disabled entities
            if not collider_a.enabled or not collider_b.enabled:
                continue
            
            # Calculate world centers
            pos_a = self.entity_positions[entity_a]
            pos_b = self.entity_positions[entity_b]
            
            center_a = collider_a.world_center(pos_a[0], pos_a[1])
            center_b = collider_b.world_center(pos_b[0], pos_b[1])
            
            # Narrow-phase: Circle collision detection
            if circle_collide(center_a, collider_a.radius, center_b, collider_b.radius):
                collision_info = circle_collision_info(center_a, collider_a.radius, 
                                                     center_b, collider_b.radius)
                
                if collision_info:
                    normal_x, normal_y, penetration = collision_info
                    
                    # Create collision event
                    is_trigger = collider_a.is_trigger or collider_b.is_trigger
                    event = CollisionEvent(
                        entity_a=entity_a,
                        entity_b=entity_b,
                        normal_x=normal_x,
                        normal_y=normal_y,
                        penetration=penetration,
                        is_trigger=is_trigger
                    )
                    
                    collision_events.append(event)
                    current_collisions.add((entity_a, entity_b) if entity_a < entity_b else (entity_b, entity_a))
                    
                    # Call collision callbacks
                    for callback in self.collision_callbacks:
                        callback(event)
        
        self.performance_stats['narrow_phase_time'] = time.perf_counter() - narrow_phase_start
        self.performance_stats['collision_checks'] = collision_check_count
        self.performance_stats['collisions_found'] = len(collision_events)
        self.performance_stats['last_frame_time'] = time.perf_counter() - frame_start
        
        # Update active collisions tracking
        self.active_collisions = current_collisions
        
        # Apply collision resolution if enabled
        if self.resolution_enabled:
            self._apply_collision_resolution(collision_events)
        
        return collision_events
    
    def query_circle(self, center: Tuple[int, int], radius: int, 
                    layer_mask: int = CollisionLayers.ALL) -> Set[int]:
        """Query all entities within a circular area
        
        Args:
            center: (x, y) center of query circle
            radius: Radius of query circle
            layer_mask: Bitmask of layers to include (default: all layers)
            
        Returns:
            Set of entity IDs in the query area
        """
        if not self.colliders:
            return set()
            
        # Use spatial grid for initial filtering
        candidates = self.grid.query_circle(center, radius, self.entity_positions)
        
        # Filter by layer compatibility and do precise circle check
        results = set()
        for entity_id in candidates:
            if entity_id in self.colliders:
                collider = self.colliders[entity_id]
                if not collider.enabled:
                    continue
                    
                # Check layer compatibility
                if not (collider.layer & layer_mask):
                    continue
                
                # Precise circle check
                pos = self.entity_positions[entity_id]
                collider_center = collider.world_center(pos[0], pos[1])
                
                if circle_collide(center, radius, collider_center, collider.radius):
                    results.add(entity_id)
        
        return results
    
    def raycast(self, start: Tuple[int, int], direction: Tuple[float, float], 
               max_distance: float, layer_mask: int = CollisionLayers.ALL) -> Optional[Tuple[int, float, Tuple[int, int]]]:
        """Raycast for line-of-sight and target detection
        
        Args:
            start: (x, y) starting position
            direction: (dx, dy) normalized direction vector
            max_distance: Maximum distance to cast
            layer_mask: Bitmask of layers to include
            
        Returns:
            None if no hit, otherwise (entity_id, distance, hit_point)
        """
        if not self.colliders:
            return None
            
        # Normalize direction
        length = math.sqrt(direction[0]*direction[0] + direction[1]*direction[1])
        if length == 0:
            return None
            
        dir_x = direction[0] / length
        dir_y = direction[1] / length
        
        # Query entities near the ray path
        query_end = (int(start[0] + dir_x * max_distance), 
                    int(start[1] + dir_y * max_distance))
        query_radius = max_distance  # Conservative radius
        
        candidates = self.grid.query_circle(start, query_radius, self.entity_positions)
        
        # Find closest intersection
        closest_hit = None
        closest_distance = max_distance
        
        for entity_id in candidates:
            if entity_id not in self.colliders:
                continue
                
            collider = self.colliders[entity_id]
            if not collider.enabled:
                continue
                
            # Check layer compatibility
            if not (collider.layer & layer_mask):
                continue
            
            # Raycast against this entity's circle
            pos = self.entity_positions[entity_id]
            center = collider.world_center(pos[0], pos[1])
            
            hit_distance = raycast_circle(start, (dir_x, dir_y), max_distance, center, collider.radius)
            
            if hit_distance is not None and hit_distance < closest_distance:
                closest_distance = hit_distance
                hit_point = (int(start[0] + dir_x * hit_distance), 
                           int(start[1] + dir_y * hit_distance))
                closest_hit = (entity_id, hit_distance, hit_point)
        
        return closest_hit
    
    def _find_potential_collisions(self) -> Set[Tuple[int, int]]:
        """Find potential collision pairs using spatial grid
        
        Returns:
            Set of (entity_a, entity_b) pairs that might collide
        """
        potential_pairs = set()
        
        # For each cell, check all entity pairs within that cell
        for cell_entities in self.grid.cells.values():
            if len(cell_entities) < 2:
                continue
                
            entities_list = list(cell_entities)
            for i in range(len(entities_list)):
                for j in range(i + 1, len(entities_list)):
                    entity_a = entities_list[i]
                    entity_b = entities_list[j]
                    
                    # Ensure consistent ordering
                    if entity_a > entity_b:
                        entity_a, entity_b = entity_b, entity_a
                    
                    potential_pairs.add((entity_a, entity_b))
        
        # Also check adjacent cells to catch entities spanning cell boundaries
        for cell_key, entities in self.grid.cells.items():
            if not entities:
                continue
                
            grid_x = cell_key % self.grid.grid_width
            grid_y = cell_key // self.grid.grid_width
            
            # Check 8 neighboring cells
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                        
                    neighbor_x = grid_x + dx
                    neighbor_y = grid_y + dy
                    
                    if (0 <= neighbor_x < self.grid.grid_width and 
                        0 <= neighbor_y < self.grid.grid_height):
                        
                        neighbor_key = neighbor_y * self.grid.grid_width + neighbor_x
                        if neighbor_key in self.grid.cells:
                            for entity_a in entities:
                                for entity_b in self.grid.cells[neighbor_key]:
                                    if entity_a != entity_b:
                                        pair = (min(entity_a, entity_b), max(entity_a, entity_b))
                                        potential_pairs.add(pair)
        
        return potential_pairs
    
    def _apply_collision_resolution(self, collisions: List[CollisionEvent]) -> None:
        """Apply collision resolution using push-apart algorithm
        
        Args:
            collisions: List of collision events from this frame
        """
        if not self.resolution_callback or not collisions:
            return
            
        # Collect resolution forces per entity
        forces: Dict[int, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
        
        for collision in collisions:
            if collision.is_trigger:
                continue  # Skip triggers for resolution
                
            entity_a = collision.entity_a
            entity_b = collision.entity_b
            normal_x, normal_y = collision.normal_x, collision.normal_y
            penetration = collision.penetration
            
            # Apply half penetration to each entity in opposite directions
            force_a_x = -normal_x * (penetration * 0.5)
            force_a_y = -normal_y * (penetration * 0.5)
            force_b_x = normal_x * (penetration * 0.5)
            force_b_y = normal_y * (penetration * 0.5)
            
            # Accumulate forces
            current_a_x, current_a_y = forces[entity_a]
            current_b_x, current_b_y = forces[entity_b]
            
            forces[entity_a] = (current_a_x + force_a_x, current_a_y + force_a_y)
            forces[entity_b] = (current_b_x + force_b_x, current_b_y + force_b_y)
        
        # Apply resolution callback
        for entity_id, (force_x, force_y) in forces.items():
            if abs(force_x) > 0.001 or abs(force_y) > 0.001:
                self.resolution_callback(entity_id, force_x, force_y)
    
    def add_collision_callback(self, callback: Callable[[CollisionEvent], None]) -> None:
        """Add callback for collision events
        
        Args:
            callback: Function to call for each collision event
        """
        self.collision_callbacks.append(callback)
    
    def remove_collision_callback(self, callback: Callable[[CollisionEvent], None]) -> None:
        """Remove collision event callback
        
        Args:
            callback: Callback to remove
        """
        if callback in self.collision_callbacks:
            self.collision_callbacks.remove(callback)
    
    def set_resolution_enabled(self, enabled: bool) -> None:
        """Enable or disable collision resolution
        
        Args:
            enabled: Whether to enable collision resolution
        """
        self.resolution_enabled = enabled
    
    def set_resolution_callback(self, callback: Optional[Callable[[int, float, float], None]]) -> None:
        """Set collision resolution callback
        
        Args:
            callback: Function to apply resolution forces (entity_id, force_x, force_y)
        """
        self.resolution_callback = callback
    
    def set_lod_callback(self, callback: Callable[[int, bool], None]) -> None:
        """Set LOD callback for entity management
        
        Args:
            callback: Function called when entity LOD state changes (entity_id, enabled)
        """
        self.lod_callback = callback
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics from last frame
        
        Returns:
            Dictionary of performance metrics
        """
        return self.performance_stats.copy()
    
    def clear(self) -> None:
        """Clear all entities and reset system"""
        self.colliders.clear()
        self.entity_positions.clear()
        self.entity_layers.clear()
        self.active_collisions.clear()
        self.grid.clear()
        self.performance_stats['entities_count'] = 0
        
    def get_entity_count(self) -> int:
        """Get current number of registered entities
        
        Returns:
            Number of entities in collision system
        """
        return len(self.colliders)