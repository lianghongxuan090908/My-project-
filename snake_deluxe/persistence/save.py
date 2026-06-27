"""
Persistence: high-score tracking and game statistics stored as JSON.

File location: project-root/.snake_deluxe_data.json

Architecture:
  - ``HighScoreKeeper`` manages per-difficulty, per-mode leaderboards (top 5).
  - ``StatsKeeper`` tracks aggregate stats (games played, total score, etc.)
    and auto-detects achievement unlocks.
  - Data is read/written with ``json.load`` / ``json.dump`` (UTF-8).
  - Writes are atomic via a temp-file rename pattern.
"""

import json
from pathlib import Path
from typing import Any

from snake_deluxe.core.consts import DIFFICULTIES, GAME_MODES

# ── data file path ──
DATA_FILE: Path = (
    Path(__file__).resolve().parent.parent.parent / ".snake_deluxe_data.json"
)


# ── internal helpers ──

def _key(diff: str, mode: str) -> str:
    """Build a flat storage key from difficulty and mode names.

    Example: ``("Easy", "classic")`` → ``"Easy_classic"``
    """
    return f"{diff}_{mode}"


def _load() -> dict[str, Any]:
    """Load the full JSON data file.

    Returns an empty structure (with default stats) on first run or
    when the file is missing / corrupted.
    """
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, Any]) -> None:
    """Atomically write the data dict to JSON.

    Writes to a ``.json.tmp`` sibling first, then renames over the
    real file, so a crash in the middle never corrupts the save data.
    """
    tmp = DATA_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(DATA_FILE)


def _init_data() -> dict[str, Any]:
    """Return a fresh data dictionary with zeroed stats."""
    return {
        "_stats": {
            "gp": 0,   # games played
            "tf": 0,   # total food eaten
            "ts": 0,   # total score accumulated
            "lg": 0,   # longest game duration (seconds)
            "mc": 0,   # max combo reached
            "ach": [], # unlocked achievement IDs
        }
    }


# ===================================================================
# HighScoreKeeper
# ===================================================================

class HighScoreKeeper:
    """Manages per-difficulty, per-mode high-score leaderboards (top 5).

    Each board is stored as a sorted list of up to 5 integers
    (descending).  Zeros fill unused slots.

    Usage::

        keeper = HighScoreKeeper()
        is_best = keeper.submit("Easy", "classic", 150)
        top = keeper.get_top("Normal", "timeattack")
        board = keeper.get_board("Hard", "maze")
        keeper.reset_all()
    """

    # ── public API ──

    @staticmethod
    def submit(diff: str, mode: str, score: int) -> bool:
        """Submit a score for a difficulty/mode combination.

        Args:
            diff:  Difficulty name (e.g. ``"Easy"``).
            mode:  Game mode id (e.g. ``"classic"``).
            score: Integer score to record.

        Returns:
            ``True`` if **score** is a new #1 (personal best).
        """
        data = _load()
        k = _key(diff, mode)

        board: list[int] = data.get(k, [0, 0, 0, 0, 0])
        while len(board) < 5:
            board.append(0)

        is_new_record = score > board[0]

        board.append(score)
        board.sort(reverse=True)
        board = board[:5]
        data[k] = board

        _save(data)
        return is_new_record

    @staticmethod
    def get_top(diff: str, mode: str) -> int:
        """Return the highest score for the given diff/mode.

        Returns 0 when no score has ever been recorded.
        """
        data = _load()
        board: list[int] = data.get(_key(diff, mode), [0])
        return board[0] if board else 0

    @staticmethod
    def get_board(diff: str, mode: str) -> list[int]:
        """Return the top-5 leaderboard (sorted descending).

        Unused slots are filled with 0.
        """
        data = _load()
        board: list[int] = data.get(_key(diff, mode), [0, 0, 0, 0, 0])
        while len(board) < 5:
            board.append(0)
        return board[:5]

    @staticmethod
    def reset_all() -> None:
        """Wipe all high-score entries.

        Aggregate stats are preserved so the player doesn't lose
        their total play-count or achievements.
        """
        data = _load()
        stats = data.get("_stats", _init_data()["_stats"])
        fresh = _init_data()
        fresh["_stats"] = stats
        _save(fresh)

    @staticmethod
    def reset_difficulty(diff: str) -> None:
        """Reset all mode scores for a single difficulty.

        Args:
            diff: Difficulty name (e.g. ``"Easy"``).
        """
        data = _load()
        for mode in GAME_MODES:
            data.pop(_key(diff, mode), None)
        _save(data)

    @staticmethod
    def get_all_boards() -> dict[str, list[int]]:
        """Return a dict of every non-stat entry in the data file."""
        data = _load()
        return {k: v for k, v in data.items() if k != "_stats"}

    @staticmethod
    def migrate_v1() -> None:
        """Migrate legacy data format (Chinese difficulty names) to English.

        Legacy keys like ``"简单_normal"`` are renamed to
        ``"Easy_normal"``.  The old keys are removed after migration.
        """
        legacy_map: dict[str, str] = {
            "简单": "Easy",
            "普通": "Normal",
            "困难": "Hard",
        }
        data = _load()
        changed = False
        for old_key in list(data.keys()):
            if old_key == "_stats":
                continue
            for ch, en in legacy_map.items():
                if old_key.startswith(ch + "_"):
                    suffix = old_key[len(ch) + 1:]
                    new_key = _key(en, suffix)
                    if new_key not in data:
                        data[new_key] = data.pop(old_key)
                        changed = True
                    break
        if changed:
            _save(data)


