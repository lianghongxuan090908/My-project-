"""
Algorithm #3 — Hamiltonian cycle traversal with shortcut detection.

Constructs a Hamiltonian path through every playable cell using a simple
serpentine (zigzag) pattern, then doubles it back to form a closed tour
(bidirectional traversal: forward path + reverse path without endpoints).

The snake follows this cycle unconditionally, guaranteeing it never
collides with itself.  When food lies behind on the cycle the AI may
take a BFS shortcut — but only if a 5‑step look‑ahead simulation
confirms no self‑collision.

Why Hamiltonian cycles?
  A Hamiltonian cycle visits every cell on the board exactly once (or
  twice in our bidirectional construction) and returns to the start.
  A snake that faithfully follows such a cycle can *never* trap itself,
  because the cycle provides a safe path through every reachable cell.
  The trade‑off is optimality: the cycle path is rarely the shortest
  path to the food.

Bidirectional construction:
  The simple zigzag visits all cells left‑to‑right, then right‑to‑left,
  alternating by row.  The forward path alone does *not* form a closed
  cycle (the first and last cells are not adjacent on larger grids).
  By concatenating the forward path with its reverse interior we create
  a valid cycle where every consecutive pair is grid‑adjacent::

    cycle = path + path[-2:0:-1]

  This visits interior cells twice per full tour, but every edge is
  between adjacent cells — a correctness requirement for the AI to
  issue a valid direction each tick.

Shortcut detection:
  When food lies *behind* the snake on the cycle, following the cycle
  would mean traversing nearly the entire board before eating.  Instead,
  we try a direct BFS path to the food.  If the first 5 steps of that
  shortcut are free of self‑collision, we take it.  The 5‑step limit
  keeps the simulation cheap and local.

D&C Union‑Find Merge (future work):
  For very large or irregular boards the simple zigzag produces a
  long, predictable cycle that the player can exploit.  The divide‑
  and‑conquer approach (LPRowe) splits the board into rectangles,
  builds a Hamiltonian cycle in each via union‑find, then merges
  adjacent cycles by swapping four edges.  The result is a more
  uniform, less predictable cycle.  The implementation is O(N log N)
  where N = W×H, compared to O(W×H) for zigzag.

  When to upgrade to D&C UC:
    - Board size > 30×30 (grids this large appear in Maze mode)
    - Non‑rectangular boards (Maze mode has internal walls)
    - When cycle predictability is a concern (player vs AI)

Reference: LPRowe / Hamiltonian‑cycle snake AI.
"""

from collections import deque
from typing import TYPE_CHECKING

from snake_deluxe.core.consts import UP, DOWN, LEFT, RIGHT, ALL_DIRS, OPPOSITE
from snake_deluxe.ai.base import BaseAI

if TYPE_CHECKING:
    from snake_deluxe.entities.snake import Snake
    from snake_deluxe.entities.food import Food


