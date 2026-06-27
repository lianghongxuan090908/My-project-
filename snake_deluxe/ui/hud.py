"""
In-game HUD rendering — score, combo, timer, food info.

All functions return lists of strings ready to join with ``\\n``.
No direct terminal I/O (caller prints the result).
"""

import re

from snake_deluxe.core.consts import BOLD, RESET, FG, MODE_LABELS

# ── ANSI-aware string helpers ──


def _visible_len(s: str) -> int:
    """Return the visible display length of a string, ignoring ANSI escapes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _pad_to(s: str, target: int) -> str:
    """Right-pad *s* with spaces to reach *target* visible columns."""
    return s + " " * max(0, target - _visible_len(s))


# ── HUD border helper ──


def render_hud_border(width: int, color: str) -> list[str]:
    """
    Return top and bottom HUD borders as two strings.

    Args:
        width: Total character width of the HUD (including border chars).
        color: ANSI color escape (e.g. ``FG.CYAN``) for the border lines.

    Returns:
        ``[top_border, bottom_border]`` — each uses box-drawing characters.
    """
    inner = width - 2
    top = f"{color}╔{'═' * inner}╗{RESET}"
    bot = f"{color}╚{'═' * inner}╝{RESET}"
    return [top, bot]


# ── Main HUD renderer ──


def render_hud(game_state: dict) -> list[str]:
    """
    Build the in-game HUD as a list of strings (join with ``\\n``).

    Consumed keys from *game_state*:

    +-------------------+---------------------------------------------+
    | Key               | Purpose                                     |
    +===================+=============================================+
    | ``score``         | Current score (int)                         |
    | ``highscore``     | All-time high score (int)                   |
    | ``combo``         | Active combo count (int, display when > 1)  |
    | ``combo_bonus``   | Percentage bonus from combo (int)           |
    | ``diff``          | Difficulty label (str, e.g. ``"Normal"``)   |
    | ``mode``          | Game mode key (str, e.g. ``"classic"``)     |
    | ``time_remaining``| Seconds left in time-attack mode (int)      |
    | ``theme``         | Active theme name (str, display only)       |
    | ``food_ch``       | Current food character (str)                |
    | ``food_label``    | Current food type label (str)               |
    | ``food_pts``      | Points the current food is worth (int)      |
    | ``msg``           | Floating message text (str, empty = none)   |
    | ``msg_time``      | Seconds remaining for *msg* (float, >0)     |
    | ``width``         | Total HUD width (int, default 60)           |
    +-------------------+---------------------------------------------+

    Returns:
        list[str] — join with ``"\\n"`` and write to ``sys.stdout``.
    """
    gs = game_state
    w = max(int(gs.get("width", 60)), 12)
    inner = w - 2
    lines: list[str] = []

    # ── inline helper: build a bordered line ──
    side = f"{FG.WHITE}║{RESET}"

    def _line(content: str) -> str:
        return f"{side}{_pad_to(content, inner)}{side}"

    # ══════════════════════════════════════════════════════════════
    #  Top border
    # ══════════════════════════════════════════════════════════════
    lines.append(f"{FG.CYAN}╔{'═' * inner}╗{RESET}")

    # ══════════════════════════════════════════════════════════════
    #  Score row  —  Score + High Score  |  Difficulty + Mode
    # ══════════════════════════════════════════════════════════════
    score = gs.get("score", 0)
    highscore = gs.get("highscore", 0)
    diff = gs.get("diff", "Normal")
    mode_key = gs.get("mode", "classic")
    mode_label = MODE_LABELS.get(mode_key, mode_key.title())

    left_part = (
        f" {BOLD}{FG.YELLOW}分数:{RESET} {score}"
        f"  {BOLD}最高:{RESET} {highscore}"
    )
    right_part = (
        f"{BOLD}{FG.CYAN}{diff}{RESET}"
        f"  {BOLD}{FG.GREEN}{mode_label}{RESET} "
    )
    gap = inner - _visible_len(left_part) - _visible_len(right_part)
    if gap >= 0:
        score_line = left_part + " " * gap + right_part
    else:
        # narrow terminal fallback
        score_line = left_part + " " + right_part
        score_line = _pad_to(score_line, inner)
    lines.append(_line(score_line))

    # ══════════════════════════════════════════════════════════════
    #  Combo row  —  only when combo > 1
    # ══════════════════════════════════════════════════════════════
    combo = gs.get("combo", 0)
    if isinstance(combo, int) and combo > 1:
        bonus = gs.get("combo_bonus", 0)
        combo_text = (
            f" {FG.MAGENTA}{BOLD}连击 x{combo}!{RESET}"
            f"  {FG.YELLOW}+{bonus}% 分{RESET}"
        )
        lines.append(_line(combo_text))

    # ══════════════════════════════════════════════════════════════
    #  Time-attack timer  —  mode-specific
    # ══════════════════════════════════════════════════════════════
    if gs.get("mode") in ("timeattack", "speedrun"):
        remaining = gs.get("time_remaining", 0)
        urgent = FG.RED if (isinstance(remaining, (int, float)) and remaining <= 10) else FG.YELLOW
        timer_text = f" {urgent}{BOLD}⏱  时间: {remaining}秒{RESET}"
        lines.append(_line(timer_text))

    # ══════════════════════════════════════════════════════════════
    #  AI indicator  —  shows when AI is controlling the snake
    # ══════════════════════════════════════════════════════════════
    if gs.get("ai_enabled", False):
        ai_text = f" {FG.BMAG}{BOLD}🤖 AI 控制中{RESET}"
        lines.append(_line(ai_text))

    # ══════════════════════════════════════════════════════════════
    #  Theme row  —  current theme name
    # ══════════════════════════════════════════════════════════════
    theme_name = gs.get("theme", "")
    if theme_name:
        theme_text = f" {BOLD}主题:{RESET} {FG.BCYN}{theme_name}{RESET}"
        lines.append(_line(theme_text))

    # ══════════════════════════════════════════════════════════════
    #  Food info row
    # ══════════════════════════════════════════════════════════════
    food_ch = gs.get("food_ch", "★")
    food_label = gs.get("food_label", "Basic")
    food_pts = gs.get("food_pts", 10)
    food_text = (
        f" {BOLD}食物:{RESET} {food_ch}  "
        f"{FG.GREEN}{food_label}{RESET}"
        f"  ({FG.YELLOW}+{food_pts} 分{RESET})"
    )
    lines.append(_line(food_text))

    # ══════════════════════════════════════════════════════════════
    #  Message row  —  floating in-game messages
    # ══════════════════════════════════════════════════════════════
    msg = gs.get("msg", "")
    msg_time = gs.get("msg_time", 0.0)
    if msg and isinstance(msg_time, (int, float)) and msg_time > 0:
        msg_text = f" {FG.BYEL}{BOLD}{msg}{RESET}"
        lines.append(_line(msg_text))

    # ══════════════════════════════════════════════════════════════
    #  Bottom border
    # ══════════════════════════════════════════════════════════════
    lines.append(f"{FG.CYAN}╚{'═' * inner}╝{RESET}")

    return lines
