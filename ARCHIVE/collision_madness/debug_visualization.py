# systems/collision/debug_visualization.py
"""
Debug visualization system for collision detection.
Provides visual debugging tools for collision shapes, spatial grid, and performance metrics.
"""

import pygame
from typing import Dict, List, Optional, Set, Tuple

from .collider import Collider, CollisionEvent
from .collision_system import CollisionSystem


class CollisionDebugVisualizer:
    """Debug visualization system for collision detection
    
    Provides visual debugging tools including:
    - Entity collision shapes
    - Spatial grid visualization
    - Performance metrics overlay
    - Collision event visualization
    - Real-time collision highlighting
    """
    
    def __init__(self, collision_system: CollisionSystem, screen: pygame.Surface):
        """Initialize debug visualizer
        
        Args:
            collision_system: The collision system to visualize
            screen: Pygame surface for rendering
        """
        self.collision_system = collision_system
        self.screen = screen
        self.camera_offset = (0, 0)  # Camera offset for world-to-screen transformation
        self.show_grid = True        # Show spatial grid lines
        self.show_colliders = True   # Show collision shapes
        self.show_performance = True # Show performance stats
        self.show_collisions = True  # Highlight active collisions
        
        # Colors for different entity types
        self.colors = {
            'player': (0, 255, 0),        # Green
            'enemy': (255, 0, 0),         # Red
            'projectile': (255, 255, 0),  # Yellow
            'wall': (128, 128, 128),      # Gray
            'item': (0, 0, 255),          # Blue
            'trigger': (255, 0, 255),     # Magenta
            'disabled': (64, 64, 64),     # Dark gray
            'grid': (50, 50, 50),         # Grid line color
            'collision': (255, 165, 0),   # Orange for active collisions
            'text': (255, 255, 255),      # White for text
            'background': (0, 0, 0)       # Black background
        }
        
        # Font for text rendering
        try:
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
        except:
            # Fallback if font loading fails
            self.font = pygame.font.SysFont('Arial', 24)
            self.small_font = pygame.font.SysFont('Arial', 18)
    
    def render(self) -> None:
        """Render all debug visualization elements
        
        Call this method each frame to draw debug information
        """
        # Clear screen
        self.screen.fill(self.colors['background'])
        
        # Draw spatial grid first (background layer)
        if self.show_grid:
            self._render_grid()
        
        # Draw colliders
        if self.show_colliders:
            self._render_colliders()
        
        # Draw active collisions
        if self.show_collisions:
            self._render_collisions()
        
        # Draw performance metrics
        if self.show_performance:
            self._render_performance_stats()
    
    def _render_grid(self) -> None:
        """Render spatial grid lines"""
        cell_size = self.collision_system.cell_size
        world_width = self.collision_system.world_width
        world_height = self.collision_system.world_height
        
        # Vertical grid lines
        for x in range(0, world_width, cell_size):
            start_x = x - self.camera_offset[0]
            end_x = x - self.camera_offset[0]
            start_y = -self.camera_offset[1]
            end_y = world_height - self.camera_offset[1]
            
            if 0 <= start_x <= self.screen.get_width():
                pygame.draw.line(self.screen, self.colors['grid'], 
                               (start_x, start_y), (end_x, end_y), 1)
        
        # Horizontal grid lines
        for y in range(0, world_height, cell_size):
            start_x = -self.camera_offset[0]
            end_x = world_width - self.camera_offset[0]
            start_y = y - self.camera_offset[1]
            end_y = y - self.camera_offset[1]
            
            if 0 <= start_y <= self.screen.get_height():
                pygame.draw.line(self.screen, self.colors['grid'],
                               (start_x, start_y), (end_x, start_y), 1)
    
    def _render_colliders(self) -> None:
        """Render all entity collision shapes"""
        for entity_id, collider in self.collision_system.colliders.items():
            if not collider.enabled:
                continue
                
            # Get entity position
            position = self.collision_system.entity_positions.get(entity_id)
            if not position:
                continue
            
            # Calculate world center
            center_x, center_y = collider.world_center(position[0], position[1])
            
            # Transform world coordinates to screen coordinates
            screen_x = center_x - self.camera_offset[0]
            screen_y = center_y - self.camera_offset[1]
            
            # Skip if not visible on screen
            if (screen_x < -collider.radius or screen_x > self.screen.get_width() + collider.radius or
                screen_y < -collider.radius or screen_y > self.screen.get_height() + collider.radius):
                continue
            
            # Determine color based on entity type and state
            color = self._get_entity_color(collider)
            
            # Draw collision circle
            pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), collider.radius, 2)
            
            # Draw center point
            pygame.draw.circle(self.screen, (255, 255, 255), (int(screen_x), int(screen_y)), 2)
            
            # Draw entity ID
            if self.collision_system.get_entity_count() < 100:  # Only show IDs for small numbers
                text = self.small_font.render(str(entity_id), True, self.colors['text'])
                text_rect = text.get_rect(center=(screen_x, screen_y - collider.radius - 10))
                self.screen.blit(text, text_rect)
    
    def _render_collisions(self) -> None:
        """Render active collision pairs"""
        for entity_a, entity_b in self.collision_system.active_collisions:
            # Get positions and colliders
            pos_a = self.collision_system.entity_positions.get(entity_a)
            pos_b = self.collision_system.entity_positions.get(entity_b)
            
            if not pos_a or not pos_b:
                continue
                
            collider_a = self.collision_system.colliders.get(entity_a)
            collider_b = self.collision_system.colliders.get(entity_b)
            
            if not collider_a or not collider_b:
                continue
            
            # Calculate world centers
            center_a = collider_a.world_center(pos_a[0], pos_a[1])
            center_b = collider_b.world_center(pos_b[0], pos_b[1])
            
            # Transform to screen coordinates
            screen_a_x = center_a[0] - self.camera_offset[0]
            screen_a_y = center_a[1] - self.camera_offset[1]
            screen_b_x = center_b[0] - self.camera_offset[0]
            screen_b_y = center_b[1] - self.camera_offset[1]
            
            # Draw line connecting colliding entities
            pygame.draw.line(self.screen, self.colors['collision'],
                           (screen_a_x, screen_a_y), (screen_b_x, screen_b_y), 2)
            
            # Highlight the collision circles
            pygame.draw.circle(self.screen, self.colors['collision'], 
                             (int(screen_a_x), int(screen_a_y)), collider_a.radius, 1)
            pygame.draw.circle(self.screen, self.colors['collision'],
                             (int(screen_b_x), int(screen_b_y)), collider_b.radius, 1)
    
    def _render_performance_stats(self) -> None:
        """Render performance statistics overlay"""
        stats = self.collision_system.get_performance_stats()
        
        # Position for stats display (top-right corner)
        start_x = self.screen.get_width() - 250
        start_y = 10
        
        # Background for text
        bg_rect = pygame.Rect(start_x - 10, start_y - 10, 240, 200)
        pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
        pygame.draw.rect(self.screen, self.colors['grid'], bg_rect, 2)
        
        # Render performance metrics
        y_offset = start_y
        line_height = 18
        
        stats_texts = [
            f"Entities: {stats['entities_count']}",
            f"Collision Checks: {stats['collision_checks']}",
            f"Collisions Found: {stats['collisions_found']}",
            f"Total Time: {stats['last_frame_time']*1000:.2f}ms",
            f"Grid Build: {stats['grid_rebuild_time']*1000:.2f}ms",
            f"Broad Phase: {stats['broad_phase_time']*1000:.2f}ms",
            f"Narrow Phase: {stats['narrow_phase_time']*1000:.2f}ms",
            f"Cell Count: {len(self.collision_system.grid.cells)}",
            f"Grid Size: {self.collision_system.grid.grid_width}x{self.collision_system.grid.grid_height}"
        ]
        
        for text in stats_texts:
            if y_offset < self.screen.get_height() - 20:
                rendered = self.small_font.render(text, True, self.colors['text'])
                self.screen.blit(rendered, (start_x, y_offset))
                y_offset += line_height
    
    def _get_entity_color(self, collider: Collider) -> Tuple[int, int, int]:
        """Determine entity color based on layer and state"""
        if not collider.enabled:
            return self.colors['disabled']
        
        # Determine color based on layer
        if collider.is_trigger:
            return self.colors['trigger']
        elif collider.layer == 1:  # CollisionLayers.PLAYER
            return self.colors['player']
        elif collider.layer == 2:  # CollisionLayers.ENEMIES
            return self.colors['enemy']
        elif collider.layer == 4:  # CollisionLayers.PROJECTILES
            return self.colors['projectile']
        elif collider.layer == 8:  # CollisionLayers.WALLS
            return self.colors['wall']
        elif collider.layer == 16:  # CollisionLayers.ITEMS
            return self.colors['item']
        else:
            # Unknown layer - random color based on layer ID
            color_seed = collider.layer * 37  # Pseudo-random
            r = (color_seed * 17) % 256
            g = (color_seed * 23) % 256
            b = (color_seed * 29) % 256
            return (r, g, b)
    
    def set_camera_offset(self, offset_x: int, offset_y: int) -> None:
        """Set camera offset for world-to-screen transformation
        
        Args:
            offset_x: X offset in pixels
            offset_y: Y offset in pixels
        """
        self.camera_offset = (offset_x, offset_y)
    
    def toggle_grid(self) -> None:
        """Toggle grid visibility"""
        self.show_grid = not self.show_grid
    
    def toggle_colliders(self) -> None:
        """Toggle collider visibility"""
        self.show_colliders = not self.show_colliders
    
    def toggle_performance(self) -> None:
        """Toggle performance stats visibility"""
        self.show_performance = not self.show_performance
    
    def toggle_collisions(self) -> None:
        """Toggle collision highlighting"""
        self.show_collisions = not self.show_collisions
    
    def handle_debug_input(self, event) -> bool:
        """Handle debug-specific input events
        
        Args:
            event: Pygame event
            
        Returns:
            True if event was handled by debug system
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g:
                self.toggle_grid()
                return True
            elif event.key == pygame.K_c:
                self.toggle_colliders()
                return True
            elif event.key == pygame.K_p:
                self.toggle_performance()
                return True
            elif event.key == pygame.K_h:
                self.toggle_collisions()
                return True
        
        return False


class PerformanceProfiler:
    """Performance profiler for collision system operations
    
    Provides detailed timing and profiling information for collision detection.
    """
    
    def __init__(self):
        """Initialize performance profiler"""
        self.frame_times = []
        self.operation_times = {}
        self.max_samples = 300  # Keep last 300 samples
        self.collision_counts = []
    
    def start_frame(self) -> None:
        """Mark the start of a new frame"""
        self.frame_start = __import__('time').perf_counter()
    
    def end_frame(self) -> None:
        """Mark the end of a frame and record timing"""
        frame_time = __import__('time').perf_counter() - self.frame_start
        self.frame_times.append(frame_time)
        
        # Keep only recent samples
        if len(self.frame_times) > self.max_samples:
            self.frame_times.pop(0)
    
    def record_operation(self, operation_name: str, duration: float) -> None:
        """Record timing for a specific operation
        
        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
        """
        if operation_name not in self.operation_times:
            self.operation_times[operation_name] = []
        
        self.operation_times[operation_name].append(duration)
        
        # Keep only recent samples
        if len(self.operation_times[operation_name]) > self.max_samples:
            self.operation_times[operation_name].pop(0)
    
    def record_collision_count(self, count: int) -> None:
        """Record number of collisions found in a frame
        
        Args:
            count: Number of collisions
        """
        self.collision_counts.append(count)
        
        # Keep only recent samples
        if len(self.collision_counts) > self.max_samples:
            self.collision_counts.pop(0)
    
    def get_fps(self) -> float:
        """Get current FPS based on frame times
        
        Returns:
            FPS (frames per second)
        """
        if not self.frame_times:
            return 0.0
        
        recent_times = self.frame_times[-60:]  # Last 60 frames
        avg_frame_time = sum(recent_times) / len(recent_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def get_operation_stats(self, operation_name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a specific operation
        
        Args:
            operation_name: Name of operation to get stats for
            
        Returns:
            Dictionary with min, max, avg timings or None if operation not found
        """
        if operation_name not in self.operation_times:
            return None
        
        times = self.operation_times[operation_name]
        if not times:
            return None
        
        return {
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'samples': len(times)
        }
    
    def get_collision_stats(self) -> Optional[Dict[str, float]]:
        """Get statistics for collision counts
        
        Returns:
            Dictionary with collision count statistics
        """
        if not self.collision_counts:
            return None
        
        return {
            'min': min(self.collision_counts),
            'max': max(self.collision_counts),
            'avg': sum(self.collision_counts) / len(self.collision_counts),
            'samples': len(self.collision_counts)
        }
    
    def clear_stats(self) -> None:
        """Clear all collected statistics"""
        self.frame_times.clear()
        self.operation_times.clear()
        self.collision_counts.clear()
    
    def generate_report(self) -> str:
        """Generate a performance report string
        
        Returns:
            Formatted performance report
        """
        fps = self.get_fps()
        collision_stats = self.get_collision_stats()
        
        report = f"Collision System Performance Report\n"
        report += f"{'='*40}\n"
        report += f"Current FPS: {fps:.1f}\n"
        report += f"Frame Time Samples: {len(self.frame_times)}\n\n"
        
        if collision_stats:
            report += f"Collision Statistics:\n"
            report += f"  Average: {collision_stats['avg']:.1f} collisions/frame\n"
            report += f"  Min: {collision_stats['min']} collisions/frame\n"
            report += f"  Max: {collision_stats['max']} collisions/frame\n\n"
        
        report += f"Operation Timing (last {self.max_samples} samples):\n"
        for operation, stats in self.get_operation_stats.items():
            if stats:
                report += f"  {operation}:\n"
                report += f"    Avg: {stats['avg']*1000:.2f}ms\n"
                report += f"    Min: {stats['min']*1000:.2f}ms\n"
                report += f"    Max: {stats['max']*1000:.2f}ms\n"
        
        return report


# Keyboard shortcuts for debug controls
DEBUG_KEYS = {
    pygame.K_g: "Toggle Grid",
    pygame.K_c: "Toggle Colliders", 
    pygame.K_p: "Toggle Performance Stats",
    pygame.K_h: "Toggle Collision Highlighting"
}