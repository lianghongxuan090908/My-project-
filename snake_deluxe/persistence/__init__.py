"""
Persistence: high-score tracking, game statistics, and save/load.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from snake_deluxe.persistence.save import HighScoreKeeper, StatsKeeper

__all__ = ["HighScoreKeeper", "StatsKeeper", "SaveManager"]

# ── data file (engine format) ──
_DATA_FILE: Path = (
    Path(__file__).resolve().parent.parent / ".snake_deluxe_data.json"
)


class SaveManager:
    """Engine-facing persistence: load/save highscore, stats, leaderboard.

    Wraps the agent-level ``HighScoreKeeper`` / ``StatsKeeper`` classes
    with a simpler dict-based interface for the game engine.
    """

    def __init__(self, filepath: str | None = None) -> None:
        self._path = Path(filepath) if filepath else _DATA_FILE

    def load(self) -> dict[str, Any]:
        """Load saved data. Returns default structure on first run."""
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._defaults()

    def save(self, data: dict[str, Any]) -> None:
        """Atomically write data to JSON."""
        tmp = self._path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        try:
            tmp.replace(self._path)
        except OSError:
            # Fallback for Windows cross-device rename issues
            self._path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _defaults() -> dict[str, Any]:
        return {
            "highscore": 0,
            "stats": {
                "games_played": 0,
                "total_score": 0,
                "high_score": 0,
                "food_eaten": 0,
                "longest_snake": 3,
                "time_played": 0.0,
                "max_combo": 0,
            },
            "leaderboard": [],
        }
