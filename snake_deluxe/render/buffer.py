"""
Screen buffer: builds a 2-D character grid and renders it to the terminal
using ANSI escape codes.  No CLS, no flicker — just HOME + overwrite.

The buffer maintains two parallel grids:
  - ``_ch_grid`` — the character at each cell (usually a single Unicode glyph)
  - ``_fg_grid`` — the ANSI colour escape string for that cell

Rendering proceeds in fixed Z-order: floor → walls → obstacles → food →
snake body → snake head → particles.  The final output is assembled as a
single string and written to ``sys.stdout`` in one shot.
"""

import sys
from typing import Any, Optional

from snake_deluxe.core.consts import CSI, HOME, HIDE_CURSOR, SHOW_CURSOR, RESET
from snake_deluxe.core.consts import FG

# ── default theme fallback ──
_DEFAULT_THEME: dict[str, Any] = {
    "wall": "#",
    "floor": " ",
    "snake_head": "@",
    "snake_body": "o",
    "obstacle": "X",
    "food_symbols": ["\u2605", "\u25CF", "\u25C6", "\u2663", "\u2666"],
    "colors": {
        "wall": FG.GREEN,
        "snake_head": FG.BGRN,
        "snake_body": FG.GREEN,
        "obstacle": FG.RED,
        "hud_border": FG.CYAN,
        "title": FG.BGRN,
    },
}

# ── ANSI helper: set cursor column ──
_CPOS = lambda col: f"{CSI}{col}G"


# ===================================================================
# ScreenBuffer
# ===================================================================

