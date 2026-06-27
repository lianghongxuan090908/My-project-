"""
Food entity with 5 types, weighted random spawning.
"""

import random
from snake_deluxe.core.consts import FOOD_TYPES, FOOD_WEIGHTS


class Food:
    """Food item on the board."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.pos: tuple[int, int] | None = None
        self.kind: int = 0
        self.spawn(set())

    @property
    def pts(self) -> int:
        return FOOD_TYPES[self.kind]["pts"]

    @property
    def ch(self) -> str:
        return FOOD_TYPES[self.kind]["ch"]

    @property
    def label(self) -> str:
        return FOOD_TYPES[self.kind]["label"]

    @property
    def color(self) -> str:
        return FOOD_TYPES[self.kind]["color"]

    def spawn(self, occ: set[tuple[int, int]], kind: int | None = None) -> bool:
        """Place food at a random free cell. Returns False if board full."""
        free = [
            (x, y)
            for x in range(1, self.w - 1)
            for y in range(1, self.h - 1)
            if (x, y) not in occ
        ]
        if not free:
            return False
        self.pos = random.choice(free)
        if kind is not None:
            self.kind = kind % len(FOOD_TYPES)
        else:
            r = random.random()
            cumulative = 0.0
            for i, w in enumerate(FOOD_WEIGHTS):
                cumulative += w
                if r < cumulative:
                    self.kind = i
                    break
            else:
                self.kind = 4
        return True
