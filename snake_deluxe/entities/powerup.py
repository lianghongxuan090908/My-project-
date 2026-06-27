"""
Power-up system — special items with timed effects on the snake or game state.

Each power-up type has:
    - A display character and colour
    - A duration (in game ticks) or INSTANT for one-shot effects
    - An ``apply()`` callback and an ``expire()`` callback

Architecture:
    PowerUpManager owns the list of active power-ups on the board and the
    set of currently-active timed effects.  One ``tick()`` call per game
    frame decays durations and removes expired effects.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Optional

from snake_deluxe.core.consts import FG, BOLD, RESET, CSI

# ── effect duration constants (in game ticks) ──
INSTANT = 0
SHORT = 50
MEDIUM = 120
LONG = 250

# ── colour helper for 256-color extras ──
_C = lambda n: f"{CSI}38;5;{n}m"

# ===================================================================
# PowerUpType
# ===================================================================


class PowerUpType:
    """Descriptor for one kind of power-up."""

    __slots__ = (
        "name", "ch", "color", "duration", "weight", "desc",
        "_apply", "_expire",
    )

    def __init__(
        self,
        name: str,
        ch: str,
        color: str,
        duration: int,
        weight: float = 1.0,
        desc: str = "",
        apply: Optional[Callable] = None,
        expire: Optional[Callable] = None,
    ) -> None:
        self.name = name
        self.ch = ch
        self.color = color
        self.duration = duration
        self.weight = weight
        self.desc = desc
        self._apply = apply
        self._expire = expire

    def apply(self, game_state: dict) -> None:
        """Apply the effect.  *game_state* is a mutable dict the engine
        passes in so the effect can modify speed / score multipliers etc."""
        if self._apply:
            self._apply(game_state)

    def expire(self, game_state: dict) -> None:
        """Revert the effect."""
        if self._expire:
            self._expire(game_state)

    def __repr__(self) -> str:
        return f"<PowerUp {self.name} dur={self.duration}>"


# ===================================================================
# Built-in power-up definitions
# ===================================================================


def _apply_speed(gs: dict) -> None:
    gs["_speed_factor"] = gs.get("_speed_factor", 1.0) * 1.5
    gs["_msg"] = "⚡ 加速！"
    gs["_msg_ttl"] = 3.0


def _expire_speed(gs: dict) -> None:
    gs["_speed_factor"] = max(0.5, gs.get("_speed_factor", 1.0) / 1.5)


def _apply_invincible(gs: dict) -> None:
    gs["_invincible"] = True
    gs["_msg"] = "🛡 无敌！"
    gs["_msg_ttl"] = 3.0


def _expire_invincible(gs: dict) -> None:
    gs["_invincible"] = False


def _apply_double(gs: dict) -> None:
    gs["_score_mult"] = gs.get("_score_mult", 1.0) * 2.0
    gs["_msg"] = "✖ 双倍分数！"
    gs["_msg_ttl"] = 3.0


def _expire_double(gs: dict) -> None:
    gs["_score_mult"] = max(1.0, gs.get("_score_mult", 1.0) / 2.0)


def _apply_magnet(gs: dict) -> None:
    gs["_magnet"] = True
    gs["_magnet_range"] = 3
    gs["_msg"] = "🧲 磁铁！"
    gs["_msg_ttl"] = 3.0


def _expire_magnet(gs: dict) -> None:
    gs["_magnet"] = False


def _apply_ghost(gs: dict) -> None:
    gs["_ghost"] = True
    gs["_msg"] = "👻 穿墙模式！"
    gs["_msg_ttl"] = 3.0


def _expire_ghost(gs: dict) -> None:
    gs["_ghost"] = False


def _apply_shrink(gs: dict) -> None:
    """Instant: remove 3 segments from the snake."""
    gs["_shrink"] = 3
    gs["_msg"] = "🐍 缩小！"
    gs["_msg_ttl"] = 2.0


def _apply_grow(gs: dict) -> None:
    """Instant: grow the snake by 3 segments."""
    gs["_grow_extra"] = gs.get("_grow_extra", 0) + 3
    gs["_msg"] = "📏 变长！"
    gs["_msg_ttl"] = 2.0


def _apply_freeze(gs: dict) -> None:
    """Freeze: food stops moving (only relevant in modes with moving food)."""
    gs["_food_frozen"] = True
    gs["_msg"] = "❄️ 冻结！"
    gs["_msg_ttl"] = 2.0


POWERUP_DEFS: list[PowerUpType] = [
    PowerUpType(
        "加速", "⚡", FG.BYEL, MEDIUM, weight=0.18,
        desc="蛇移动速度加快1.5倍",
        apply=_apply_speed, expire=_expire_speed,
    ),
    PowerUpType(
        "无敌", "🛡", FG.BCYN, SHORT, weight=0.15,
        desc="穿过墙壁和自己",
        apply=_apply_invincible, expire=_expire_invincible,
    ),
    PowerUpType(
        "双倍分数", "✖", FG.BRED, MEDIUM, weight=0.14,
        desc="食物得分翻倍",
        apply=_apply_double, expire=_expire_double,
    ),
    PowerUpType(
        "磁铁", "🧲", FG.BMAG, MEDIUM, weight=0.12,
        desc="食物被吸引向你",
        apply=_apply_magnet, expire=_expire_magnet,
    ),
    PowerUpType(
        "穿墙", "👻", _C(105), SHORT, weight=0.10,
        desc="穿过障碍物",
        apply=_apply_ghost, expire=_expire_ghost,
    ),
    PowerUpType(
        "缩小", "🔽", FG.GREEN, INSTANT, weight=0.10,
        desc="蛇减少3节",
        apply=_apply_shrink,
    ),
    PowerUpType(
        "变长", "🔼", FG.MAGENTA, INSTANT, weight=0.08,
        desc="蛇增加3节",
        apply=_apply_grow,
    ),
    PowerUpType(
        "冻结", "❄️", _C(81), SHORT, weight=0.08,
        desc="食物停止移动",
        apply=_apply_freeze,
    ),
    PowerUpType(
        "慢动作", "🐢", _C(130), MEDIUM, weight=0.05,
        desc="蛇移动速度减慢0.6倍",
        apply=lambda gs: (
            gs.__setitem__("_speed_factor", max(0.1, gs.get("_speed_factor", 1.0) * 0.6))
            or gs.__setitem__("_msg", "🐢 慢动作！") or gs.__setitem__("_msg_ttl", 3.0)
        ),
        expire=lambda gs: gs.__setitem__(
            "_speed_factor", min(3.0, gs.get("_speed_factor", 1.0) / 0.6)
        ),
    ),
]

# Weighted random selection helper
_POWERUP_WEIGHTS = [p.weight for p in POWERUP_DEFS]


def random_powerup_type() -> PowerUpType:
    """Pick a random power-up type weighted by each type's rarity."""
    r = random.random()
    cumulative = 0.0
    for p in POWERUP_DEFS:
        cumulative += p.weight
        if r < cumulative:
            return p
    return POWERUP_DEFS[-1]


