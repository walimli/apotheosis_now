"""Utilities for classifying chunk tiles."""
from __future__ import annotations

from collections import deque

import numpy as np


def classify_tiles(base_tiles: np.ndarray) -> np.ndarray:
    """Return a classification grid: 0 exterior void, 1 land, 2 interior void."""
    if base_tiles.ndim != 2:
        raise ValueError("base_tiles array must be two-dimensional")
    rows, cols = base_tiles.shape
    classification = np.full((rows, cols), -1, dtype=np.int8)
    land_mask = base_tiles != 0
    classification[land_mask] = 1

    visited = np.zeros((rows, cols), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(r: int, c: int) -> None:
        if 0 <= r < rows and 0 <= c < cols:
            if not visited[r, c] and not land_mask[r, c]:
                visited[r, c] = True
                queue.append((r, c))

    for c in range(cols):
        enqueue(0, c)
        enqueue(rows - 1, c)
    for r in range(rows):
        enqueue(r, 0)
        enqueue(r, cols - 1)

    while queue:
        r, c = queue.popleft()
        classification[r, c] = 0
        for nr, nc in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr, nc] and not land_mask[nr, nc]:
                visited[nr, nc] = True
                queue.append((nr, nc))

    classification[classification == -1] = 2
    return classification


__all__ = ["classify_tiles"]
