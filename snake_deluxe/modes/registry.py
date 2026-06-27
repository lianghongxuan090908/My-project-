"""
Mode registry: configuration for every game mode.

Each mode config is a dict with keys:
    wrap           bool — snake wraps around edges
    timer          int or None — countdown duration in seconds
    visible_walls  bool — walls are drawn / visible
    snake_control  bool — player controls the snake
    desc           str — short description
    maze           bool — maze walls are generated
    reverse        bool — controls are reversed periodically
    no_death       bool — snake never dies from walls/self
"""

from typing import Any, Iterator

# ===================================================================
# MODE_CONFIGS
# ===================================================================

MODE_CONFIGS: dict[str, dict[str, Any]] = {
    "classic": {
        "wrap": False,
        "timer": None,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": False,
        "blind": False,
        "desc": (
            "经典贪吃蛇。吃食物，变长，躲避墙壁和自己。"
            "经典街机规则。"
        ),
    },
    "timeattack": {
        "wrap": False,
        "timer": 60,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": False,
        "blind": False,
        "desc": (
            "与时间赛跑！60秒内尽可能获得高分。"
            "每一秒都很关键。"
        ),
    },
    "endless": {
        "wrap": True,
        "timer": None,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": False,
        "blind": False,
        "desc": (
            "没有墙壁！蛇会从边界穿到对面。"
            "唯一的敌人是你自己。"
        ),
    },
    "maze": {
        "wrap": False,
        "timer": None,
        "visible_walls": True,
        "snake_control": True,
        "maze": True,
        "reverse": False,
        "no_death": False,
        "blind": False,
        "desc": (
            "在程序生成的迷宫中穿行。"
            "到处都是墙壁——找到食物！"
        ),
    },
    "reverse": {
        "wrap": False,
        "timer": None,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": True,
        "no_death": False,
        "blind": False,
        "desc": (
            "操作每隔几秒反转一次。"
            "上变成下，左变成右。保持专注！"
        ),
    },
    "blind": {
        "wrap": False,
        "timer": None,
        "visible_walls": False,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": False,
        "blind": True,
        "desc": (
            "墙壁不可见。你只能看到蛇和食物。"
            "相信你的记忆！"
        ),
    },
    "zen": {
        "wrap": False,
        "timer": None,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": True,
        "blind": False,
        "desc": (
            "放松——你不会死。墙壁和尾巴都会穿过你。"
            "无尽的禅意模式。"
        ),
    },
    "speedrun": {
        "wrap": False,
        "timer": 30,
        "visible_walls": True,
        "snake_control": True,
        "maze": False,
        "reverse": False,
        "no_death": False,
        "blind": False,
        "desc": (
            "30秒冲刺。在计时归零前尽可能多地得分！"
        ),
    },
}


# ===================================================================
# Helper functions
# ===================================================================

def get_mode_config(mode_id: str) -> dict[str, Any]:
    """Return a **copy** of the configuration for *mode_id*.

    Raises ``KeyError`` if the mode does not exist.
    """
    if mode_id not in MODE_CONFIGS:
        raise KeyError(
            f"Unknown game mode: {mode_id!r}. "
            f"Available: {', '.join(MODE_CONFIGS)}"
        )
    return dict(MODE_CONFIGS[mode_id])  # shallow copy


def mode_iterator() -> Iterator[str]:
    """Yield every registered mode ID in definition order."""
    return iter(MODE_CONFIGS)


# ── convenience lookup ──

def is_timed(mode_id: str) -> bool:
    """Return True if the mode has a timer."""
    return get_mode_config(mode_id).get("timer") is not None


def has_maze(mode_id: str) -> bool:
    """Return True if the mode uses maze generation."""
    return get_mode_config(mode_id).get("maze", False)


def is_zen(mode_id: str) -> bool:
    """Return True if the mode is no-death (zen)."""
    return get_mode_config(mode_id).get("no_death", False)
