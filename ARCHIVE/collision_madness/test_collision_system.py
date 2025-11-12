# systems/collision/test_collision_system.py
"""
Comprehensive test suite for collision system.
Tests all components: colliders, collision math, spatial grid, and collision system.
"""

import unittest
import math
import time
from typing import List, Tuple

from .collider import Collider, CollisionEvent, CollisionLayers, ColliderTemplates
from .collision_math import (
    circle_collide, circle_collision_info, resolve_circle_overlap,
    point_in_circle, circle_line_intersection, raycast_circle, SpatialGrid
)
from .collision_system import CollisionSystem


class TestCollider(unittest.TestCase):
    """Test suite for Collider dataclass"""
    
    def test_collider_creation(self):
        """Test basic collider creation and properties"""
        collider = Collider(
            entity_id=1,
            diameter=32,
            offset_x=5,
            offset_y=10,
            layer=CollisionLayers.PLAYER,
            is_trigger=False,
            enabled=True
        )
        
        self.assertEqual(collider.entity_id, 1)
        self.assertEqual(collider.diameter, 32)
        self.assertEqual(collider.radius, 16)
        self.assertEqual(collider.offset_x, 5)
        self.assertEqual(collider.offset_y, 10)
        self.assertEqual(collider.layer, CollisionLayers.PLAYER)
        self.assertFalse(collider.is_trigger)
        self.assertTrue(collider.enabled)
    
    def test_world_center(self):
        """Test world center calculation with offsets"""
        collider = Collider(1, 32, 5, 10, CollisionLayers.PLAYER)
        center_x, center_y = collider.world_center(100, 200)
        
        self.assertEqual(center_x, 105)  # 100 + 5
        self.assertEqual(center_y, 210)  # 200 + 10
    
    def test_layer_compatibility(self):
        """Test layer-based collision filtering"""
        player_collider = Collider(1, 32, 0, 0, CollisionLayers.PLAYER)
        enemy_collider = Collider(2, 24, 0, 0, CollisionLayers.ENEMIES)
        wall_collider = Collider(3, 64, 0, 0, CollisionLayers.WALLS)
        
        # Compatible layers
        self.assertTrue(player_collider.check_layer_compatible(CollisionLayers.ENEMIES))
        self.assertTrue(enemy_collider.check_layer_compatible(CollisionLayers.PLAYER))
        
        # Incompatible layers
        self.assertFalse(player_collider.check_layer_compatible(CollisionLayers.WALLS))
        self.assertFalse(wall_collider.check_layer_compatible(CollisionLayers.PROJECTILES))
    
    def test_collider_templates(self):
        """Test predefined collider templates"""
        player = ColliderTemplates.player(diameter=32)
        self.assertEqual(player.diameter, 32)
        self.assertEqual(player.layer, CollisionLayers.PLAYER)
        
        enemy = ColliderTemplates.enemy(diameter=24)
        self.assertEqual(enemy.diameter, 24)
        self.assertEqual(enemy.layer, CollisionLayers.ENEMIES)
        
        projectile = ColliderTemplates.projectile(diameter=8)
        self.assertEqual(projectile.diameter, 8)
        self.assertEqual(projectile.layer, CollisionLayers.PROJECTILES)