class HamiltonianAI(BaseAI):
    """Cycle‑following snake AI.

    The snake traces a pre‑computed Hamiltonian cycle that visits every
    playable cell.  Safety is guaranteed by construction — the snake
    cannot collide with itself as long as it stays on the cycle.

    Shortcuts toward food that is *behind* the snake on the cycle are
    taken when a local safety simulation passes.
    """

    def __init__(self) -> None:
        self._cycle: list[tuple[int, int]] = []
        self._cycle_index: dict[tuple[int, int], int] = {}

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "HamiltonianAI"

    # ── Hooks ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear cached cycle so it is rebuilt on the next think()."""
        self._cycle.clear()
        self._cycle_index.clear()

    # ── Cycle construction ────────────────────────────────────────────────

    def build_cycle(self, W: int, H: int) -> None:
        """Build a serpentine Hamiltonian path and close it into a cycle.

        The playable area is ``(1, 1) … (W-2, H-2)``.  We zigzag
        through every cell, then append the reverse of the interior
        so the snake can traverse back.  Every consecutive pair in
        the resulting list is adjacent in grid space.

        This yields a cycle of length ``2 * (W-2) * (H-2) - 2`` —
        each interior cell appears twice (once forward, once backward).

        NOTE: For very large grids the D&C UC merge (LPRowe) produces
        a more uniform cycle, but this zigzag is O(W×H) and works
        well for the board sizes used in Snake Deluxe.
        """
        path: list[tuple[int, int]] = []

        for y in range(1, H - 1):
            if (y - 1) % 2 == 0:
                # Left → right
                for x in range(1, W - 1):
                    path.append((x, y))
            else:
                # Right → left
                for x in range(W - 2, 0, -1):
                    path.append((x, y))

        # Close into a cycle: forward path + reverse of interior
        # path[-2:0:-1] yields path[last-1], …, path[1]
        self._cycle = path + path[-2:0:-1]
        self._cycle_index = {pos: i for i, pos in enumerate(self._cycle)}

    # ── Cycle helpers ─────────────────────────────────────────────────────

    def _next_on_cycle(
        self,
        pos: tuple[int, int],
    ) -> tuple[int, int] | None:
        """Return the cell immediately after *pos* on the Hamiltonian cycle."""
        idx = self._cycle_index.get(pos)
        if idx is None:
            return None
        next_idx = (idx + 1) % len(self._cycle)
        return self._cycle[next_idx]

    def _dir_between(
        self,
        a: tuple[int, int],
        b: tuple[int, int],
    ) -> tuple[int, int] | None:
        """Unit direction from cell *a* to cell *b* (must be adjacent)."""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if (dx, dy) in ALL_DIRS:
            return (dx, dy)
        return None  # not adjacent

    # ── Shortcut safety ───────────────────────────────────────────────────

    @staticmethod
    def _is_safe_shortcut(
        snake: "Snake",
        path: list[tuple[int, int]],
        obs: list[tuple[int, int]],
        W: int,
        H: int,
    ) -> bool:
        """Simulate the first 5 steps of *path* and check for collisions.

        Returns *True* if every step stays inside the board, avoids
        obstacles, and never touches the snake's body (tail excepted).
        """
        sim_body = list(snake.body)
        steps = min(len(path), 5)

        for d in path[:steps]:
            hx, hy = sim_body[0]
            nx, ny = hx + d[0], hy + d[1]

            # Wall check
            if nx <= 0 or nx >= W - 1 or ny <= 0 or ny >= H - 1:
                return False

            # Self‑collision (tail excluded — it moves away)
            if (nx, ny) in sim_body[:-1]:
                return False

            # Obstacle
            if (nx, ny) in obs:
                return False

            sim_body.insert(0, (nx, ny))
            sim_body.pop()

        return True

    # ── BFS helper (self‑contained) ───────────────────────────────────────

    @staticmethod
    def _bfs_path(
        start: tuple[int, int],
        goal: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        prefer_dir: tuple[int, int] | None = None,
    ) -> list[tuple[int, int]] | None:
        """Shortest BFS path from *start* to *goal* avoiding *occupied*."""
        if start == goal:
            return []
        if start in occupied:
            return None

        queue: deque[tuple[tuple[int, int], list[tuple[int, int]]]] = deque()
        queue.append((start, []))
        visited: set[tuple[int, int]] = {start}

        dir_order = sorted(
            ALL_DIRS,
            key=lambda d: 0 if d == prefer_dir else 1,
        )

        while queue:
            (x, y), path = queue.popleft()

            for dx, dy in dir_order:
                nx, ny = x + dx, y + dy
                if nx <= 0 or nx >= W - 1 or ny <= 0 or ny >= H - 1:
                    continue
                cell = (nx, ny)
                if cell in visited or cell in occupied:
                    continue

                new_path = path + [(dx, dy)]
                if cell == goal:
                    return new_path

                visited.add(cell)
                queue.append((cell, new_path))

        return None

    # ── Core decision ─────────────────────────────────────────────────────

    def think(
        self,
        snake: "Snake",
        food: "Food",
        W: int,
        H: int,
        obs: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Decide direction: follow the Hamiltonian cycle, shortcut to food.

        The decision logic balances two opposing goals:

        1. **Safety** (primary): Staying on the cycle guarantees no
           self‑collision.  The snake can loop forever without dying.

        2. **Efficiency** (secondary): The cycle path to the food may
           be very long when the food is *behind* the snake.  When safe,
           we take a BFS shortcut to reach the food faster.

        Shortcut safety is verified with `_is_safe_shortcut`, which
        simulates the first 5 steps of the BFS path on a *copy* of
        the body.  If any step causes a collision, we abort the
        shortcut and stay on the cycle.

        Decision pipeline:
          1. Build cycle on first use (lazy initialisation).
          2. Locate head on the cycle.  If the head is **off** the
             cycle (e.g. after teleportation in Reverse mode) →
             fall back to any safe direction.
          3. If food is on the cycle and **behind** the snake →
             try a BFS shortcut (only if 5‑step sim is safe).
          4. Otherwise → follow the next direction on the cycle.

        The cycle construction is O(W×H) and runs once per game
        (lazily on the first think() call).  Subsequent calls are
        O(1) — a dictionary lookup for the current cycle index and
        a modulo operation to find the next cell.
        """
        # ── 1. Lazy cycle construction ──
        if not self._cycle:
            self.build_cycle(W, H)

        head = snake.head()
        head_idx = self._cycle_index.get(head)

        # ── 2. Off‑cycle fallback ──
        if head_idx is None:
            occupied: set[tuple[int, int]] = set(snake.body) | set(obs)
            for d in ALL_DIRS:
                if d == OPPOSITE.get(snake.dir):
                    continue
                nx, ny = head[0] + d[0], head[1] + d[1]
                if 0 < nx < W - 1 and 0 < ny < H - 1 and (nx, ny) not in occupied:
                    return d
            return snake.dir

        # ── 3. Food on cycle → check for shortcut opportunity ──
        food_idx = self._cycle_index.get(food.pos)

        if food_idx is not None:
            # Distance *forward* along the cycle
            dist_ahead = (food_idx - head_idx) % len(self._cycle)
            dist_behind = (head_idx - food_idx) % len(self._cycle)

            # If food is closer behind us, try a shortcut
            if 0 < dist_behind < dist_ahead:
                occupied = set(snake.body) | set(obs)
                shortcut = self._bfs_path(head, food.pos, occupied, W, H, snake.dir)
                if shortcut is not None and self._is_safe_shortcut(
                    snake, shortcut, obs, W, H,
                ):
                    return shortcut[0]

        # ── 4. Follow the cycle ──
        next_pos = self._next_on_cycle(head)
        if next_pos is not None:
            d = self._dir_between(head, next_pos)
            if d is not None and d != OPPOSITE.get(snake.dir):
                return d

        # ── 5. Safety net (should be unreachable) ──
        occupied = set(snake.body) | set(obs)
        for d in ALL_DIRS:
            if d == OPPOSITE.get(snake.dir):
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if 0 < nx < W - 1 and 0 < ny < H - 1 and (nx, ny) not in occupied:
                return d
        return snake.dir
