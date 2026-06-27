"""
Algorithm #1 — BFS pathfinder with virtual snake simulation (chynl/snake).

Strategy:
  1. BFS from head → food avoiding walls, obstacles, and the snake's body.
  2. Simulate the snake eating the food (slide body along the path,
     no tail‑pop on the final step — snake grows by one).
  3. Check whether the *virtual* snake can reach its own tail after
     eating — if yes, the move is safe; eat.
  4. Flood‑fill from the virtual head: if the reachable area is larger
     than the snake's current length, there is enough room to survive.
  5. If eating is unsafe → delegate to SurvivalAI (tail‑chase / flee).

Why virtual‑snake simulation?
  Standard greedy BFS snake AIs chase food whenever a path exists,
  but this frequently leads to death by self‑wrapping.  The virtual
  simulation lets us peek into the future: we "fast‑forward" the
  snake along the BFS path to the food, then check whether the
  resulting body configuration is still survivable (tail reachable
  / enough free space).  This single heuristic eliminates the vast
  majority of suicidal food chases while being cheap to compute.

Direction ordering:
  Neighbour cells in BFS are sorted so that the snake's current
  direction appears first.  This encourages straight‑line movement
  which, over multiple ticks, scatters fewer body cells across the
  board — keeping more space available for future manoeuvres.

Reference: chynl/snake — BFS + virtual snake heuristic.
"""

from collections import deque
from typing import TYPE_CHECKING

from snake_deluxe.core.consts import UP, DOWN, LEFT, RIGHT, ALL_DIRS, OPPOSITE
from snake_deluxe.ai.base import BaseAI
from snake_deluxe.ai.survival import SurvivalAI

if TYPE_CHECKING:
    from snake_deluxe.entities.snake import Snake
    from snake_deluxe.entities.food import Food


