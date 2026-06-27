"""
AI module — intelligent snake controllers.

Three core strategies are provided:

  +--------------------+--------------------------------------------------+
  | Class              | Strategy                                         |
  +--------------------+--------------------------------------------------+
  | ``BFS_SnakeAI``    | BFS pathfinder + virtual-snake safety check      |
  | ``SurvivalAI``     | Tail‑chase with starvation escape                |
  | ``HamiltonianAI``  | Hamiltonian‑cycle traversal + shortcuts          |
  +--------------------+--------------------------------------------------+

Usage::

    from snake_deluxe.ai import BFS_SnakeAI, SurvivalAI, HamiltonianAI

    ai = BFS_SnakeAI()
    direction = ai.think(snake, food, W, H, obstacles)
"""

from snake_deluxe.ai.base import BaseAI
from snake_deluxe.ai.bfs import BFS_SnakeAI
from snake_deluxe.ai.survival import SurvivalAI
from snake_deluxe.ai.hamiltonian import HamiltonianAI

__all__ = [
    "BaseAI",
    "BFS_SnakeAI",
    "SurvivalAI",
    "HamiltonianAI",
]
