"""
Menu screens for Snake Deluxe — main menu, pause overlay, game over,
leaderboard, settings, stats, help, and theme browser.

Every ``draw_*`` function clears the screen, writes directly to
``sys.stdout`` via ``sys.stdout.write()``, and returns ``None``.
"""

import sys
import re

from snake_deluxe.core.consts import (
    CLS,
    HOME,
    HIDE_CURSOR,
    SHOW_CURSOR,
    BOLD,
    RESET,
    FG,
    DIFFICULTIES,
    GAME_MODES,
    MODE_LABELS,
    OPPOSITE,
)

# ══════════════════════════════════════════════════════════════════════════════
#  ANSI-aware string helpers
# ══════════════════════════════════════════════════════════════════════════════


def _vlen(s: str) -> int:
    """Visible length of a string (ignoring ANSI escapes)."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _pad(s: str, w: int) -> str:
    """Right-pad *s* to visible width *w*."""
    return s + " " * max(0, w - _vlen(s))


def _center(s: str, w: int) -> str:
    """Center *s* in visible width *w*."""
    v = _vlen(s)
    if v >= w:
        return s
    left = (w - v) // 2
    return " " * left + s + " " * (w - v - left)


def _repeat(ch: str, n: int) -> str:
    """Repeat character *ch* *n* times (with 0 clamp)."""
    return ch * max(0, n)


# ══════════════════════════════════════════════════════════════════════════════
#  Display constants
# ══════════════════════════════════════════════════════════════════════════════

# Standard menu width — wide enough for the title art.
MENU_W = 64

# Title art (block letters).
TITLE_ART: list[str] = [
    r"███████╗███╗   ██╗ █████╗ ██╗  ██╗███████╗",
    r"██╔════╝████╗  ██║██╔══██╗██║ ██╔╝██╔════╝",
    r"███████╗██╔██╗ ██║███████║█████╔╝ █████╗  ",
    r"╚════██║██║╚██╗██║██╔══██║██╔═██╗ ██╔══╝  ",
    r"███████║██║ ╚████║██║  ██║██║  ██╗███████╗",
    r"╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝",
    r"██████╗ ███████╗██╗     ██╗   ██╗██╗  ██╗███████╗",
    r"██╔══██╗██╔════╝██║     ██║   ██║╚██╗██╔╝██╔════╝",
    r"██║  ██║█████╗  ██║     ██║   ██║ ╚███╔╝ █████╗  ",
    r"██║  ██║██╔══╝  ██║     ██║   ██║ ██╔██╗ ██╔══╝  ",
    r"██████╔╝███████╗███████╗╚██████╔╝██╔╝ ██╗███████╗",
    r"╚═════╝ ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝",
]

# Color palette for title animation.
_TITLE_COLORS = [FG.RED, FG.YELLOW, FG.GREEN, FG.CYAN, FG.BLUE, FG.MAGENTA]

# Medal symbols for the leaderboard.
_MEDALS = ["\u263A", "\u263B", "\u2665"]  # ☺ ☻ ♥


def _title_color(frame: int) -> str:
    """Return a color for the title art based on animation frame."""
    return _TITLE_COLORS[frame % len(_TITLE_COLORS)]


def _should_blink(frame: int) -> bool:
    """Return True on even frames (visible blink phase)."""
    return frame % 2 == 0


def _hdr(text: str) -> str:
    """Return a formatted section header."""
    return f"{FG.CYAN}{BOLD}{text}{RESET}"


# ══════════════════════════════════════════════════════════════════════════════
#  draw_main_menu
# ══════════════════════════════════════════════════════════════════════════════


def draw_main_menu(
    anim_frame: int,
    current_diff: str,
    current_mode: str,
    current_theme_name: str,
) -> None:
    """
    Full-screen main menu.

    Args:
        anim_frame: Incrementing frame counter for animation (colour cycling &
            blinking).
        current_diff: Currently selected difficulty key (e.g. ``"Normal"``).
        current_mode: Currently selected mode key (e.g. ``"classic"``).
        current_theme_name: Active theme display name.
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    tc = _title_color(anim_frame)

    # ── title art ──
    for line in TITLE_ART:
        buf.append(f"{tc}{BOLD}{line}{RESET}")
    buf.append("")

    # ── difficulty column ──
    buf.append(f"  {_hdr('难  度')}")
    for d in DIFFICULTIES:
        cfg = DIFFICULTIES[d]
        marker = f"{FG.GREEN}\u25C0{RESET}" if d == current_diff else " "
        speed_str = f"{cfg['speed'] * 1000:.0f}毫秒"
        dim = f"{FG.WHITE}{cfg['w']}\u00d7{cfg['h']}{RESET}"
        buf.append(
            f"    {marker}  {BOLD}{d}{RESET}"
            f"  {FG.CYAN}{speed_str}{RESET}"
            f"  ({dim}, {cfg['obs']} 障碍物)"
        )
    buf.append("")

    # ── mode column ──
    buf.append(f"  {_hdr('游戏模式')}")
    for m in GAME_MODES:
        label = MODE_LABELS.get(m, m.title())
        marker = f"{FG.GREEN}\u25C0{RESET}" if m == current_mode else " "
        buf.append(f"    {marker}  {label}")
    buf.append("")

    # ── theme info ──
    buf.append(
        f"  {_hdr('主  题')}:  {FG.BCYN}{current_theme_name}{RESET}"
    )
    buf.append("")

    # ── key bindings ──
    buf.append(
        f"  {FG.WHITE}\u2500 操作控制{RESET}"
    )
    buf.append(
f"  {FG.CYAN}W A S D{RESET} / "
f"{FG.YELLOW}\u2190\u2191\u2193\u2192{RESET}  移动  "
f"{FG.CYAN}P{RESET} 暂停  "
f"{FG.CYAN}A{RESET} AI  "
f"{FG.CYAN}Q{RESET} 退出"
    )
    buf.append(
f"  {FG.CYAN}S{RESET} 设置  "
f"{FG.CYAN}H{RESET} 排行  "
f"{FG.CYAN}T{RESET} 主题  "
f"{FG.CYAN}Enter{RESET} 开始"
    )
    buf.append("")

    # ── blinking start prompt ──
    start_text = "按 ENTER 开始游戏"
    if _should_blink(anim_frame):
        buf.append(
            f"{_center(start_text, MENU_W)}"
        )
    else:
        buf.append(
            f"{_center(f'{FG.BLACK}{start_text}{RESET}', MENU_W)}"
        )

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_pause
# ══════════════════════════════════════════════════════════════════════════════