class TestCollisionMath(unittest.TestCase):
    """Test suite for collision mathematics"""
    
    def test_circle_collision_no_overlap(self):
        """Test circles that don't collide"""
        self.assertFalse(circle_collide((0, 0), 10, (30, 0), 10))  # Separate
        self.assertFalse(circle_collide((0, 0), 5, (15, 0), 5))   # Just touching (edge case)
    
    def test_circle_collision_with_overlap(self):
        """Test circles that do collide"""
        self.assertTrue(circle_collide((0, 0), 10, (15, 0), 10))  # Overlapping
        self.assertTrue(circle_collide((0, 0), 20, (10, 0), 20))  # Heavy overlap
        self.assertTrue(circle_collide((5, 5), 10, (15, 15), 10)) # Diagonal overlap
    
    def test_circle_collision_exact_center(self):
        """Test circles with same center position"""
        # Same position, same radius - should collide
        self.assertTrue(circle_collide((10, 10), 10, (10, 10), 10))
        
        # Same position, different radius - should collide
        self.assertTrue(circle_collide((10, 10), 5, (10, 10), 15))
    
    def test_collision_info(self):
        """Test detailed collision information"""
        # No collision
        info = circle_collision_info((0, 0), 10, (30, 0), 10)
        self.assertIsNone(info)
        
        # With collision
        info = circle_collision_info((0, 0), 10, (15, 0), 10)
        self.assertIsNotNone(info)
        
        normal_x, normal_y, penetration = info
        self.assertAlmostEqual(normal_x, 1.0, places=2)  # Should point from A to B
        self.assertAlmostEqual(normal_y, 0.0, places=2)
        self.assertAlmostEqual(penetration, 5.0, places=2)  # 20 - 15 = 5
    
    def test_overlap_resolution(self):
        """Test circle overlap resolution"""
        # Overlapping circles
        delta_a_x, delta_a_y, delta_b_x, delta_b_y = resolve_circle_overlap(
            (0, 0), 10, (15, 0), 10
        )
        
        # They should be pushed apart
        self.assertAlmostEqual(delta_a_x, -2.5, places=1)  # A moves left
        self.assertAlmostEqual(delta_b_x, 2.5, places=1)   # B moves right
        self.assertEqual(delta_a_y, 0.0)
        self.assertEqual(delta_b_y, 0.0)
    
    def test_point_in_circle(self):
        """Test point-in-circle detection"""
        center = (10, 10)
        radius = 5
        
        # Points inside circle
        self.assertTrue(point_in_circle((10, 10), center, radius))  # Center
        self.assertTrue(point_in_circle((12, 10), center, radius))  # Edge
        self.assertTrue(point_in_circle((8, 8), center, radius))    # Corner
        
        # Points outside circle
        self.assertFalse(point_in_circle((16, 10), center, radius)) # Outside
        self.assertFalse(point_in_circle((10, 20), center, radius)) # Outside
    
    def test_raycast_circle(self):
        """Test raycast against circle"""
        start = (0, 0)
        direction = (1, 0)  # Right
        center = (10, 0)
        radius = 5
        
        # Ray hits circle
        hit = raycast_circle(start, direction, 20, center, radius)
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit, 5.0, places=1)  # Hits at x=5
        
        # Ray misses circle
        direction = (0, 1)  # Up
        hit = raycast_circle(start, direction, 20, center, radius)
        self.assertIsNone(hit)


class TestSpatialGrid(unittest.TestCase):
    """Test suite for spatial grid partitioning"""
    
    def setUp(self):
        """Set up spatial grid for testing"""
        self.grid = SpatialGrid(128, 128, cell_size=32)
    
    def test_cell_coordinate_conversion(self):
        """Test world to grid coordinate conversion"""
        grid = SpatialGrid(128, 128, 32)
        
        # Test corner cases
        self.assertEqual(grid._get_cell_coords(0, 0), (0, 0))
        self.assertEqual(grid._get_cell_coords(31, 31), (0, 0))
        self.assertEqual(grid._get_cell_coords(32, 32), (1, 1))
        self.assertEqual(grid._get_cell_coords(127, 127), (3, 3))
    
    def test_entity_add_remove(self):
        """Test adding and removing entities from grid"""
        # Add entity
        self.grid.add_entity(1, 16, 16, 8)  # Centered in cell (0,0)
        self.assertIn(1, list(self.grid.cells.values())[0])
        
        # Remove entity
        self.grid.remove_entity(1, 16, 16, 8)
        self.assertNotIn(1, self.grid.cells.get(list(self.grid.cells.keys())[0], set()))
    
    def test_query_circle(self):
        """Test circular area queries"""
        # Add some entities
        self.grid.add_entity(1, 16, 16, 8)   # Cell (0,0)
        self.grid.add_entity(2, 48, 16, 8)   # Cell (1,0)
        self.grid.add_entity(3, 80, 80, 8)   # Cell (2,2)
        
        positions = {
            1: (16, 16),
            2: (48, 16),
            3: (80, 80)
        }
        
        # Query around entity 1
        results = self.grid.query_circle((16, 16), 16, positions)
        self.assertIn(1, results)
        self.assertIn(2, results)  # Should be in neighboring cell
        
        # Query around entity 3 (isolated)
        results = self.grid.query_circle((80, 80), 16, positions)
        self.assertIn(3, results)
        self.assertNotIn(1, results)
        self.assertNotIn(2, results)
    
    def test_multicell_entities(self):
        """Test entities that span multiple grid cells"""
        # Add large entity that spans multiple cells
        self.grid.add_entity(1, 32, 32, 20)  # Should span cells (0,0), (1,0), (0,1), (1,1)
        
        # Check it exists in multiple cells
        cells_with_entity = []
        for cell_entities in self.grid.cells.values():
            if 1 in cell_entities:
                cells_with_entity.append(cell_entities)
        
        self.assertGreater(len(cells_with_entity), 1)


