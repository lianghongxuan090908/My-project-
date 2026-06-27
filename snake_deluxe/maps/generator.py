"""
Map generation: maze algorithms, obstacle placement, and built-in presets.
"""

import random
from typing import Optional

from snake_deluxe.core.consts import DIFFICULTIES

# ── type alias ──
Cell = tuple[int, int]
Grid = list[list[bool]]  # True = wall, False = passage

# ===================================================================
# MazeGenerator
# ===================================================================

class MazeGenerator:
    """Generates mazes using classic algorithms.

    Usage:
        maze = MazeGenerator()
        walls = maze.generate(20, 16, algorithm="recursive_backtracker")
    """

    def __init__(self) -> None:
        self._width: int = 0
        self._height: int = 0
        self._grid: Grid = []

    # ── public API ──

    def generate(
        self,
        w: int,
        h: int,
        algorithm: str = "recursive_backtracker",
    ) -> list[Cell]:
        """Generate a maze and return wall cell coordinates.

        Supported algorithms:
            - "recursive_backtracker" (DFS)
            - "prims" (randomized Prim's)
        """
        # Dimensions must be odd so the maze grid aligns properly
        self._width = w if w % 2 == 1 else w + 1
        self._height = h if h % 2 == 1 else h + 1

        # Initialise: all cells are walls
        self._grid = [
            [True] * self._width for _ in range(self._height)
        ]

        if algorithm == "prims":
            self._prims()
        else:
            self._recursive_backtracker()

        return self._extract_walls()

    # ── algorithm: recursive backtracker (DFS) ──

    def _recursive_backtracker(self) -> None:
        """Depth-first search maze generation."""
        # Start at cell (1, 1)
        start_x, start_y = 1, 1
        self._grid[start_y][start_x] = False

        stack: list[Cell] = [(start_x, start_y)]
        visited: set[Cell] = {(start_x, start_y)}

        while stack:
            cx, cy = stack[-1]
            neighbours = self._unvisited_neighbours(cx, cy, visited)

            if not neighbours:
                stack.pop()
                continue

            nx, ny = random.choice(neighbours)
            # Knock down the wall between current and chosen cell
            wx = cx + (nx - cx) // 2
            wy = cy + (ny - cy) // 2
            self._grid[wy][wx] = False
            self._grid[ny][nx] = False
            visited.add((nx, ny))
            stack.append((nx, ny))

    def _unvisited_neighbours(
        self, x: int, y: int, visited: set[Cell]
    ) -> list[Cell]:
        """Return unvisited neighbours 2 cells away in cardinal directions."""
        neighbours: list[Cell] = []
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < self._width - 1 and 0 < ny < self._height - 1:
                if (nx, ny) not in visited:
                    neighbours.append((nx, ny))
        return neighbours

    # ── algorithm: randomized Prim's ──

    def _prims(self) -> None:
        """Randomized Prim's algorithm for maze generation."""
        # Start at (1, 1)
        self._grid[1][1] = False

        walls: list[Cell] = self._cell_walls(1, 1)
        in_maze: set[Cell] = {(1, 1)}

        while walls:
            idx = random.randrange(0, len(walls))
            wx, wy = walls.pop(idx)

            # Find which side of the wall leads to a cell already in the maze
            passages: list[Cell] = []
            for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                cx, cy = wx + dx, wy + dy
                if (cx, cy) in in_maze:
                    passages.append((cx, cy))

            if len(passages) == 1:
                # The other side should be a wall not yet in the maze
                px, py = passages[0]
                nx = wx + (wx - px)
                ny = wy + (wy - py)
                if 0 < nx < self._width - 1 and 0 < ny < self._height - 1:
                    if (nx, ny) not in in_maze:
                        self._grid[wy][wx] = False
                        self._grid[ny][nx] = False
                        in_maze.add((nx, ny))
                        in_maze.add((wx, wy))
                        walls.extend(self._cell_walls(nx, ny))

            # Remove any walls that are now in-maze
            walls = [c for c in walls if c not in in_maze]

    def _cell_walls(self, x: int, y: int) -> list[Cell]:
        """Return wall coordinates adjacent to cell (x, y)."""
        result: list[Cell] = []
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            wx, wy = x + dx, y + dy
            if 0 < wx < self._width - 1 and 0 < wy < self._height - 1:
                if self._grid[wy][wx]:
                    result.append((wx, wy))
        return result

    # ── helper ──

    def _extract_walls(self) -> list[Cell]:
        """Convert the boolean grid to a list of wall coordinates."""
        walls: list[Cell] = []
        for y in range(self._height):
            for x in range(self._width):
                if self._grid[y][x]:
                    walls.append((x, y))
        return walls


# ===================================================================
# Free functions
# ===================================================================

def add_obstacles(
    w: int, h: int,
    count: int,
    occupied: set[Cell],
) -> list[Cell]:
    """Place *count* obstacles on the grid avoiding occupied cells.

    Obstacles are placed at least 1 cell away from occupied positions
    to give the player room to manoeuvre.
    """
    obstacles: list[Cell] = []
    candidates: list[Cell] = [
        (x, y)
        for y in range(1, h - 1)
        for x in range(1, w - 1)
        if (x, y) not in occupied
    ]
    random.shuffle(candidates)

    for cx, cy in candidates:
        if len(obstacles) >= count:
            break
        # Ensure at least 2-cell clearance from any existing obstacle
        too_close = False
        for ox, oy in obstacles:
            if abs(cx - ox) + abs(cy - oy) < 2:
                too_close = True
                break
        if not too_close:
            obstacles.append((cx, cy))

    return obstacles


def generate_borders(w: int, h: int) -> set[Cell]:
    """Return the set of border wall cells for a w×h grid."""
    borders: set[Cell] = set()
    for x in range(w):
        borders.add((x, 0))
        borders.add((x, h - 1))
    for y in range(1, h - 1):
        borders.add((0, y))
        borders.add((w - 1, y))
    return borders


# ===================================================================
# Built-in map presets
# ===================================================================

def preset_cross(w: int, h: int) -> list[Cell]:
    """A cross pattern dividing the playfield into four quadrants."""
    walls: list[Cell] = []
    mid_x, mid_y = w // 2, h // 2
    for y in range(1, h - 1):
        walls.append((mid_x, y))
    for x in range(1, w - 1):
        walls.append((x, mid_y))
    # leave a gap in the centre
    for gx in range(mid_x - 1, mid_x + 2):
        for gy in range(mid_y - 1, mid_y + 2):
            if 0 < gx < w - 1 and 0 < gy < h - 1:
                try:
                    walls.remove((gx, gy))
                except ValueError:
                    pass
    return walls


def preset_rings(w: int, h: int) -> list[Cell]:
    """Concentric ring pattern."""
    walls: list[Cell] = []
    for r in range(2, min(w, h) // 2, 3):
        x0, y0 = r, r
        x1, y1 = w - r - 1, h - r - 1
        if x0 >= x1 or y0 >= y1:
            break
        for x in range(x0, x1 + 1):
            walls.append((x, y0))
            walls.append((x, y1))
        for y in range(y0 + 1, y1):
            walls.append((x0, y))
            walls.append((x1, y))
    return walls


def preset_checkerboard(w: int, h: int) -> list[Cell]:
    """Checkerboard pattern: every other cell is blocked."""
    walls: list[Cell] = []
    for y in range(1, h - 1, 2):
        for x in range(1, w - 1, 2):
            walls.append((x, y))
    return walls
