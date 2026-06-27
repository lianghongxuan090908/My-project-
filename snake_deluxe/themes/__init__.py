"""
Theme management for snake_deluxe.

Exports:
    ThemeManager — Loads, lists, retrieves, and applies visual themes.
"""

from __future__ import annotations

import os

from snake_deluxe.themes.data import ALL_THEMES


class ThemeManager:
    """Manages the collection of visual themes for the game.

    Usage:
        mgr = ThemeManager()
        mgr.apply("ocean")
        theme = mgr.current  # returns theme dict for "ocean"
        for tid in mgr.list_themes():
            print(mgr.get(tid)["name"])
    """

    # Metadata

    THEME_NAMES: dict[str, str] = {
        tid: info["name"] for tid, info in ALL_THEMES.items()
    }

    # Lifecycle

    def __init__(self) -> None:
        """Initialise the manager with all themes loaded from *data.py*."""
        self._themes: dict[str, dict] = dict(ALL_THEMES)
        self._current_id: str = "classic"

    # Lookup

    def list_themes(self) -> list[str]:
        """Return a sorted list of all available theme IDs."""
        return sorted(self._themes)

    def get(self, theme_id: str) -> dict:
        """Return the theme dict for *theme_id* (raises KeyError if missing)."""
        if theme_id not in self._themes:
            raise KeyError(f"Unknown theme: {theme_id!r}")
        return dict(self._themes[theme_id])

    # Mutation

    def apply(self, theme_id: str) -> None:
        """Set the active theme to *theme_id*.  Raises KeyError if unknown."""
        if theme_id not in self._themes:
            raise KeyError(f"Cannot apply unknown theme: {theme_id!r}")
        self._current_id = theme_id

    # Current theme

    @property
    def current(self) -> dict:
        """The currently active theme dict."""
        return dict(self._themes[self._current_id])

    # Filesystem

    @staticmethod
    def get_theme_path() -> str:
        """Return the absolute path to the themes package directory."""
        return os.path.dirname(os.path.abspath(__file__))