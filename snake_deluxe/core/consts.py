"""
Shared constants for the entire game.
"""

import os, sys

# ── ANSI escapes ──
CSI = "\033["
HOME = CSI + "H"
CLS = CSI + "2J" + HOME
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"
BOLD = CSI + "1m"
RESET = CSI + "0m"
REVERSE = CSI + "7m"

# 16 standard colors
class FG:
    BLACK   = CSI + "30m"
    RED     = CSI + "31m"
    GREEN   = CSI + "32m"
    YELLOW  = CSI + "33m"
    BLUE    = CSI + "34m"
    MAGENTA = CSI + "35m"
    CYAN    = CSI + "36m"
    WHITE   = CSI + "37m"
    BRED    = CSI + "91m"
    BGRN    = CSI + "92m"
    BYEL    = CSI + "93m"
    BBLU    = CSI + "94m"
    BMAG    = CSI + "95m"
    BCYN    = CSI + "96m"

# ── Directions ──
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIR_NAMES: dict[tuple[int,int], str] = {
    UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"
}
OPPOSITE: dict[tuple[int,int], tuple[int,int]] = {
    UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT
}
ALL_DIRS = [UP, DOWN, LEFT, RIGHT]

# Arrow key scancodes (\xe0 prefix)
ARROW_MAP: dict[bytes, tuple[int,int]] = {
    b"H": UP, b"P": DOWN, b"K": LEFT, b"M": RIGHT
}
WASD_MAP: dict[bytes, tuple[int,int]] = {
    b"w": UP, b"s": DOWN, b"a": LEFT, b"d": RIGHT
}

# ── Difficulty presets ──
DIFFICULTIES: dict[str, dict] = {
    "简单":  {"w": 18, "h": 14, "speed": 0.18, "obs": 0},
    "普通": {"w": 22, "h": 16, "speed": 0.13, "obs": 3},
    "困难":  {"w": 28, "h": 20, "speed": 0.09, "obs": 6},
}

# ── Food types ──
FOOD_TYPES: list[dict] = [
    {"ch": "\u2605", "pts": 10, "color": FG.RED,    "label": "基础"},
    {"ch": "\u25CF", "pts": 15, "color": FG.BLUE,   "label": "蓝莓"},
    {"ch": "\u25C6", "pts": 20, "color": FG.YELLOW, "label": "黄金"},
    {"ch": "\u2663", "pts": 25, "color": FG.GREEN,  "label": "翡翠"},
    {"ch": "\u2666", "pts": 30, "color": FG.MAGENTA,"label": "钻石"},
]

FOOD_WEIGHTS = [0.50, 0.25, 0.13, 0.08, 0.04]

# ── Game mode definitions ──
GAME_MODES: list[str] = [
    "classic", "timeattack", "endless",
    "maze", "reverse", "blind", "zen", "speedrun"
]

MODE_LABELS: dict[str, str] = {
    "classic":    "经典",
    "timeattack": "限时挑战",
    "endless":    "无尽",
    "maze":       "迷宫",
    "reverse":    "反转",
    "blind":      "盲人",
    "zen":        "禅意",
    "speedrun":   "速通",
}

# ── Console setup ──
def setup_console() -> None:
    """Force UTF-8 and enable VT processing on Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.GetStdHandle(-11)
        m = ctypes.c_ulong()
        ctypes.windll.kernel32.GetConsoleMode(h, ctypes.byref(m))
        ctypes.windll.kernel32.SetConsoleMode(h, m.value | 0x0004)
