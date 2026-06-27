"""
Algorithm #2 — Tail‑chase with starvation detection and flood‑fill escape.

The fundamental insight (from the classic snake AI literature) is that
if the snake can always reach its own tail, it can survive indefinitely —
the tail "moves away" as the snake advances, creating a permanent safe
loop.  SurvivalAI implements this tail‑chase strategy, augmented with a
starvation detector and a flood‑fill escape for when the tail is blocked.

Strategy:
  1. Track consecutive non‑eating moves (starvation counter).
  2. If starved beyond STARVE_LIMIT and no path to food exists →
     keep moving if the current direction is safe; otherwise fall
     through to survival checks (avoid driving into walls).
  3. BFS to own tail (tail excluded from occupied — it moves away).
  4. If a tail‑path exists → follow it (safe chasing).
  5. Evaluate every legal move by flood‑fill reachable area →
     pick the direction that leaves the most space.
  6. Last resort: any safe direction (no reverse, no wall, no self).

Why STARVE_LIMIT = 20?
  A snake that cannot eat for 20+ consecutive moves is likely trapped
  in a local configuration where food is unreachable.  Rather than
  fruitlessly chasing food forever, we stop trying and switch to pure
  survival.  This prevents the "wandering forever" death spiral.
  20 ticks at 0.13s/tick ≈ 2.6 seconds of starvation — a reasonable
  threshold for the grid sizes used in Snake Deluxe (20×14 to 26×18).

Tail exclusion rationale:
  When BFS searches for a path to the tail, the tail cell itself is
  *not* marked as occupied.  This is correct because the tail moves
  away on every tick: the moment the snake advances, the previous
  tail cell becomes empty.  Excluding it allows BFS to find paths
  that "chase" the moving tail.
"""

from collections import deque
from typing import TYPE_CHECKING

from snake_deluxe.core.consts import UP, DOWN, LEFT, RIGHT, ALL_DIRS, OPPOSITE
from snake_deluxe.ai.base import BaseAI

if TYPE_CHECKING:
    from snake_deluxe.entities.snake import Snake
    from snake_deluxe.entities.food import Food


class SurvivalAI(BaseAI):
    """Tail‑chase AI with starvation escape.

    Safe fallback for any other AI — guarantees the snake stays alive
    as long as any safe move exists.
    """

    STARVE_LIMIT = 20

    def __init__(self) -> None:
        self._starve: int = 0

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "SurvivalAI"

    # ── Hooks ─────────────────────────────────────────────────────────────

    def on_eat(self) -> None:
        """Reset starvation counter after eating."""
        self._starve = 0

    def reset(self) -> None:
        """Full state reset."""
        self._starve = 0

    # ── BFS helpers (self‑contained) ──────────────────────────────────────

    @staticmethod
    def _bfs_path(
        start: tuple[int, int],
        goal: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        prefer_dir: tuple[int, int] | None = None,
    ) -> list[tuple[int, int]] | None:
        """Shortest path from *start* to *goal* avoiding *occupied*.

        Neighbour directions are sorted to prefer *prefer_dir* first —
        this keeps the snake moving straight and scatters fewer cells.

        Returns a list of direction tuples, or *None* if unreachable.
        """
        if start == goal:
            return []
        if start in occupied:
            return None

        queue: deque[tuple[tuple[int, int], list[tuple[int, int]]]] = deque()
        queue.append((start, []))
        visited: set[tuple[int, int]] = {start}

        # Sort directions: prefer_dir first, then others
        dir_order = sorted(
            ALL_DIRS,
            key=lambda d: 0 if d == prefer_dir else 1,
        )

        while queue:
            (x, y), path = queue.popleft()

            for dx, dy in dir_order:
                nx, ny = x + dx, y + dy

                # Wall check
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

    @staticmethod
    def _flood_count(
        start: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        limit: int = 200,
    ) -> int:
        """Count reachable empty cells from *start* (BFS flood‑fill).

        This is the classic "room counting" heuristic from competition
        snake AIs.  Unlike the tail‑reachability check (which is a
        binary pass/fail), flood fill returns a continuous measure of
        available space.  We use it in two places:

        1. In BFS_SnakeAI: after simulated eating, count the room
           around the new head.  If room > body length, the snake has
           enough space to manoeuvre even if the tail is far away.

        2. In SurvivalAI flood‑fill evaluation: among all legal moves,
           pick the one with the most room — stay in open areas and
           avoid corners.

        The *limit* parameter bounds the search so that flood fill
        on a fully open board (≈ 260 cells on Normal) returns quickly.
        200 is a safe cutoff: room > body length almost always
        resolves below this threshold.

        Returns *limit* if at least *limit* cells were found, otherwise
        the exact count of reachable cells.
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

    # ── Core decision ─────────────────────────────────────────────────────

    def think(
        self,
        snake: "Snake",
        food: "Food",
        W: int,
        H: int,
        obs: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Decide the safest direction to keep the snake alive."""
        # ── increment starvation counter ──
        self._starve += 1

        head: tuple[int, int] = snake.head()
        body_set: set[tuple[int, int]] = set(snake.body)
        occupied: set[tuple[int, int]] = body_set | set(obs)

        # ── Step 1: starved and no food reachable → accept death ──
        # When starved we give up on eating.  But we still avoid driving
        # straight into a wall: if the current direction is safe (not a
        # wall and not occupied) we keep moving; otherwise fall through
        # to the survival checks below.
        if self._starve >= self.STARVE_LIMIT:
            path_to_food = self._bfs_path(
                head, food.pos, occupied, W, H, snake.dir,
            )
            if path_to_food is None:
                sx, sy = head[0] + snake.dir[0], head[1] + snake.dir[1]
                if (
                    0 < sx < W - 1
                    and 0 < sy < H - 1
                    and (sx, sy) not in occupied
                ):
                    return snake.dir
                # else fall through — current direction would hit a wall

        # ── Step 2: BFS to own tail ──
        # Exclude the tail-tip — it moves away when the snake advances.
        tail_excluded: set[tuple[int, int]] = set(snake.body[:-1]) | set(obs)
        path_to_tail = self._bfs_path(
            head, snake.tail(), tail_excluded, W, H, snake.dir,
        )
        if path_to_tail is not None:
            return path_to_tail[0]

        # ── Step 3: flood‑fill evaluation for each legal move ──
        best_dir: tuple[int, int] | None = None
        best_room: int = -1

        for d in ALL_DIRS:
            # No reversal
            if d == OPPOSITE.get(snake.dir):
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            # Wall
            if nx <= 0 or nx >= W - 1 or ny <= 0 or ny >= H - 1:
                continue
            cell = (nx, ny)
            # Self / obstacle
            if cell in occupied:
                continue

            # How much space does this move leave us?
            next_occupied = occupied | {cell}
            room = self._flood_count(cell, next_occupied, W, H)
            if room > best_room:
                best_room = room
                best_dir = d

        if best_dir is not None:
            return best_dir

        # ── Step 4: last resort — any safe direction ──
        for d in ALL_DIRS:
            if d == OPPOSITE.get(snake.dir):
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if 0 < nx < W - 1 and 0 < ny < H - 1 and (nx, ny) not in occupied:
                return d

        # Nothing works — keep moving (we are dead anyway)
        return snake.dir