# ===================================================================
# ActivePowerUp (instance on the board)
# ===================================================================


class ActivePowerUp:
    """A power-up item sitting on the board waiting to be collected."""

    __slots__ = ("pos", "ptype", "ticks_left")

    def __init__(self, pos: tuple[int, int], ptype: PowerUpType) -> None:
        self.pos = pos
        self.ptype = ptype
        self.ticks_left: int = 300  # despawn after 300 ticks if not collected

    @property
    def ch(self) -> str:
        return self.ptype.ch

    @property
    def color(self) -> str:
        return self.ptype.color

    def tick(self) -> bool:
        """Decay despawn timer.  Returns True if still alive."""
        self.ticks_left -= 1
        return self.ticks_left > 0


# ===================================================================
# ActiveEffect (timed effect on the snake)
# ===================================================================


class ActiveEffect:
    """A timed effect currently applied to the game state."""

    __slots__ = ("ptype", "remaining")

    def __init__(self, ptype: PowerUpType, duration: int) -> None:
        self.ptype = ptype
        self.remaining = duration

    def tick(self) -> bool:
        """Decay.  Returns True while still active."""
        self.remaining -= 1
        return self.remaining > 0

    @property
    def name(self) -> str:
        return self.ptype.name


# ===================================================================
# PowerUpManager
# ===================================================================


