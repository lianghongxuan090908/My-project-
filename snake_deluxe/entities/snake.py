"""
Snake entity with turn buffer (anti-180) and growth mechanics.
"""

from snake_deluxe.core.consts import RIGHT, OPPOSITE


class Snake:
    """The snake. Body is a list of (x,y) tuples, head at index 0."""

    def __init__(self, cx: int, cy: int, length: int = 3):
        self.body: list[tuple[int, int]] = [(cx - i, cy) for i in range(length)]
        self.dir: tuple[int, int] = RIGHT
        self._buf: list[tuple[int, int]] = [RIGHT]
        self._grow = 0

    # ── Properties ──

    def head(self) -> tuple[int, int]:
        return self.body[0]

    def length(self) -> int:
        return len(self.body)

    def tail(self) -> tuple[int, int]:
        return self.body[-1]

    # ── Movement ──

    def turn(self, d: tuple[int, int]) -> None:
        """Queue a direction change. Max 3 buffered, no 180."""
        if len(self._buf) < 3:
            last = self._buf[-1] if self._buf else self.dir
            if d != OPPOSITE.get(last):
                self._buf.append(d)

    def set_dir(self, d: tuple[int, int]) -> None:
        """Force direction (AI use). Subject to anti-180 rule."""
        if d != OPPOSITE.get(self.dir):
            self._buf.clear()
            self._buf.append(d)

    def tick(self) -> None:
        """Move one step forward."""
        if self._buf:
            self.dir = self._buf.pop(0)
        dx, dy = self.dir
        hx, hy = self.head()
        self.body.insert(0, (hx + dx, hy + dy))
        if self._grow:
            self._grow -= 1
        else:
            self.body.pop()

    def grow(self, n: int = 1) -> None:
        self._grow += n

    # ── Collision ──

    def hit_self(self) -> bool:
        return self.head() in self.body[1:]

    def occupies(self, x: int, y: int) -> bool:
        return (x, y) in self.body

    def occupied_set(self) -> set[tuple[int, int]]:
        return set(self.body)

    # ── Serialization ──

    def to_dict(self) -> dict:
        return {"body": self.body, "dir": self.dir, "grow": self._grow}

    @classmethod
    def from_dict(cls, d: dict) -> "Snake":
        s = cls.__new__(cls)
        s.body = d["body"]
        s.dir = d["dir"]
        s._buf = [d["dir"]]
        s._grow = d.get("grow", 0)
        return s