class ScreenBuffer:
    """Double-buffered terminal screen with ANSI rendering.

    Builds a 2-D character + colour grid and flushes to ``sys.stdout``
    using the HOME cursor escape to avoid flicker.

    Args:
        w:     Number of logical columns (characters).
        h:     Number of logical rows.
        theme: Theme dictionary (see ``snake_deluxe.themes.data``).
    """

    def __init__(
        self,
        w: int,
        h: int,
        theme: Optional[dict[str, Any]] = None,
    ) -> None:
        self._w = int(w)
        self._h = int(h)
        self._theme: dict[str, Any] = theme or dict(_DEFAULT_THEME)
        self._colors: dict[str, str] = self._theme.get("colors", {})

        # char grid: grid[y][x] = (char, color_escape or "")
        self._fg_grid: list[list[str]] = [
            [""] * self._w for _ in range(self._h)
        ]
        self._ch_grid: list[list[str]] = [
            [" "] * self._w for _ in range(self._h)
        ]

        # Previous-frame tracking for minimal-diff rendering
        self._prev_ch: Optional[list[list[str]]] = None

        # Colour cache: map (r, g, b) tuples to 256-color escapes
        self._color_cache: dict[tuple[int, int, int], str] = {}

    # ── property helpers ──

    @property
    def width(self) -> int:
        """Grid width in logical cells."""
        return self._w

    @property
    def height(self) -> int:
        """Grid height in logical rows."""
        return self._h

    @property
    def theme(self) -> dict[str, Any]:
        """Return the active theme (read-only view)."""
        return dict(self._theme)

    # ── public API ──

    def set(self, x: int, y: int, char: str, color: Optional[str] = None) -> None:
        """Place *char* at grid position (x, y) with optional ANSI colour.

        Coordinates outside the buffer are silently ignored.
        """
        if 0 <= x < self._w and 0 <= y < self._h:
            self._ch_grid[y][x] = char
            self._fg_grid[y][x] = color or ""

    def fill(
        self,
        x0: int, y0: int,
        x1: int, y1: int,
        char: str,
        color: Optional[str] = None,
    ) -> None:
        """Fill a rectangular region with the same character and colour.

        Coordinates are clamped to buffer bounds.
        """
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self._w - 1, x1)
        y1 = min(self._h - 1, y1)
        col = color or ""
        for y in range(y0, y1 + 1):
            row_ch = self._ch_grid[y]
            row_fg = self._fg_grid[y]
            for x in range(x0, x1 + 1):
                row_ch[x] = char
                row_fg[x] = col

    def clear(self) -> None:
        """Reset the buffers to floor characters from the active theme."""
        floor = self._theme.get("floor", " ")
        for y in range(self._h):
            row_ch = self._ch_grid[y]
            row_fg = self._fg_grid[y]
            for x in range(self._w):
                row_ch[x] = floor
                row_fg[x] = ""

    def resize(self, w: int, h: int) -> None:
        """Resize the buffer, preserving as much of the current content as
        possible.  New cells are filled with the floor character.
        """
        old_w, old_h = self._w, self._h
        self._w = int(w)
        self._h = int(h)

        # grow or shrink row by row
        new_ch: list[list[str]] = [
            [" "] * self._w for _ in range(self._h)
        ]
        new_fg: list[list[str]] = [
            [""] * self._w for _ in range(self._h)
        ]
        floor = self._theme.get("floor", " ")

        for y in range(min(old_h, self._h)):
            for x in range(min(old_w, self._w)):
                new_ch[y][x] = self._ch_grid[y][x]
                new_fg[y][x] = self._fg_grid[y][x]
            for x in range(old_w, self._w):
                new_ch[y][x] = floor

        self._ch_grid = new_ch
        self._fg_grid = new_fg

    def set_theme(self, theme: dict[str, Any]) -> None:
        """Swap theme and re-apply floor characters.

        The previous content is discarded — call ``render_frame``
        with a fresh state after changing the theme.
        """
        self._theme = dict(theme)
        self._colors = self._theme.get("colors", {})
        self.clear()

    # ── colour-cache helpers ──

    def _make_256_color(self, r: int, g: int, b: int) -> str:
        """Return a 256-color ANSI escape for an integer RGB triple.
        Results are cached so we don't generate the same escape twice.
        """
        key = (r, g, b)
        if key not in self._color_cache:
            # nearest 6×6×6 cube index
            ri = max(0, min(5, round(r / 51)))
            gi = max(0, min(5, round(g / 51)))
            bi = max(0, min(5, round(b / 51)))
            idx = 16 + 36 * ri + 6 * gi + bi
            self._color_cache[key] = f"{CSI}38;5;{idx}m"
        return self._color_cache[key]

    # ── rendering ──

    def render_frame(self, state: dict[str, Any]) -> None:
        """Render a complete frame from a game-state dictionary.

        Expected keys:

            snake_body     list[(x, y)]   — snake segment positions
            food_pos       (x, y)         — food location
            food_ch        str            — food character
            obstacle_list  list[(x, y)]   — obstacle positions
            particle_list  list[dict]     — active particles
            borders        set[(x,y)]     — wall cells
            theme          dict           — active theme (overrides)
            score          int
            combo          int
            mode           str
            diff           str
            msg            str or None    — overlay message
            msg_t          int or None    — message timer frames
            time_limit     int or None    — time-attack limit (s)
            play_time      float          — elapsed seconds
            seeds          int or None    — seed count (maze mode)

        The frame is assembled in Z-order and flushed in one write.
        """
        # ── 1. Apply theme override ──
        if "theme" in state and state["theme"]:
            self.set_theme(state["theme"])

        # ── 2. Clear floor ──
        self.clear()

        theme = self._theme
        colors = self._colors

        # ── 3. Walls (borders) — Z=0 ──
        borders: set[tuple[int, int]] = state.get("borders") or set()
        wall_ch = theme.get("wall", "#")
        wall_col = colors.get("wall", "")
        for bx, by in borders:
            self.set(bx, by, wall_ch, wall_col)

        # ── 4. Obstacles — Z=1 ──
        obs_ch = theme.get("obstacle", "X")
        obs_col = colors.get("obstacle", "")
        for ox, oy in state.get("obstacle_list", []):
            self.set(ox, oy, obs_ch, obs_col)

        # ── 5. Food — Z=2 ──
        fpos = state.get("food_pos")
        if fpos:
            fx, fy = fpos
            fch = state.get("food_ch", theme["food_symbols"][0])
            self.set(fx, fy, fch, colors.get("obstacle", FG.RED))

        # ── 6. Snake body — Z=3 (head rendered last for overlap) ──
        body: list[tuple[int, int]] = state.get("snake_body", [])
        head_char = theme.get("snake_head", "@")
        head_col = colors.get("snake_head", FG.BGRN)
        body_char = theme.get("snake_body", "o")
        body_col = colors.get("snake_body", FG.GREEN)

        # Draw body segments in reverse so head paints last
        for idx in range(len(body) - 1, -1, -1):
            sx, sy = body[idx]
            if idx == 0:
                self.set(sx, sy, head_char, head_col)
            else:
                self.set(sx, sy, body_char, body_col)

        # ── 7. Particles — Z=4 ──
        for p in state.get("particle_list", []):
            px = int(round(p.get("x", 0)))
            py = int(round(p.get("y", 0)))
            pch = p.get("char", "*")
            pcol = p.get("color", "")
            self.set(px, py, pch, pcol)

        # ── 8. Build the output string ──
        out: list[str] = []
        out.append(HIDE_CURSOR)
        out.append(HOME)

        hcol = colors.get("hud_border", FG.CYAN)
        score = state.get("score", 0)
        combo = state.get("combo", 0)
        mode_raw = state.get("mode", "")
        mode = mode_raw.capitalize() if mode_raw else ""
        diff = state.get("diff", "")
        play_time = state.get("play_time", 0.0)
        seeds = state.get("seeds", None)

        # ── HUD: left block ──
        left_parts: list[str] = [f" {mode}"]
        if diff:
            left_parts.append(f"| {diff}")
        if seeds is not None:
            left_parts.append(f"| Seeds:{seeds}")
        hud_left = " ".join(left_parts)

        # ── HUD: right block ──
        time_limit = state.get("time_limit")
        if time_limit is not None:
            remaining = max(0, time_limit - play_time)
            hud_right = f" Score:{score}  Combo:{combo}x  Time:{remaining:.0f}s "
        else:
            hud_right = f" Score:{score}  Combo:{combo}x  Time:{play_time:.0f}s "

        hud_line = hud_left + "  │" + hud_right
        out.append(hcol)
        out.append(hud_line)
        out.append(RESET)
        out.append("\r\n")

        # ── Playfield rows ──
        screen_w = self._w
        for y in range(self._h):
            row_chars: list[str] = []
            row_cols: list[str] = []
            prev_col = ""
            for x in range(screen_w):
                ch = self._ch_grid[y][x]
                col = self._fg_grid[y][x]
                if col != prev_col and col:
                    row_cols.append(col)
                    prev_col = col
                row_chars.append(ch)
                row_chars.append(" ")   # double-width cell
            out.append("".join(row_cols))
            out.append("".join(row_chars))
            out.append(RESET)
            out.append("\r\n")

        # ── Message overlay ──
        msg = state.get("msg")
        msg_t = state.get("msg_t")
        if msg and msg_t is not None and msg_t > 0:
            out.append(hcol)
            out.append(f" \u26a1 {msg} ")
            out.append(RESET)
        else:
            out.append(" " * (screen_w * 2))

        out.append("\r\n")
        out.append(SHOW_CURSOR)

        # ── 9. Flush ──
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def debug_repr(self) -> str:
        """Return a plain-text representation of the current buffer
        (no ANSI escapes) for debugging.
        """
        lines: list[str] = []
        for y in range(self._h):
            line = "".join(self._ch_grid[y])
            lines.append(line)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<ScreenBuffer {self._w}x{self._h}>"
