"""
Modes: game mode registry with per-mode configuration.
"""

from snake_deluxe.modes.registry import (
    MODE_CONFIGS,
    get_mode_config,
    mode_iterator,
    is_timed,
    has_maze,
    is_zen,
)

__all__ = [
    "MODE_CONFIGS",
    "get_mode_config",
    "mode_iterator",
    "is_timed",
    "has_maze",
    "is_zen",
]
