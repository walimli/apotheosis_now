"""WorldBuilder orchestrates chunk generation using cellular automata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from services.world_builder.moss_builder import apply_moss

TileArray = np.ndarray


@dataclass
class WorldBuilder:
    seed: int
    chunk_size: int = 32
    land_probability: float = 0.45
    ca_steps: int = 5
    spike_neighbor_threshold: int = 3
    minimum_island_size: int = 4
    chunk_padding: int = 1

    _hash_mul_a: np.uint64 = field(
        default=np.uint64(6364136223846793005), init=False, repr=False
    )
    _hash_mul_b: np.uint64 = field(
        default=np.uint64(1442695040888963407), init=False, repr=False
    )
    _hash_mul_c: np.uint64 = field(default=np.uint64(22695477), init=False, repr=False)
    _hash_mask: np.uint64 = field(
        default=np.uint64((1 << 64) - 1), init=False, repr=False
    )

    def generate_chunk(
        self, chunk_x: int, chunk_y: int
    ) -> Tuple[TileArray, List[object]]:
        """Create a deterministic chunk of tiles and an empty object list."""
        grid = self._create_initial_grid(chunk_x, chunk_y)
        for _ in range(self.ca_steps):
            grid = self._cellular_step(grid)
        grid = self._prune_spikes(grid)
        grid = self._remove_small_islands(grid)
        grid = self._remove_bridges(grid)

        if self.chunk_padding > 0:
            start = self.chunk_padding
            end = -self.chunk_padding
            grid = grid[start:end, start:end]

        # Phase 2: assign a single biome id to each island deterministically
        grid = self._assign_biomes(grid, chunk_x, chunk_y)

        # Phase 3: moss CA per island (code 4)
        grid = apply_moss(grid, chunk_x, chunk_y, self.seed)

        return grid.astype(np.int8, copy=False), []

    def _create_initial_grid(self, chunk_x: int, chunk_y: int) -> TileArray:
        pad = self.chunk_padding
        size = self.chunk_size + pad * 2
        start_x = chunk_x * self.chunk_size - pad
        start_y = chunk_y * self.chunk_size - pad

        x_coords = np.arange(start_x, start_x + size, dtype=np.int64)
        y_coords = np.arange(start_y, start_y + size, dtype=np.int64)
        x_grid, y_grid = np.meshgrid(x_coords, y_coords)

        random_values = self._hashed_random(x_grid, y_grid)
        return (random_values < self.land_probability).astype(np.int8)

    def _hashed_random(self, x_grid: TileArray, y_grid: TileArray) -> TileArray:
        seed_val = np.uint64(self.seed)

        mix = np.uint64(seed_val * self._hash_mul_a)
        mix ^= np.uint64(x_grid) * self._hash_mul_b
        mix ^= np.uint64(y_grid) * self._hash_mul_c
        mix &= self._hash_mask

        mix ^= mix >> np.uint64(33)
        mix *= np.uint64(0xFF51AFD7ED558CCD)
        mix &= self._hash_mask
        mix ^= mix >> np.uint64(33)
        mix *= np.uint64(0xC4CEB9FE1A85EC53)
        mix &= self._hash_mask
        mix ^= mix >> np.uint64(33)

        return (mix & np.uint64((1 << 53) - 1)).astype(np.float64) / float(1 << 53)

    def _cellular_step(self, grid: TileArray) -> TileArray:
        neighbors = self._neighbor_counts(grid)
        survive = (grid == 1) & (neighbors >= 4)
        birth = (grid == 0) & (neighbors > 4)
        return np.where(survive | birth, 1, 0).astype(np.int8)

    @staticmethod
    def _neighbor_counts(grid: TileArray) -> TileArray:
        padded = np.pad(grid, 1, mode="constant", constant_values=0)
        neighbors = (
            padded[:-2, :-2]
            + padded[:-2, 1:-1]
            + padded[:-2, 2:]
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
            + padded[2:, :-2]
            + padded[2:, 1:-1]
            + padded[2:, 2:]
        )
        return neighbors.astype(np.int8)

    def _prune_spikes(self, grid: TileArray) -> TileArray:
        neighbors = self._neighbor_counts(grid)
        mask = (grid == 1) & (neighbors < self.spike_neighbor_threshold)
        result = grid.copy()
        result[mask] = 0
        return result

    def _remove_small_islands(self, grid: TileArray) -> TileArray:
        rows, cols = grid.shape
        visited = np.zeros((rows, cols), dtype=bool)

        def explore(start_row: int, start_col: int) -> List[Tuple[int, int]]:
            stack = [(start_row, start_col)]
            component: List[Tuple[int, int]] = []
            visited[start_row, start_col] = True
            while stack:
                row, col = stack.pop()
                component.append((row, col))
                for neighbor in self._orthogonal_neighbors(row, col, rows, cols):
                    n_row, n_col = neighbor
                    if grid[n_row, n_col] == 1 and not visited[n_row, n_col]:
                        visited[n_row, n_col] = True
                        stack.append((n_row, n_col))
            return component

        result = grid.copy()
        for row in range(rows):
            for col in range(cols):
                if grid[row, col] == 1 and not visited[row, col]:
                    component = explore(row, col)
                    if len(component) < self.minimum_island_size:
                        for c_row, c_col in component:
                            result[c_row, c_col] = 0
        return result

    def _remove_bridges(self, grid: TileArray) -> TileArray:
        rows, cols = grid.shape
        result = grid.copy()
        for row in range(rows):
            for col in range(cols):
                if grid[row, col] == 0:
                    continue
                north = grid[row - 1, col] if row > 0 else 0
                south = grid[row + 1, col] if row < rows - 1 else 0
                west = grid[row, col - 1] if col > 0 else 0
                east = grid[row, col + 1] if col < cols - 1 else 0
                if west == 0 and east == 0:
                    result[row, col] = 0
                elif north == 0 and south == 0:
                    result[row, col] = 0
        return result

    # --- Phase 2: island biomes ---
    def _assign_biomes(self, grid: TileArray, chunk_x: int, chunk_y: int) -> TileArray:
        """Assign a homogeneous biome id to each island (land component).

        Weights per island:
        - clay (1):    50%
        - stone (3):   30%
        - redrock (2): 20%
        """
        if grid.size == 0:
            return grid
        rows, cols = grid.shape
        visited = np.zeros((rows, cols), dtype=bool)
        result = grid.astype(np.int8, copy=True)

        rng = self._rng_for_chunk(chunk_x, chunk_y)

        def choose_biome() -> int:
            r = float(rng.random())
            if r < 0.5:
                return 1  # clay
            elif r < 0.8:
                return 3  # stone
            else:
                return 2  # redrock

        for row in range(rows):
            for col in range(cols):
                if result[row, col] == 0 or visited[row, col]:
                    continue
                # Explore this island (4-connected component)
                stack = [(row, col)]
                component: list[tuple[int, int]] = []
                visited[row, col] = True
                while stack:
                    cr, cc = stack.pop()
                    component.append((cr, cc))
                    for nr, nc in self._orthogonal_neighbors(cr, cc, rows, cols):
                        if result[nr, nc] != 0 and not visited[nr, nc]:
                            visited[nr, nc] = True
                            stack.append((nr, nc))

                biome_code = choose_biome()
                for ir, ic in component:
                    result[ir, ic] = biome_code

        return result

    def _rng_for_chunk(self, chunk_x: int, chunk_y: int) -> np.random.Generator:
        """Deterministic RNG keyed by builder seed and chunk coords."""
        mask = (1 << 64) - 1
        mix = (int(self.seed) * int(self._hash_mul_a)) & mask
        mix ^= (int(chunk_x) * int(self._hash_mul_b)) & mask
        mix ^= (int(chunk_y) * int(self._hash_mul_c)) & mask
        mix ^= 0xB10E123456789AB  # arbitrary tag for biome rng separation
        return np.random.default_rng(np.uint64(mix))

    @staticmethod
    def _orthogonal_neighbors(
        row: int, col: int, rows: int, cols: int
    ) -> List[Tuple[int, int]]:
        neighbors: List[Tuple[int, int]] = []
        if row > 0:
            neighbors.append((row - 1, col))
        if row + 1 < rows:
            neighbors.append((row + 1, col))
        if col > 0:
            neighbors.append((row, col - 1))
        if col + 1 < cols:
            neighbors.append((row, col + 1))
        return neighbors
