"""
snake_deluxe.ui — terminal UI rendering for Snake Deluxe.
"""

from snake_deluxe.ui.hud import render_hud, render_hud_border
from snake_deluxe.ui.menu import (
    draw_main_menu,
    draw_pause,
    draw_game_over,
    draw_leaderboard,
    draw_settings,
    draw_stats,
    draw_help,
    draw_theme_browser,
)

__all__ = [
    "render_hud",
    "render_hud_border",
    "draw_main_menu",
    "draw_pause",
    "draw_game_over",
    "draw_leaderboard",
    "draw_settings",
    "draw_stats",
    "draw_help",
    "draw_theme_browser",
]
