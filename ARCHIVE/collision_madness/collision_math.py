# systems/collision/collision_math.py
"""
High-performance circle collision mathematics.
Optimized for 2D circle-circle collision detection with minimal overhead.
"""

import math
from typing import Optional, Tuple


def circle_collide(center_a: Tuple[int, int], radius_a: int, 
                  center_b: Tuple[int, int], radius_b: int) -> bool:
    """Fast circle collision detection using squared distance
    
    Args:
        center_a: (x, y) center position of circle A
        radius_a: Radius of circle A
        center_b: (x, y) center position of circle B  
        radius_b: Radius of circle B
        
    Returns:
        True if circles overlap, False otherwise
    """
    dx = center_a[0] - center_b[0]
    dy = center_a[1] - center_b[1]
    
    # Use squared distance to avoid expensive sqrt
    combined_radius = radius_a + radius_b
    return dx*dx + dy*dy < combined_radius * combined_radius


def circle_collision_info(center_a: Tuple[int, int], radius_a: int,
                         center_b: Tuple[int, int], radius_b: int) -> Optional[Tuple[float, float, float]]:
    """Get detailed collision information for circle-circle collision
    
    Args:
        center_a: (x, y) center position of circle A
        radius_a: Radius of circle A
        center_b: (x, y) center position of circle B
        radius_b: Radius of circle B
        
    Returns:
        None if no collision, otherwise (normal_x, normal_y, penetration)
    """
    dx = center_b[0] - center_a[0]
    dy = center_b[1] - center_a[1]
    dist_sq = dx*dx + dy*dy
    
    combined_radius = radius_a + radius_b
    combined_radius_sq = combined_radius * combined_radius
    
    if dist_sq >= combined_radius_sq:
        return None  # No collision
    
    # Handle the case where centers are exactly the same
    if dist_sq == 0:
        return (0.0, 1.0, float(combined_radius))  # Arbitrary normal
    
    # Calculate actual distance and normal
    dist = math.sqrt(dist_sq)
    normal_x = dx / dist
    normal_y = dy / dist
    penetration = float(combined_radius - dist)
    
    return (normal_x, normal_y, penetration)


def resolve_circle_overlap(center_a: Tuple[float, float], radius_a: int,
                          center_b: Tuple[float, float], radius_b: int) -> Tuple[float, float, float, float]:
    """Resolve circle overlap by pushing circles apart equally
    
    Args:
        center_a: (x, y) center position of circle A
        radius_a: Radius of circle A
        center_b: (x, y) center position of circle B
        radius_b: Radius of circle B
        
    Returns:
        (delta_a_x, delta_a_y, delta_b_x, delta_b_y) - adjustments to move circles apart
    """
    dx = center_b[0] - center_a[0]
    dy = center_b[1] - center_a[1]
    dist_sq = dx*dx + dy*dy
    
    if dist_sq == 0:
        # Centers are identical - push apart in random direction
        return (0.0, radius_a, 0.0, -radius_b)
    
    combined_radius = radius_a + radius_b
    dist = math.sqrt(dist_sq)
    
    if dist >= combined_radius:
        return (0.0, 0.0, 0.0, 0.0)  # No overlap
    
    # Calculate overlap and split it equally
    overlap = combined_radius - dist
    push_x = (dx / dist) * (overlap * 0.5)
    push_y = (dy / dist) * (overlap * 0.5)
    
    # Circle A moves opposite to the normal, Circle B moves along it
    return (-push_x, -push_y, push_x, push_y)


def point_in_circle(point: Tuple[int, int], center: Tuple[int, int], radius: int) -> bool:
    """Check if a point is inside a circle
    
    Args:
        point: (x, y) point to test
        center: (x, y) circle center
        radius: Circle radius
        
    Returns:
        True if point is inside or on the circle boundary
    """
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return dx*dx + dy*dy <= radius * radius


def circle_line_intersection(center: Tuple[int, int], radius: int,
                           line_start: Tuple[int, int], line_end: Tuple[int, int]) -> bool:
    """Check if a line segment intersects a circle
    
    Args:
        center: (x, y) circle center
        radius: Circle radius
        line_start: (x, y) start of line segment
        line_end: (x, y) end of line segment
        
    Returns:
        True if line segment intersects circle
    """
    # Vector from line start to end
    line_dx = line_end[0] - line_start[0]
    line_dy = line_end[1] - line_start[1]
    
    # Vector from line start to circle center
    center_dx = center[0] - line_start[0]
    center_dy = center[1] - line_start[1]
    
    # Project center onto line and clamp to segment
    line_length_sq = line_dx*line_dx + line_dy*line_dy
    if line_length_sq == 0:
        # Line is a point
        return point_in_circle(center, line_start, radius)
    
    t = (center_dx * line_dx + center_dy * line_dy) / line_length_sq
    t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
    
    # Find closest point on line to circle center
    closest_x = line_start[0] + t * line_dx
    closest_y = line_start[1] + t * line_dy
    
    return point_in_circle(center, (int(closest_x), int(closest_y)), radius)


