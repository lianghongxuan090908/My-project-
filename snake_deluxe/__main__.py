"""
Snake Deluxe — Entry point.
Run:  python -m snake_deluxe
"""

from snake_deluxe.core.consts import setup_console
from snake_deluxe.core.engine import Game


def main() -> None:
    setup_console()
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
