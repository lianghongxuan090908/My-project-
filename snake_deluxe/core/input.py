"""
Keyboard input handler using msvcrt (Windows).
"""

import msvcrt
from snake_deluxe.core.consts import ARROW_MAP, WASD_MAP, ALL_DIRS, OPPOSITE


# Key action constants
ACTION_UP    = "up"
ACTION_DOWN  = "down"
ACTION_LEFT  = "left"
ACTION_RIGHT = "right"
ACTION_PAUSE   = "pause"
ACTION_RESTART = "restart"
ACTION_QUIT    = "quit"
ACTION_ENTER   = "enter"
ACTION_MENU    = "menu"
ACTION_STATS   = "stats"
ACTION_LEADER  = "leaderboard"
ACTION_THEME   = "theme"
ACTION_NONE    = None


class InputHandler:
    """Reads keyboard input and returns action tokens + direction changes."""

    def __init__(self):
        self._dir_pressed: tuple[int, int] | None = None
        self._action: str | None = None

    def poll(self) -> None:
        """Read all pending keypresses. Call once per frame."""
        self._dir_pressed = None
        self._action = None
        while msvcrt.kbhit():
            k = msvcrt.getch()
            if k == b"\xe0":
                k = msvcrt.getch()
                if k in ARROW_MAP:
                    self._dir_pressed = ARROW_MAP[k]
                continue
            if k == b" " or k in (b"p", b"P"):
                self._action = ACTION_PAUSE; return
            if k in (b"r", b"R"):
                self._action = ACTION_RESTART; return
            if k in (b"q", b"Q"):
                self._action = ACTION_QUIT; return
            if k in (b"\r", b"\n"):
                self._action = ACTION_ENTER; return
            if k == b"m" or k == b"M":
                self._action = ACTION_MENU; return
            if k.lower() in WASD_MAP:
                self._dir_pressed = WASD_MAP[k.lower()]; return
            # Menu-only keys (handled by caller when state permits)

    @property
    def dir_pressed(self) -> tuple[int, int] | None:
        return self._dir_pressed

    @property
    def action(self) -> str | None:
        return self._action

    def get_menu_key(self) -> str | None:
        """Read one key for menu navigation."""
        while msvcrt.kbhit():
            k = msvcrt.getch()
            if k == b"\xe0":
                k = msvcrt.getch()
                if k == b"H": return ACTION_UP
                if k == b"P": return ACTION_DOWN
                if k == b"K": return ACTION_LEFT
                if k == b"M": return ACTION_RIGHT
                continue
            if k in (b"1", b"2", b"3"):
                return k.decode()
            if k in (b"\r", b"\n"): return ACTION_ENTER
            if k == b" ": return ACTION_ENTER
            if k in (b"q", b"Q"): return ACTION_QUIT
            # Action keys FIRST (before generic a-h catch-all)
            if k == b"s" or k == b"S": return ACTION_STATS
            if k == b"h" or k == b"H": return ACTION_LEADER
            if k == b"t" or k == b"T": return ACTION_THEME
            if k == b"m" or k == b"M": return ACTION_MENU
            if k in (b"p", b"P"): return "p"
            if k in (b"r", b"R"): return ACTION_RESTART
            if k in (b"a", b"b", b"c", b"d", b"e", b"f", b"g", b"h"):
                return k.decode()
        return None