# ===================================================================
# StatsKeeper
# ===================================================================

class StatsKeeper:
    """Tracks aggregate game statistics and achievement unlocking.

    Achievements are auto-detected when ``record_game`` is called
    and persisted under the ``"ach"`` key in the stats dict.

    Achievement catalogue::

        score_100     score >= 100     Reach 100 points
        score_300     score >= 300     Reach 300 points
        score_500     score >= 500     Reach 500 points
        combo_3       combo >= 3       Achieve a 3x combo
        combo_5       combo >= 5       Achieve a 5x combo
        combo_10      combo >= 10      Achieve a 10x combo
        feast_20      food >= 20       Eat 20 food items
        speed_demon   (custom)         Score 200+ in ≤30 s
        marathon      duration >= 120  Survive 2 minutes
        survivor      duration >= 300  Survive 5 minutes
    """

    _ACHIEVEMENTS: dict[str, tuple[str, Any, Any]] = {
        "score_100":  ("score", 100, None),
        "score_300":  ("score", 300, None),
        "score_500":  ("score", 500, None),
        "combo_3":    ("combo", 3,   None),
        "combo_5":    ("combo", 5,   None),
        "combo_10":   ("combo", 10,  None),
        "feast_20":   ("food",  20,  None),
        "speed_demon":("speed", None, None),
        "marathon":   ("duration", 120, None),
        "survivor":   ("duration", 300, None),
    }

    # ── public API ──

    @staticmethod
    def record_game(
        score: int,
        food: int,
        duration: float,
        combo: int,
    ) -> None:
        """Record one completed game and check for new achievements.

        Args:
            score:    Final score of the game.
            food:     Total food items eaten.
            duration: Game length in seconds (float).
            combo:    Maximum combo reached.
        """
        data = _load()
        stats: dict = data.get("_stats", _init_data()["_stats"])

        stats["gp"] += 1
        stats["tf"] += food
        stats["ts"] += score
        if duration > stats["lg"]:
            stats["lg"] = int(duration)
        if combo > stats["mc"]:
            stats["mc"] = combo

        # ── achievement checks ──
        existing: set[str] = set(stats.get("ach", []))
        achieved: set[str] = set(existing)

        for ach_id, (kind, threshold, _) in StatsKeeper._ACHIEVEMENTS.items():
            if ach_id in existing:
                continue
            if kind == "score" and score >= threshold:
                achieved.add(ach_id)
            elif kind == "combo" and combo >= threshold:
                achieved.add(ach_id)
            elif kind == "food" and food >= threshold:
                achieved.add(ach_id)
            elif kind == "duration" and duration >= threshold:
                achieved.add(ach_id)
            elif kind == "speed":
                if score >= 200 and duration <= 30:
                    achieved.add(ach_id)

        stats["ach"] = sorted(achieved)
        data["_stats"] = stats
        _save(data)

    @staticmethod
    def get_dict() -> dict[str, Any]:
        """Return the stats dictionary for display or HUD use.

        Guaranteed keys: ``gp``, ``tf``, ``ts``, ``lg``, ``mc``, ``ach``.
        """
        data = _load()
        return data.get("_stats", _init_data()["_stats"])

    @staticmethod
    def reset() -> None:
        """Reset all stats and high scores to factory defaults."""
        _save(_init_data())

    @property
    def achievements(self) -> set[str]:
        """Return the set of currently unlocked achievement IDs.

        This is a live property that re-reads from disk each time.
        """
        stats = self.get_dict()
        return set(stats.get("ach", []))

    @staticmethod
    def achievement_label(ach_id: str) -> str:
        """Return a human-readable label for an achievement ID."""
        labels: dict[str, str] = {
            "score_100":  "100分",
            "score_300":  "300分",
            "score_500":  "500分",
            "combo_3":    "3x连击",
            "combo_5":    "5x连击",
            "combo_10":   "10x连击",
            "feast_20":   "大餐 (20个食物)",
            "speed_demon":"极速达人",
            "marathon":   "马拉松 (2分钟)",
            "survivor":   "生存者 (5分钟)",
        }
        return labels.get(ach_id, ach_id)

    @staticmethod
    def achievement_description(ach_id: str) -> str:
        """Return a short description for an achievement ID."""
        descs: dict[str, str] = {
            "score_100":  "单局达到100分。",
            "score_300":  "单局达到300分。",
            "score_500":  "单局达到500分。",
            "combo_3":    "达成3连击。",
            "combo_5":    "达成5连击。",
            "combo_10":   "达成10连击。",
            "feast_20":   "单局吃掉20个食物。",
            "speed_demon":"30秒内获得200+分。",
            "marathon":   "存活2分钟。",
            "survivor":   "存活5分钟。",
        }
        return descs.get(ach_id, "")

    @staticmethod
    def get_summary() -> str:
        """Return a one-line summary of current stats."""
        s = StatsKeeper.get_dict()
        return (
            f"{s['gp']} 局 | {s['tf']} 食物 | "
            f"{s['ts']} 总分 | {len(s['ach'])} 成就"
        )

    def __repr__(self) -> str:
        stats = self.get_dict()
        return (
            f"<StatsKeeper games={stats['gp']} "
            f"total_score={stats['ts']} "
            f"achievements={len(stats['ach'])}>"
        )