class BFS_SnakeAI(BaseAI):
    """BFS-based snake AI with virtual-snake safety validation.

    This is the primary AI for normal gameplay.  It aggressively seeks
    food but only commits to eating when a post‑meal safety check passes.

    The safety pipeline works as follows:

        BFS path exists?
          │
          ├─ Yes ─► Simulate eating ─► Tail reachable? ──Yes──► Eat
          │                               │
          │                              No
          │                               │
          │                          Flood room > len? ──Yes──► Eat
          │                               │
          │                              No
          │                               │
          └─ No ──────────────────────► Delegate to SurvivalAI

    The two safety checks (tail‑reachability and flood‑fill room) are
    complementary: tail‑reachability is the stronger guarantee (if the
    snake can reach its own tail it can survive indefinitely), while
    flood‑fill room is a cheap heuristic that works well on sparse
    boards where the tail is far away.
    """

    def __init__(self) -> None:
        self._survival: SurvivalAI = SurvivalAI()

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "BFS_SnakeAI"

    # ── Hooks ─────────────────────────────────────────────────────────────

    def on_eat(self) -> None:
        """Delegate per‑eating state reset to the survival fallback."""
        self._survival.on_eat()

    def reset(self) -> None:
        """Full reset for a new game."""
        self._survival.reset()

    # ── BFS pathfinding ───────────────────────────────────────────────────

    @staticmethod
    def _bfs_path(
        start: tuple[int, int],
        goal: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        prefer_dir: tuple[int, int] | None = None,
    ) -> list[tuple[int, int]] | None:
        """BFS shortest path from *start* to *goal* avoiding *occupied*.

        Unlike A* which needs a heuristic, BFS guarantees the shortest
        path in an unweighted 4‑connected grid.  This is optimal for
        snake because every move costs exactly 1 tick.

        Neighbour directions are sorted to put *prefer_dir* first —
        the snake moves straight when possible, which scatters fewer
        cells and keeps the board compact.  When multiple paths of
        equal length exist, the one that continues straight is
        visually more natural and less likely to trap the snake.

        Complexity: O(V + E) where V = W×H (playable cells) and
        E ≤ 4V (4‑connected grid).  For the largest board in Snake
        Deluxe (28×20 = 560 cells) this completes in < 1 ms.

        Returns a list of direction tuples (e.g. [(0,-1), (1,0)]),
        or *None* if the goal is unreachable.
        """
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

                # Wall bounds (walls are at 0 / W-1 / 0 / H-1)
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

    # ── Flood fill ────────────────────────────────────────────────────────

    @staticmethod
    def _flood_count(
        start: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        limit: int = 200,
    ) -> int:
        """Count reachable empty cells from *start* (bounded BFS flood).

        Used as a cheap "is there enough room?" heuristic.
        Returns early as soon as *limit* cells are reached.
        """
        if start in occupied:
            return 0

        visited: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])
        count = 0

        while queue and count < limit:
            x, y = queue.popleft()
            count += 1

            for dx, dy in ALL_DIRS:
                nx, ny = x + dx, y + dy
                cell = (nx, ny)
                if (
                    0 < nx < W - 1
                    and 0 < ny < H - 1
                    and cell not in visited
                    and cell not in occupied
                ):
                    visited.add(cell)
                    queue.append(cell)

        return count

    # ── Virtual snake simulation ──────────────────────────────────────────

    @staticmethod
    def _sim_virtual_snake(
        snake_body: list[tuple[int, int]],
        path_to_food: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Simulate the snake eating food by walking *path_to_food*.

        The head slides along the path; on every step we insert a new
        head.  On the **last** step we *do not* pop the tail — this
        simulates the snake growing by one cell (eating).

        Args:
            snake_body:  Current body list (head at index 0).
            path_to_food:  List of direction tuples from _bfs_path.

        Returns:
            The body list *after* eating the food.
        """
        sim_body = list(snake_body)

        for step, d in enumerate(path_to_food):
            hx, hy = sim_body[0]
            new_head = (hx + d[0], hy + d[1])
            sim_body.insert(0, new_head)

            # Eat on the last step → no tail pop
            if step < len(path_to_food) - 1:
                sim_body.pop()

        return sim_body

    # ── Safety checks ─────────────────────────────────────────────────────

    def _can_reach_tail(
        self,
        simulated_body: list[tuple[int, int]],
        obs: list[tuple[int, int]],
        W: int,
        H: int,
    ) -> bool:
        """Check whether the *simulated* head can BFS to its own tail.

        The tail cell is **excluded** from the occupied set because it
        moves away when the snake advances — this is the classic
        "can it reach its tail?" survival check.
        """
        vhead = simulated_body[0]
        vtail = simulated_body[-1]

        # Mark all body except the very tip of the tail as occupied.
        occupied: set[tuple[int, int]] = set(simulated_body[:-1]) | set(obs)

        path = self._bfs_path(vhead, vtail, occupied, W, H)
        return path is not None

    # ── Core decision ─────────────────────────────────────────────────────

    def think(
        self,
        snake: "Snake",
        food: "Food",
        W: int,
        H: int,
        obs: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Decide direction: prefer food but only when safe.

        Decision pipeline:
          1. BFS head → food.
          2. If path exists, simulate eating.
          3. Tail‑reachable after eating?  → eat (return path[0]).
          4. Flood‑fill room > snake length?  → eat.
          5. Otherwise → SurvivalAI (tail‑chase / flee).
        """
        head = snake.head()
        occupied: set[tuple[int, int]] = set(snake.body) | set(obs)

        # ── 1. BFS to food ────────────────────────────────────────────────
        path_to_food = self._bfs_path(
            head, food.pos, occupied, W, H, snake.dir,
        )

        if path_to_food is not None:
            # ── 2. Simulate eating ──
            sim_body = self._sim_virtual_snake(snake.body, path_to_food)

            # ── 3. Tail‑reachability test ──
            if self._can_reach_tail(sim_body, obs, W, H):
                return path_to_food[0]

            # ── 4. Flood‑fill room test ──
            sim_head = sim_body[0]
            sim_occupied: set[tuple[int, int]] = set(sim_body) | set(obs)
            room = self._flood_count(sim_head, sim_occupied, W, H)
            if room > len(snake.body):
                return path_to_food[0]

        # ── 5. Unsafe → delegate to survival mode ─────────────────────────
        return self._survival.think(snake, food, W, H, obs)
