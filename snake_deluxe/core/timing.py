"""
Timing / FPS management for the game loop.
"""

import time


class GameTimer:
    """Manages game speed and frame timing."""

    def __init__(self, speed: float = 0.13):
        self._speed = speed
        self._last = time.time()
        self._last_move = time.time()
        self._play_time = 0.0

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, val: float) -> None:
        self._speed = max(0.035, val)

    @property
    def play_time(self) -> float:
        return self._play_time

    def reset(self, speed: float = 0.13) -> None:
        self._speed = speed
        now = time.time()
        self._last = now
        self._last_move = now
        self._play_time = 0.0

    def should_move(self) -> bool:
        """Return True when it's time for the next game tick."""
        now = time.time()
        self._play_time += now - self._last
        self._last = now
        dt = now - self._last_move
        if dt >= self._speed:
            self._last_move = now
            return True
        return False

    def frame_delay(self) -> float:
        """Sleep time for ~60fps rendering."""
        return 0.01