def draw_pause(anim_frame: int) -> None:
    """
    Pause overlay — centred dialog box on a dimmed background.

    Args:
        anim_frame: Frame counter (controls blinking of the title).
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    # fill screen with blank lines to centre the dialog
    rows_before = 8
    for _ in range(rows_before):
        buf.append("")

    # ── dialog box ──
    box_w = 36
    inner_w = box_w - 4

    # top border
    buf.append(
        _center(
            f"{FG.CYAN}\u2554{_repeat('\u2550', inner_w)}\u2557{RESET}",
            MENU_W,
        )
    )

    # blank spacer
    buf.append(
        _center(f"{FG.CYAN}\u2551{RESET}{' ' * inner_w}{FG.CYAN}\u2551{RESET}", MENU_W)
    )

    # title
    title = f"{FG.YELLOW}{BOLD}  游戏暂停  {RESET}" if _should_blink(anim_frame) else f"  游戏暂停  "
    buf.append(
        _center(
            f"{FG.CYAN}\u2551{RESET}{_center(title, inner_w)}{FG.CYAN}\u2551{RESET}",
            MENU_W,
        )
    )

    # blank spacer
    buf.append(
        _center(f"{FG.CYAN}\u2551{RESET}{' ' * inner_w}{FG.CYAN}\u2551{RESET}", MENU_W)
    )

    # resume hint
    resume = f"{FG.WHITE}按  {BOLD}P/空格/Enter{RESET}{FG.WHITE}  继续{RESET}"
    buf.append(
        _center(
            f"{FG.CYAN}\u2551{RESET}{_center(resume, inner_w)}{FG.CYAN}\u2551{RESET}",
            MENU_W,
        )
    )

    # quit hint
    quit_hint = f"{FG.WHITE}按  {BOLD}Q{RESET}{FG.WHITE}  返回菜单{RESET}"
    buf.append(
        _center(
            f"{FG.CYAN}\u2551{RESET}{_center(quit_hint, inner_w)}{FG.CYAN}\u2551{RESET}",
            MENU_W,
        )
    )

    # blank spacer
    buf.append(
        _center(f"{FG.CYAN}\u2551{RESET}{' ' * inner_w}{FG.CYAN}\u2551{RESET}", MENU_W)
    )

    # bottom border
    buf.append(
        _center(
            f"{FG.CYAN}\u255A{_repeat('\u2550', inner_w)}\u255D{RESET}",
            MENU_W,
        )
    )

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_game_over
# ══════════════════════════════════════════════════════════════════════════════


def draw_game_over(
    anim_frame: int,
    score: int,
    top: int,
    new_record: bool,
    stats_line: str,
) -> None:
    """
    Game-over screen with score summary and blinking death text.

    Args:
        anim_frame: Frame counter (blinking).
        score: Final score.
        top: All-time high score.
        new_record: Whether this game set a new high score.
        stats_line: Pre-formatted one-line summary of game stats.
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    # vertical centring
    for _ in range(6):
        buf.append("")

    # ── blinking death title ──
    death_text = f"{FG.RED}{BOLD}游 戏 结 束{RESET}" if _should_blink(anim_frame) else f"游 戏 结 束"
    buf.append(f"  {_center(death_text, MENU_W)}")
    buf.append("")

    # ── skull decoration ──
    skull = f"{FG.YELLOW}\u2620{RESET}" if _should_blink(anim_frame) else " "
    buf.append(f"  {_center(f'{skull}  {FG.RED}{BOLD}\u2580\u2580\u2580  {RESET}{skull}', MENU_W)}")
    buf.append("")

    # ── score ──
    score_str = f"{BOLD}{FG.YELLOW}分  数:{RESET} {score}"
    buf.append(f"  {_center(score_str, MENU_W)}")

    # ── high score ──
    hi_str = f"{BOLD}最高分:{RESET} {top}"
    if new_record:
        hi_str += f"   {FG.GREEN}{BOLD}新 纪 录 ！{RESET}"
    buf.append(f"  {_center(hi_str, MENU_W)}")

    if new_record:
        stars = f"{FG.YELLOW}{BOLD}\u2605 \u2605 \u2605{RESET}"
        buf.append(f"  {_center(stars, MENU_W)}")

    buf.append("")

    # ── stats line ──
    if stats_line:
        stats_display = f"{FG.CYAN}{stats_line}{RESET}"
        buf.append(f"  {_center(stats_display, MENU_W)}")
        buf.append("")

    # ── continue prompt ──
    prompt = f"{FG.WHITE}按  {BOLD}ENTER{RESET}{FG.WHITE}  继续{RESET}"
    if _should_blink(anim_frame):
        buf.append(f"  {_center(prompt, MENU_W)}")
    else:
        buf.append(f"  {_center('', MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_leaderboard
# ══════════════════════════════════════════════════════════════════════════════


def draw_leaderboard(
    entries: list[tuple[int, str, str]],
    diff: str,
    mode: str,
) -> None:
    """
    Full-screen leaderboard (top 5).

    Args:
        entries: Sorted list of ``(score, name, date)`` tuples.
        diff: Difficulty label (e.g. ``"Normal"``).
        mode: Mode key (e.g. ``"classic"``).
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    for _ in range(3):
        buf.append("")

    # ── title ──
    mode_label = MODE_LABELS.get(mode, mode.title())
    title = f"{BOLD}{FG.YELLOW}排 行 榜{RESET}  {FG.CYAN}{diff} / {mode_label}{RESET}"
    buf.append(f"  {_center(title, MENU_W)}")
    buf.append("")

    # ── box top ──
    box_inner = MENU_W - 6
    buf.append(
        f"    {FG.CYAN}\u2554{_repeat('\u2550', box_inner)}\u2557{RESET}"
    )

    if not entries:
        # empty state
        empty = f"{FG.WHITE}暂无分数！{RESET}"
        buf.append(
            f"    {FG.CYAN}\u2551{RESET}{_center(empty, box_inner)}{FG.CYAN}\u2551{RESET}"
        )
    else:
        header = f"{BOLD}{'排名':>5}  {'分数':>7}  {'名字':<12}  日期{RESET}"
        buf.append(
            f"    {FG.CYAN}\u2551{RESET} {_pad(header, box_inner - 1)} "
            f"{FG.CYAN}\u2551{RESET}"
        )
        buf.append(
            f"    {FG.CYAN}\u2551{RESET}"
            f" {FG.WHITE}{_repeat('\u2500', box_inner - 2)}{RESET} "
            f"{FG.CYAN}\u2551{RESET}"
        )

        medals = _MEDALS  # gold, silver, bronze face symbols

        for rank, (score_val, name, date_str) in enumerate(entries, start=1):

            if rank <= 3:
                rank_disp = f"{FG.YELLOW}{BOLD}{medals[rank - 1]}{RESET}"
            else:
                rank_disp = f"{FG.WHITE}{rank}{RESET}"

            score_col = f"{FG.WHITE}{score_val:>7}{RESET}" if rank > 3 else f"{FG.YELLOW}{BOLD}{score_val:>7}{RESET}"
            name_col = f"{FG.GREEN}{_pad(name, 12)}{RESET}"
            date_col = f"{FG.CYAN}{date_str}{RESET}"

            line = f" {rank_disp}  {score_col}  {name_col}  {date_col}"
            line = _pad(line, box_inner - 1)
            buf.append(
                f"    {FG.CYAN}\u2551{RESET} {line} {FG.CYAN}\u2551{RESET}"
            )

    # ── box bottom ──
    buf.append(
        f"    {FG.CYAN}\u255A{_repeat('\u2550', box_inner)}\u255D{RESET}"
    )
    buf.append("")

    # ── return prompt ──
    prompt = f"{FG.WHITE}按任意键返回{RESET}"
    buf.append(f"  {_center(prompt, MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_settings
# ══════════════════════════════════════════════════════════════════════════════


def draw_settings(current_theme: str, sound_on: bool) -> None:
    """
    Settings screen — theme selector and sound toggle.

    Args:
        current_theme: Active theme display name.
        sound_on: Whether sound effects are enabled.
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    for _ in range(5):
        buf.append("")

    # ── title ──
    buf.append(f"  {_center(f'{BOLD}{FG.YELLOW}设    置{RESET}', MENU_W)}")
    buf.append("")

    # ── box ──
    box_inner = MENU_W - 6

    # top
    buf.append(
        f"    {FG.CYAN}\u2554{_repeat('\u2550', box_inner)}\u2557{RESET}"
    )

    # theme row
    theme_row = (
        f"{FG.WHITE}{BOLD}主题:{RESET}  "
        f"{FG.BCYN}{current_theme}{RESET}  "
        f"{FG.WHITE}(\u2190 \u2192 切换){RESET}"
    )
    buf.append(
        f"    {FG.CYAN}\u2551{RESET} {_pad(theme_row, box_inner - 1)} "
        f"{FG.CYAN}\u2551{RESET}"
    )

    # separator
    buf.append(
        f"    {FG.CYAN}\u2551{RESET}"
        f" {FG.WHITE}{_repeat('\u2500', box_inner - 2)}{RESET} "
        f"{FG.CYAN}\u2551{RESET}"
    )

    # sound row
    sound_status = f"{FG.GREEN}开{RESET}" if sound_on else f"{FG.RED}关{RESET}"
    sound_row = (
        f"{FG.WHITE}{BOLD}音效:{RESET}  "
        f"{sound_status}  "
        f"{FG.WHITE}(按 S 开关){RESET}"
    )
    buf.append(
        f"    {FG.CYAN}\u2551{RESET} {_pad(sound_row, box_inner - 1)} "
        f"{FG.CYAN}\u2551{RESET}"
    )

    # spacer
    buf.append(
        f"    {FG.CYAN}\u2551{RESET}{' ' * box_inner}{FG.CYAN}\u2551{RESET}"
    )

    # controls hint
    ctrl = f"{FG.WHITE}操作:  {FG.CYAN}\u2190 \u2192{RESET} 浏览主题  {FG.CYAN}S{RESET} 音效  {FG.CYAN}ESC{RESET} 返回{RESET}"
    buf.append(
        f"    {FG.CYAN}\u2551{RESET} {_pad(ctrl, box_inner - 1)} "
        f"{FG.CYAN}\u2551{RESET}"
    )

    # bottom
    buf.append(
        f"    {FG.CYAN}\u255A{_repeat('\u2550', box_inner)}\u255D{RESET}"
    )
    buf.append("")

    # return prompt
    prompt = f"{FG.WHITE}按  {BOLD}ESC{RESET}{FG.WHITE}  返回菜单{RESET}"
    buf.append(f"  {_center(prompt, MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_stats
# ══════════════════════════════════════════════════════════════════════════════


def draw_stats(stats_data: dict, achievements: list[str]) -> None:
    """
    Player statistics and achievements screen.

    Args:
        stats_data: Dict of stat key → value (int/str).
            Typical keys: ``games_played``, ``total_score``, ``high_score``,
            ``food_eaten``, ``longest_snake``, ``time_played``, ``max_combo``.
        achievements: List of achievement display strings.
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    for _ in range(2):
        buf.append("")

    # ── title ──
    buf.append(f"  {_center(f'{BOLD}{FG.YELLOW}玩 家 统 计{RESET}', MENU_W)}")
    buf.append("")

    # ── stats box ──
    box_inner = MENU_W - 6

    # top
    buf.append(
        f"    {FG.CYAN}\u2554{_repeat('\u2550', box_inner)}\u2557{RESET}"
    )

    stat_labels: dict[str, str] = {
        "games_played": "游戏次数",
        "total_score": "总分",
        "high_score": "最高分",
        "food_eaten": "食物数",
        "longest_snake": "最长长度",
        "time_played": "游戏时长",
        "max_combo": "最高连击",
    }

    stat_index = 0
    for key, label in stat_labels.items():
        if key not in stats_data:
            continue
        val = stats_data[key]
        # format the value nicely
        if isinstance(val, int):
            formatted = f"{val:,}"
        elif isinstance(val, float):
            formatted = f"{val:.1f}"
        else:
            formatted = str(val)

        if stat_index % 2 == 0:
            color = FG.WHITE
        else:
            color = FG.CYAN

        row = f"{color}{BOLD}{label}:{RESET}  {FG.YELLOW}{formatted}{RESET}"
        # pad to two columns
        row = _pad(row, box_inner // 2) + " "
        buf.append(
            f"    {FG.CYAN}\u2551{RESET} {_pad(row, box_inner - 1)} "
            f"{FG.CYAN}\u2551{RESET}"
        )
        stat_index += 1

    # separator if there are achievements
    if achievements:
        buf.append(
            f"    {FG.CYAN}\u2551{RESET}"
            f" {FG.WHITE}{_repeat('\u2500', box_inner - 2)}{RESET} "
            f"{FG.CYAN}\u2551{RESET}"
        )

        # achievements header
        ach_header = f"{BOLD}{FG.YELLOW}成  就{RESET}"
        buf.append(
            f"    {FG.CYAN}\u2551{RESET} {_pad(ach_header, box_inner - 1)} "
            f"{FG.CYAN}\u2551{RESET}"
        )

        for ach in achievements:
            ach_line = f" {FG.GREEN}\u2713{RESET}  {FG.WHITE}{ach}{RESET}"
            buf.append(
                f"    {FG.CYAN}\u2551{RESET} {_pad(ach_line, box_inner - 1)} "
                f"{FG.CYAN}\u2551{RESET}"
            )

    # bottom
    buf.append(
        f"    {FG.CYAN}\u255A{_repeat('\u2550', box_inner)}\u255D{RESET}"
    )
    buf.append("")

    # return prompt
    prompt = f"{FG.WHITE}Press any key to return{RESET}"
    buf.append(f"  {_center(prompt, MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_help
# ══════════════════════════════════════════════════════════════════════════════


def draw_help() -> None:
    """
    Help screen — controls reference and game mode explanations.
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    for _ in range(1):
        buf.append("")

    # ── title ──
    buf.append(f"  {_center(f'{BOLD}{FG.YELLOW}帮      助{RESET}', MENU_W)}")
    buf.append("")

    # ── controls section ──
    controls = [
        ("W / \u2191", "向上移动"),
        ("A / \u2190", "向左移动"),
        ("S / \u2193", "向下移动"),
        ("D / \u2192", "向右移动"),
        ("P", "暂停 / 继续"),
        ("A", "切换 AI 模式"),
        ("Q", "返回主菜单"),
        ("ESC", "返回 / 取消"),
        ("ENTER", "确认 / 开始游戏"),
    ]

    buf.append(f"  {_hdr('操  作')}")
    for key, action in controls:
        k_col = f"{FG.CYAN}{BOLD}{key:<12}{RESET}"
        a_col = f"{FG.WHITE}{action}{RESET}"
        buf.append(f"    {k_col}  {a_col}")

    # note about reverse-direction protection
    buf.append("")
    buf.append(
        f"    {FG.WHITE}{BOLD}提示:{RESET}"
        f" {FG.CYAN}蛇不能直接反向移动{RESET}"
        f" {FG.WHITE}(防倒转规则).{RESET}"
    )
    buf.append("")

    # ── game modes ──
    mode_descriptions: dict[str, str] = {
        "classic": "标准贪吃蛇 — 吃食物变长，撞墙或自己则死亡。",
        "timeattack": "在时间耗尽前尽可能多得分。",
        "endless": "没有墙壁 — 从边界穿到对面。不会撞死。",
        "maze": "在程序生成的迷宫中穿行。",
        "reverse": "操作每隔几秒反转。",
        "blind": "墙壁不可见 — 靠记忆导航。",
        "zen": "不会死亡 — 轻松放置食物和生长。",
        "speedrun": "每吃一个食物速度都会增加。",
    }

    buf.append(f"  {_hdr('游戏模式')}")
    for mode_key in GAME_MODES:
        label = MODE_LABELS.get(mode_key, mode_key.title())
        desc = mode_descriptions.get(mode_key, "")
        buf.append(
            f"    {BOLD}{FG.GREEN}{label:<13}{RESET}"
            f"  {FG.WHITE}{desc}{RESET}"
        )
    buf.append("")

    # ── difficulty ──
    buf.append(f"  {_hdr('难  度')}")
    for d, cfg in DIFFICULTIES.items():
        buf.append(
            f"    {FG.CYAN}{d:<8}{RESET}"
            f"  {cfg['w']}\u00d7{cfg['h']} 面板"
            f"  {cfg['speed'] * 1000:.0f}毫秒/步"
            f"  {cfg['obs']} 障碍物"
        )
    buf.append("")

    # return prompt
    prompt = f"{FG.WHITE}按任意键返回{RESET}"
    buf.append(f"  {_center(prompt, MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  draw_theme_browser
# ══════════════════════════════════════════════════════════════════════════════


def draw_theme_browser(
    themes: list[str],
    current_idx: int,
    preview_data: dict,
) -> None:
    """
    Theme browser — choose a visual theme with live preview.

    Args:
        themes: List of all theme names (ordered).
        current_idx: Index of the currently selected theme.
        preview_data: Theme dict with ``"name"``, ``"colors"`` (dict of
            ANSI escapes), and optionally ``"title_art"`` (list[str]).
    """
    buf: list[str] = []
    buf.append(CLS + HIDE_CURSOR)

    for _ in range(2):
        buf.append("")

    # ── title ──
    buf.append(f"  {_center(f'{BOLD}{FG.YELLOW}主 题 浏 览{RESET}', MENU_W)}")
    buf.append("")

    # ── current theme name with navigation arrows ──
    nav_prev = f"{FG.CYAN}\u25C0{RESET}" if current_idx > 0 else " "
    nav_next = f"{FG.CYAN}\u25B6{RESET}" if current_idx < len(themes) - 1 else " "

    name = themes[current_idx] if 0 <= current_idx < len(themes) else "?"
    theme_line = f"  {nav_prev}  {FG.BCYN}{BOLD}{name}{RESET}  {nav_next}"
    buf.append(f"  {_center(theme_line, MENU_W)}")

    if len(themes) <= 1:
        idx_info = f"{FG.WHITE}1 / 1{RESET}"
    else:
        idx_info = f"{FG.WHITE}{current_idx + 1} / {len(themes)}{RESET}"
    buf.append(f"  {_center(idx_info, MENU_W)}")
    buf.append("")

    # ── preview area ──
    colors: dict = preview_data.get("colors", {})
    wall_color = colors.get("wall", FG.WHITE)
    snake_head = colors.get("snake_head", FG.GREEN)
    snake_body = colors.get("snake_body", FG.BGRN)
    food_color = colors.get("food", FG.RED)
    bg_color = colors.get("bg", FG.BLACK)

    preview_w = 30
    preview_inner = preview_w - 2

    # top border of preview
    buf.append(
        f"    {bg_color}{wall_color}\u2554{_repeat('\u2550', preview_inner)}"
        f"\u2557{RESET}"
    )

    # sample game frame lines
    # line 1: wall + empty + wall
    pw = preview_inner
    l1 = (
        f"{wall_color}\u2551{RESET}"
        f"{bg_color}{' ' * pw}{RESET}"
        f"{wall_color}\u2551{RESET}"
    )
    buf.append(f"    {l1}")

    # line 2: wall + snake head + body + empty + food + wall
    snake_demo = f"{snake_head}{BOLD}\u2588{RESET}{bg_color}{snake_body}{BOLD}\u2588\u2588\u2588{RESET}{bg_color}"
    food_demo = f"{food_color}{BOLD}\u2605{RESET}"

    # position: snake at col 2, food at col preview_inner - 3
    left_pad = 3
    mid_pad = preview_inner - left_pad - 4 - 2  # 4 for snake, 2 for food
    l2_content = (
        f"{bg_color}{' ' * left_pad}{RESET}"
        f"{snake_demo}"
        f"{bg_color}{' ' * max(0, mid_pad)}{RESET}"
        f"{food_demo}{bg_color}{' ' * 2}{RESET}"
    )
    l2 = (
        f"{wall_color}\u2551{RESET}"
        f"{_pad(l2_content, preview_inner)}"
        f"{wall_color}\u2551{RESET}"
    )
    buf.append(f"    {l2}")

    # line 3: empty
    l3 = (
        f"{wall_color}\u2551{RESET}"
        f"{bg_color}{' ' * preview_inner}{RESET}"
        f"{wall_color}\u2551{RESET}"
    )
    buf.append(f"    {l3}")

    # line 4: wall segment + food legend
    legend = (
        f"{bg_color}  {food_color}\u2605{RESET} "
        f"{FG.WHITE}+10 分{RESET}{bg_color}{RESET}"
    )
    l4 = (
        f"{wall_color}\u2551{RESET}"
        f"{_pad(legend + f'  {snake_head}\u2588{RESET}{FG.WHITE}头{RESET}', preview_inner)}"
        f"{wall_color}\u2551{RESET}"
    )
    buf.append(f"    {l4}")

    # bottom border of preview
    buf.append(
        f"    {bg_color}{wall_color}\u255A{_repeat('\u2550', preview_inner)}"
        f"\u255D{RESET}"
    )
    buf.append("")

    # ── color swatches ──
    swatch_colors = [
        ("墙", colors.get("wall", FG.WHITE)),
        ("头", colors.get("snake_head", FG.GREEN)),
        ("身", colors.get("snake_body", FG.BGRN)),
        ("食物", colors.get("food", FG.RED)),
        ("背景", colors.get("bg", FG.BLACK)),
    ]
    swatch_parts: list[str] = []
    for label, ansi in swatch_colors:
        swatch = f"{ansi}{BOLD}  {label}  {RESET}"
        swatch_parts.append(swatch)
    swatch_line = "  ".join(swatch_parts)
    buf.append(f"    {swatch_line}")
    buf.append("")

    # ── title art preview ──
    title_preview = preview_data.get("title_art")
    if title_preview:
        tp_color = colors.get("title", FG.CYAN)
        for tline in title_preview[:6]:  # show first 6 lines max
            buf.append(f"    {tp_color}{tline}{RESET}")

    buf.append("")

    # ── key bindings ──
    bindings = (
        f"{FG.CYAN}\u2191 \u2193{RESET} 浏览  "
        f"{FG.CYAN}ENTER{RESET} 选择  "
        f"{FG.CYAN}ESC{RESET} 返回"
    )
    buf.append(f"  {_center(bindings, MENU_W)}")

    buf.append(RESET)
    sys.stdout.write("\n".join(buf) + "\n")
    sys.stdout.flush()
