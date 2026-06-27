"""
AI Tournament — head‑to‑head and round‑robin comparison (bonus module).

Each AI plays an isolated game (same board size, same obstacle set),
and scores are accumulated across matches.  The tournament module
provides a simple benchmark to compare AI strategies.

Scoring:
  Each AI gets one game per match.  The game runs for *max_ticks*
  steps or until the snake dies (wall / self‑collision).  The score
  is the total point value of food eaten (different food types have
  different point values — see snake_deluxe.core.consts.FOOD_TYPES).

Match types:
  - ``run_match(ai1, ai2)`` — two AIs play independent games on the
    same board; returns ``(score_ai1, score_ai2)``.
  - ``run_tournament(ais, rounds)`` — round‑robin: every pair plays
    *rounds* matches.  Returns a sorted leaderboard.

Usage::

    from snake_deluxe.ai.bfs import BFS_SnakeAI
    from snake_deluxe.ai.hamiltonian import HamiltonianAI
    from snake_deluxe.ai.tournament import AITournament

    bfs = BFS_SnakeAI()
    ham = HamiltonianAI()
    s1, s2 = AITournament.run_match(bfs, ham, W=22, H=16)
    ranking = AITournament.run_tournament([bfs, ham], rounds=3)

Implementation note:
  Games are simulated entirely inside this module using the public
  API of Snake, Food, and the AI subclasses.  No game‑engine
  dependency is required, which makes the tournament testable in
  isolation and usable as a training harness for future ML‑based
  AIs.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snake_deluxe.ai.base import BaseAI


class AITournament:
    """Collection of static methods for running AI vs AI comparisons."""

    @staticmethod
    def _play(
        ai: "BaseAI",
        W: int,
        H: int,
        obs: list[tuple[int, int]],
        max_ticks: int,
    ) -> int:
        """Run one full game for *ai* and return the score.

        The snake starts at the centre, and the game runs for
        *max_ticks* steps or until the snake dies.
        """
        # Late imports to avoid circular dependencies at module level
        from snake_deluxe.entities.snake import Snake
        from snake_deluxe.entities.food import Food

        cx, cy = W // 2, H // 2
        snake = Snake(cx, cy, 3)
        food = Food(W, H)
        score = 0
        ai.reset()

        for _ in range(max_ticks):
            d = ai.think(snake, food, W, H, list(obs))
            snake.set_dir(d)
            snake.tick()

            # Death by self‑collision
            if snake.hit_self():
                break
            # Death by wall
            hx, hy = snake.head()
            if hx <= 0 or hx >= W - 1 or hy <= 0 or hy >= H - 1:
                break

            # Food consumed?
            if snake.head() == food.pos:
                snake.grow(1)
                ai.on_eat()
                score += food.pts
                if not food.spawn(snake.occupied_set()):
                    break  # board full — no more food

        return score

    # ── Public API ────────────────────────────────────────────────────────

    @staticmethod
    def run_match(
        ai1: "BaseAI",
        ai2: "BaseAI",
        W: int = 22,
        H: int = 16,
        obs: list[tuple[int, int]] | None = None,
        max_ticks: int = 1000,
    ) -> tuple[int, int]:
        """Let two AIs each play one game and compare scores.

        Returns:
            ``(score_ai1, score_ai2)``
        """
        obs = obs or []
        s1 = AITournament._play(ai1, W, H, obs, max_ticks)
        s2 = AITournament._play(ai2, W, H, obs, max_ticks)
        return (s1, s2)

    @staticmethod
    def run_tournament(
        ais: list["BaseAI"],
        rounds: int = 1,
        W: int = 22,
        H: int = 16,
        obs: list[tuple[int, int]] | None = None,
    ) -> list[tuple[str, int]]:
        """Round‑robin tournament: every AI plays every other AI.

        Each pair plays *rounds* times (alternating who goes first is
        irrelevant because games are independent).  Returns a sorted
        leaderboard::

            [("BFS_SnakeAI", 420), ("HamiltonianAI", 380), ("SurvivalAI", 150)]
        """
        obs = obs or []
        scores: dict[str, int] = {ai.name: 0 for ai in ais}

        for _ in range(rounds):
            for i in range(len(ais)):
                for j in range(i + 1, len(ais)):
                    s1, s2 = AITournament.run_match(ais[i], ais[j], W, H, obs)
                    scores[ais[i].name] += s1
                    scores[ais[j].name] += s2

        return sorted(scores.items(), key=lambda x: -x[1])