class TestCollisionSystem(unittest.TestCase):
    """Test suite for main collision system"""
    
    def setUp(self):
        """Set up collision system for testing"""
        self.collision_system = CollisionSystem(world_width=256, world_height=256, cell_size=64)
    
    def test_register_unregister(self):
        """Test entity registration and unregistration"""
        collider = Collider(1, 32, 0, 0, CollisionLayers.PLAYER)
        
        # Register entity
        success = self.collision_system.register(1, collider, (10, 10))
        self.assertTrue(success)
        self.assertEqual(self.collision_system.get_entity_count(), 1)
        
        # Try to register same entity again
        success = self.collision_system.register(1, collider, (10, 10))
        self.assertFalse(success)
        
        # Unregister entity
        success = self.collision_system.unregister(1)
        self.assertTrue(success)
        self.assertEqual(self.collision_system.get_entity_count(), 0)
    
    def test_position_updates(self):
        """Test batch position updates"""
        collider = Collider(1, 32, 0, 0, CollisionLayers.PLAYER)
        self.collision_system.register(1, collider, (10, 10))
        
        # Update position
        self.collision_system.update_positions({1: (50, 50)})
        
        # Check position was updated
        self.assertEqual(self.collision_system.entity_positions[1], (50, 50))
    
    def test_collision_detection(self):
        """Test collision detection between entities"""
        # Create two colliding entities
        collider_a = Collider(1, 32, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
        collider_b = Collider(2, 32, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
        
        self.collision_system.register(1, collider_a, (0, 0))
        self.collision_system.register(2, collider_b, (20, 0))  # Close enough to collide
        
        # Run collision detection
        collisions = self.collision_system.update()
        
        # Should find one collision
        self.assertEqual(len(collisions), 1)
        collision = collisions[0]
        
        self.assertIn(collision.entity_a, [1, 2])
        self.assertIn(collision.entity_b, [1, 2])
        self.assertGreater(collision.penetration, 0)
    
    def test_layer_filtering(self):
        """Test layer-based collision filtering"""
        # Create entities with incompatible layers
        player = Collider(1, 32, 0, 0, CollisionLayers.PLAYER)
        wall = Collider(2, 64, 0, 0, CollisionLayers.WALLS)
        
        self.collision_system.register(1, player, (0, 0))
        self.collision_system.register(2, wall, (50, 0))  # Shouldn't collide due to layers
        
        collisions = self.collision_system.update()
        
        # Should not find collisions (layers don't overlap)
        self.assertEqual(len(collisions), 0)
    
    def test_query_circle(self):
        """Test circular area queries"""
        # Create entities in different locations
        entities = [
            (1, Collider(1, 16, 0, 0, CollisionLayers.PLAYER), (16, 16)),
            (2, Collider(2, 16, 0, 0, CollisionLayers.ENEMIES), (48, 16)),
            (3, Collider(3, 16, 0, 0, CollisionLayers.ITEMS), (80, 80))
        ]
        
        for entity_id, collider, pos in entities:
            self.collision_system.register(entity_id, collider, pos)
        
        # Query around first two entities
        results = self.collision_system.query_circle((32, 16), 20)
        
        self.assertIn(1, results)  # Should find entity 1
        self.assertIn(2, results)  # Should find entity 2
        self.assertNotIn(3, results)  # Should not find entity 3
    
    def test_raycast(self):
        """Test raycast functionality"""
        # Create entities
        wall = Collider(1, 32, 0, 0, CollisionLayers.WALLS)
        player = Collider(2, 16, 0, 0, CollisionLayers.PLAYER)
        
        self.collision_system.register(1, wall, (50, 25))
        self.collision_system.register(2, player, (100, 25))
        
        # Raycast from left to right
        hit = self.collision_system.raycast((0, 25), (1, 0), 100)
        
        self.assertIsNotNone(hit)
        entity_id, distance, hit_point = hit
        self.assertEqual(entity_id, 1)  # Should hit the wall
        self.assertLess(distance, 100)
    
    def test_trigger_entities(self):
        """Test trigger-only collision detection"""
        # Create trigger entities
        trigger_a = Collider(1, 32, 0, 0, CollisionLayers.PLAYER, is_trigger=True)
        trigger_b = Collider(2, 32, 0, 0, CollisionLayers.ENEMIES, is_trigger=True)
        
        self.collision_system.register(1, trigger_a, (0, 0))
        self.collision_system.register(2, trigger_b, (20, 0))
        
        collisions = self.collision_system.update()
        
        # Should find collision
        self.assertEqual(len(collisions), 1)
        self.assertTrue(collisions[0].is_trigger)
    
    def test_disabled_entities(self):
        """Test entities that are disabled"""
        # Create enabled and disabled entities
        enabled = Collider(1, 32, 0, 0, CollisionLayers.PLAYER, enabled=True)
        disabled = Collider(2, 32, 0, 0, CollisionLayers.ENEMIES, enabled=False)
        
        self.collision_system.register(1, enabled, (0, 0))
        self.collision_system.register(2, disabled, (20, 0))  # Would collide if enabled
        
        collisions = self.collision_system.update()
        
        # Should not find collision (one entity is disabled)
        self.assertEqual(len(collisions), 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for collision system at scale"""
    
    def test_large_entity_count(self):
        """Test collision system with many entities"""
        collision_system = CollisionSystem(world_width=1024, world_height=1024, cell_size=64)
        
        # Create many entities
        start_time = time.time()
        for i in range(1000):
            collider = Collider(i, 16, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
            x = (i % 32) * 32  # Distribute entities across grid
            y = (i // 32) * 32
            collision_system.register(i, collider, (x, y))
        
        register_time = time.time() - start_time
        
        # Run collision detection
        start_time = time.time()
        collisions = collision_system.update()
        detection_time = time.time() - start_time
        
        # Performance assertions (these are flexible - adjust as needed)
        self.assertLess(register_time, 1.0)  # Should register 1000 entities in under 1 second
        self.assertLess(detection_time, 0.1)  # Should detect collisions in under 0.1 seconds
        
        # Print performance metrics for manual review
        stats = collision_system.get_performance_stats()
        print(f"Performance Test Results:")
        print(f"  Entities: {stats['entities_count']}")
        print(f"  Register time: {register_time*1000:.2f}ms")
        print(f"  Detection time: {detection_time*1000:.2f}ms")
        print(f"  Collision checks: {stats['collision_checks']}")
        print(f"  Collisions found: {stats['collisions_found']}")
    
    def test_stress_spatial_grid(self):
        """Test spatial grid performance with random positions"""
        grid = SpatialGrid(512, 512, 32)
        
        # Add many entities at random positions
        start_time = time.time()
        for i in range(500):
            x = (i * 137) % 512  # Pseudo-random positions
            y = (i * 173) % 512
            grid.add_entity(i, x, y, 8)
        
        add_time = time.time() - start_time
        
        # Query performance
        start_time = time.time()
        for _ in range(100):
            query_center = ((i * 41) % 512, (i * 59) % 512)
            grid.query_circle(query_center, 32, {})
        
        query_time = time.time() - start_time
        
        print(f"Spatial Grid Stress Test:")
        print(f"  Add time for 500 entities: {add_time*1000:.2f}ms")
        print(f"  Query time for 100 queries: {query_time*1000:.2f}ms")
        print(f"  Grid cell count: {len(grid.cells)}")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_zero_radius_collider(self):
        """Test collider with zero radius"""
        collider = Collider(1, 0, 0, 0, CollisionLayers.PLAYER)
        self.assertEqual(collider.radius, 0)
        
        # Should not collide with anything
        collision_system = CollisionSystem()
        collider_a = Collider(1, 0, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
        collider_b = Collider(2, 32, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
        
        collision_system.register(1, collider_a, (0, 0))
        collision_system.register(2, collider_b, (10, 0))
        
        collisions = collision_system.update()
        self.assertEqual(len(collisions), 0)
    
    def test_very_large_entities(self):
        """Test entities larger than grid cells"""
        collision_system = CollisionSystem(world_width=128, world_height=128, cell_size=32)
        
        # Entity larger than grid cell
        large_collider = Collider(1, 128, 0, 0, CollisionLayers.PLAYER)
        collision_system.register(1, large_collider, (64, 64))
        
        # Should still work
        self.assertEqual(collision_system.get_entity_count(), 1)
    
    def test_entity_outside_world_bounds(self):
        """Test entities positioned outside world bounds"""
        collision_system = CollisionSystem(world_width=100, world_height=100, cell_size=25)
        
        # Entity outside bounds - should still register but not cause errors
        collider = Collider(1, 16, 0, 0, CollisionLayers.PLAYER)
        success = collision_system.register(1, collider, (200, 200))
        
        # Registration should succeed (no bounds checking in register)
        self.assertTrue(success)
    
    def test_max_entities_limit(self):
        """Test entity count limits"""
        collision_system = CollisionSystem(max_entities=10)
        
        # Should be able to register up to limit
        for i in range(10):
            collider = Collider(i, 16, 0, 0, CollisionLayers.PLAYER)
            success = collision_system.register(i, collider, (i * 10, 0))
            self.assertTrue(success)
        
        # Should fail for entity ID exceeding limit
        collider = Collider(15, 16, 0, 0, CollisionLayers.PLAYER)
        with self.assertRaises(ValueError):
            collision_system.register(15, collider, (0, 0))


def run_performance_benchmark():
    """Run a comprehensive performance benchmark"""
    print("Running Collision System Performance Benchmark")
    print("=" * 50)
    
    # Test different entity counts
    entity_counts = [100, 500, 1000, 2000]
    
    for count in entity_counts:
        print(f"\nTesting with {count} entities:")
        
        collision_system = CollisionSystem(world_width=1024, world_height=1024, cell_size=64)
        
        # Create entities
        start_time = time.time()
        for i in range(count):
            collider = Collider(i, 16, 0, 0, CollisionLayers.PLAYER | CollisionLayers.ENEMIES)
            x = (i % 32) * 32
            y = (i // 32) * 32
            collision_system.register(i, collider, (x, y))
        
        register_time = time.time() - start_time
        
        # Run multiple collision detection passes
        detection_times = []
        for _ in range(10):
            start_time = time.time()
            collisions = collision_system.update()
            detection_time = time.time() - start_time
            detection_times.append(detection_time)
        
        avg_detection_time = sum(detection_times) / len(detection_times)
        stats = collision_system.get_performance_stats()
        
        print(f"  Registration: {register_time*1000:.2f}ms")
        print(f"  Avg detection: {avg_detection_time*1000:.2f}ms")
        print(f"  Max detection: {max(detection_times)*1000:.2f}ms")
        print(f"  Collision checks: {stats['collision_checks']}")
        print(f"  Collisions found: {stats['collisions_found']}")
        print(f"  Grid cells: {len(collision_system.grid.cells)}")


if __name__ == '__main__':
    # Run unit tests
    print("Running Collision System Unit Tests")
    print("=" * 40)
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 50)
    
    # Run performance benchmark
    run_performance_benchmark()