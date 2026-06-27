"""
Maps: procedural maze generation, obstacle placement, and presets.
"""

from snake_deluxe.maps.generator import (
    MazeGenerator,
    add_obstacles,
    generate_borders,
    preset_cross,
    preset_rings,
    preset_checkerboard,
)

__all__ = [
    "MazeGenerator",
    "add_obstacles",
    "generate_borders",
    "preset_cross",
    "preset_rings",
    "preset_checkerboard",
]
