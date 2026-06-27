"""
Abstract base class for snake AI implementations.

All AI strategies inherit from BaseAI and implement the think() method
which returns a direction (UP / DOWN / LEFT / RIGHT) each tick.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snake_deluxe.entities.snake import Snake
    from snake_deluxe.entities.food import Food


class BaseAI(ABC):
    """Abstract base class for all snake AI decision-makers.

    Subclasses must define:
      - name   (property)
      - think  (method)

    Subclasses should override:
      - on_eat()  — called when food is consumed (reset per-eating state)
      - reset()   — called to fully reset internal state
    """

    # ── Required ──────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this AI strategy."""
        ...

    @abstractmethod
    def think(
        self,
        snake: "Snake",
        food: "Food",
        W: int,
        H: int,
        obs: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Decide the next movement direction.

        Args:
            snake: The Snake entity (owns body, dir, head, tail, …).
            food:  The Food entity (pos, pts, …).
            W:     Board width  in cells (includes wall columns).
            H:     Board height in cells (includes wall rows).
            obs:   List of obstacle positions (static walls / hazards).

        Returns:
            One of ( 0,-1) UP,
                    ( 0, 1) DOWN,
                    (-1, 0) LEFT,
                    ( 1, 0) RIGHT.
        """
        ...

    # ── Life‑cycle hooks ──────────────────────────────────────────────────

    def on_eat(self) -> None:
        """Notification that the AI's snake just ate food.

        Override to reset per‑eating counters (e.g. starvation timer).
        """
        pass

    def reset(self) -> None:
        """Full reset of internal state for a new game.

        Override to clear caches, rebuild cycles, etc.
        """
        pass