def raycast_circle(start: Tuple[int, int], direction: Tuple[float, float], 
                  max_distance: float, center: Tuple[int, int], radius: int) -> Optional[float]:
    """Raycast from start point in direction to find intersection with circle
    
    Args:
        start: (x, y) ray start position
        direction: (dx, dy) normalized direction vector
        max_distance: Maximum distance to check
        center: (x, y) circle center
        radius: Circle radius
        
    Returns:
        None if no hit, otherwise distance to intersection point
    """
    # Vector from ray start to circle center
    start_dx = center[0] - start[0]
    start_dy = center[1] - start[1]
    
    # Project circle center onto ray direction
    projection = start_dx * direction[0] + start_dy * direction[1]
    
    if projection < 0 or projection > max_distance:
        return None  # Circle is behind start or too far away
    
    # Find closest approach point
    closest_x = start[0] + projection * direction[0]
    closest_y = start[1] + projection * direction[1]
    
    # Check if closest point is within circle radius
    dx = closest_x - center[0]
    dy = closest_y - center[1]
    
    if dx*dx + dy*dy <= radius * radius:
        return projection
    
    return None


class SpatialGrid:
    """Uniform grid spatial partitioning for efficient collision detection"""
    
    def __init__(self, world_width: int, world_height: int, cell_size: int = 128):
        self.world_width = world_width
        self.world_height = world_height
        self.cell_size = cell_size
        
        # Grid dimensions
        self.grid_width = (world_width + cell_size - 1) // cell_size
        self.grid_height = (world_height + cell_size - 1) // cell_size
        
        # Spatial hash: (grid_x, grid_y) -> set of entity_ids
        self.cells = {}
        
    def _get_cell_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Convert world coordinates to grid coordinates"""
        grid_x = x // self.cell_size
        grid_y = y // self.cell_size
        return (grid_x, grid_y)
    
    def _get_cell_key(self, grid_x: int, grid_y: int) -> int:
        """Generate unique key for grid cell"""
        return grid_y * self.grid_width + grid_x
    
    def add_entity(self, entity_id: int, center_x: int, center_y: int, radius: int):
        """Add entity to appropriate grid cells
        
        Args:
            entity_id: Unique entity identifier
            center_x: Entity center X position
            center_y: Entity center Y position
            radius: Entity collision radius
        """
        # Calculate which cells the entity spans
        min_x = center_x - radius
        max_x = center_x + radius
        min_y = center_y - radius
        max_y = center_y + radius
        
        # Convert to grid coordinates
        min_grid_x, min_grid_y = self._get_cell_coords(min_x, min_y)
        max_grid_x, max_grid_y = self._get_cell_coords(max_x, max_y)
        
        # Add entity to all cells it spans
        for grid_x in range(min_grid_x, max_grid_x + 1):
            if 0 <= grid_x < self.grid_width:
                for grid_y in range(min_grid_y, max_grid_y + 1):
                    if 0 <= grid_y < self.grid_height:
                        key = self._get_cell_key(grid_x, grid_y)
                        if key not in self.cells:
                            self.cells[key] = set()
                        self.cells[key].add(entity_id)
    
    def remove_entity(self, entity_id: int, center_x: int, center_y: int, radius: int):
        """Remove entity from all grid cells
        
        Args:
            entity_id: Entity to remove
            center_x: Entity center X position
            center_y: Entity center Y position  
            radius: Entity collision radius
        """
        # Calculate which cells the entity spans
        min_x = center_x - radius
        max_x = center_x + radius
        min_y = center_y - radius
        max_y = center_y + radius
        
        min_grid_x, min_grid_y = self._get_cell_coords(min_x, min_y)
        max_grid_x, max_grid_y = self._get_cell_coords(max_x, max_y)
        
        # Remove entity from all cells
        for grid_x in range(min_grid_x, max_grid_x + 1):
            if 0 <= grid_x < self.grid_width:
                for grid_y in range(min_grid_y, max_grid_y + 1):
                    if 0 <= grid_y < self.grid_height:
                        key = self._get_cell_key(grid_x, grid_y)
                        if key in self.cells:
                            self.cells[key].discard(entity_id)
                            # Clean up empty cells to save memory
                            if not self.cells[key]:
                                del self.cells[key]
    
    def query_circle(self, center: Tuple[int, int], radius: int, 
                    entity_positions: dict) -> set[int]:
        """Query all entities in circle area
        
        Args:
            center: (x, y) query center
            radius: Query radius
            entity_positions: {entity_id: (x, y)} positions map
            
        Returns:
            Set of entity_ids potentially overlapping the query circle
        """
        # Calculate query bounds
        min_x = center[0] - radius
        max_x = center[0] + radius
        min_y = center[1] - radius
        max_y = center[1] + radius
        
        # Convert to grid coordinates
        min_grid_x, min_grid_y = self._get_cell_coords(min_x, min_y)
        max_grid_x, max_grid_y = self._get_cell_coords(max_x, max_y)
        
        # Collect entities from overlapping cells
        candidates = set()
        for grid_x in range(min_grid_x, max_grid_x + 1):
            if 0 <= grid_x < self.grid_width:
                for grid_y in range(min_grid_y, max_grid_y + 1):
                    if 0 <= grid_y < self.grid_height:
                        key = self._get_cell_key(grid_x, grid_y)
                        if key in self.cells:
                            candidates.update(self.cells[key])
        
        return candidates
    
    def clear(self):
        """Clear all entities from grid"""
        self.cells.clear()