class PowerUpManager:
    """Manages power-up spawning, collection, and active effect tracking.

    Typical usage::

        mgr = PowerUpManager()
        mgr.spawn_random(occupied, w, h)
        for pu in mgr.board_items:
            draw(pu.pos, pu.ch, pu.color)
        if snake.head in [pu.pos for pu in mgr.board_items]:
            mgr.collect(snake.head, game_state)
        mgr.tick(game_state)
        expired = mgr.get_expired()
        for e in expired:
            e.ptype.expire(game_state)
    """

    def __init__(self) -> None:
        self.board_items: list[ActivePowerUp] = []
        self.active_effects: list[ActiveEffect] = []
        self._spawn_cooldown: int = 0
        self._max_on_board: int = 3

    # ── spawning ──

    def spawn_random(
        self,
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
    ) -> bool:
        """Place one random power-up on a free cell.  No-op if board full
        or already at max items."""
        if len(self.board_items) >= self._max_on_board:
            return False
        free = [
            (x, y) for x in range(1, W - 1) for y in range(1, H - 1)
            if (x, y) not in occupied
        ]
        if not free:
            return False
        pos = random.choice(free)
        ptype = random_powerup_type()
        self.board_items.append(ActivePowerUp(pos, ptype))
        return True

    def spawn_near(
        self,
        near: tuple[int, int],
        occupied: set[tuple[int, int]],
        W: int,
        H: int,
        radius: int = 5,
    ) -> bool:
        """Spawn a power-up near a position (e.g. near the snake)."""
        if len(self.board_items) >= self._max_on_board:
            return False
        cx, cy = near
        candidates = [
            (x, y) for x in range(max(1, cx - radius), min(W - 1, cx + radius + 1))
            for y in range(max(1, cy - radius), min(H - 1, cy + radius + 1))
            if (x, y) not in occupied
        ]
        if not candidates:
            return self.spawn_random(occupied, W, H)
        pos = random.choice(candidates)
        ptype = random_powerup_type()
        self.board_items.append(ActivePowerUp(pos, ptype))
        return True

    # ── collection ──

    def collect(self, pos: tuple[int, int], game_state: dict) -> Optional[PowerUpType]:
        """Collect a power-up at *pos*.  Returns the type if one was found."""
        for i, pu in enumerate(self.board_items):
            if pu.pos == pos:
                ptype = pu.ptype
                self.board_items.pop(i)

                # Apply instant effects immediately
                if ptype.duration == INSTANT:
                    ptype.apply(game_state)
                else:
                    ptype.apply(game_state)
                    self.active_effects.append(ActiveEffect(ptype, ptype.duration))
                return ptype
        return None

    # ── per-tick updates ──

    def tick(self, game_state: dict) -> list[PowerUpType]:
        """Called every game tick.  Returns list of *expired* effect types."""
        # Decay board items
        self.board_items = [pu for pu in self.board_items if pu.tick()]

        # Decay active effects
        expired: list[PowerUpType] = []
        surviving: list[ActiveEffect] = []
        for ef in self.active_effects:
            if not ef.tick():
                expired.append(ef.ptype)
                ef.ptype.expire(game_state)
            else:
                surviving.append(ef)
        self.active_effects = surviving

        # Cooldown before next spawn
        if self._spawn_cooldown > 0:
            self._spawn_cooldown -= 1

        return expired

    # ── queries ──

    def has_effect(self, name: str) -> bool:
        """Check if a named effect is currently active."""
        return any(ef.name == name for ef in self.active_effects)

    def active_names(self) -> list[str]:
        """Return names of all active effects."""
        return [ef.name for ef in self.active_effects]

    def reset(self) -> None:
        """Full reset for new game."""
        self.board_items.clear()
        self.active_effects.clear()
        self._spawn_cooldown = 0

    # ── serialization ──

    def to_dict(self) -> dict:
        return {
            "board": [(p.pos, p.ptype.name, p.ticks_left) for p in self.board_items],
            "effects": [(e.ptype.name, e.remaining) for e in self.active_effects],
        }

    def __repr__(self) -> str:
        return (
            f"<PowerUpManager board={len(self.board_items)} "
            f"effects={len(self.active_effects)}>"
        )
