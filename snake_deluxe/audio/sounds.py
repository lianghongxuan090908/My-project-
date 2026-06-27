"""
Sound manager: terminal beeps via winsound.Beep (Windows) or '\a' (other OS).
All sounds run in a background thread so the game loop never blocks.

Architecture:
  - Each public ``play_*`` method schedules one or more beeps via daemon threads.
  - The ``_play_async`` helper dispatches a single frequency/duration pair.
  - A threading.Lock protects the enabled flag for thread-safe toggling.
  - On non-Windows platforms all sounds degrade to the terminal bell character.
"""

import os
import sys
import threading
from snake_deluxe.core.consts import DIFFICULTIES, GAME_MODES

# ── platform detection ──
_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    import winsound


def _beep_win(freq: int, dur: int) -> None:
    """Play a beep on Windows via the winsound.Beep API.

    Args:
        freq: Frequency in Hertz (37 – 32767).
        dur:  Duration in milliseconds.
    """
    winsound.Beep(freq, dur)


def _beep_fallback(freq: int, dur: int) -> None:
    """Fallback: print the ASCII bell character to stdout.

    This produces a system-dependent alert sound on Linux, macOS, etc.
    The frequency and duration parameters are ignored.
    """
    sys.stdout.write("\a")
    sys.stdout.flush()


_BEEP = _beep_win if _IS_WINDOWS else _beep_fallback


# ===================================================================
# SoundManager
# ===================================================================

class SoundManager:
    """Manages game sound effects via non-blocking beep threads.

    Usage::

        sm = SoundManager(enabled=True)
        sm.play_eat()
        sm.toggle()
        if sm.enabled:
            sm.play_game_start()

    All sound methods return immediately — the actual ``Beep`` call
    runs in a **daemon thread** so the game loop is never blocked.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = bool(enabled)
        self._lock = threading.Lock()

    # ── public property ──

    @property
    def enabled(self) -> bool:
        """Whether sounds are currently enabled (read-only)."""
        return self._enabled

    # ── internal helpers ──

    @staticmethod
    def _play_async(freq: int, dur: int) -> None:
        """Run a single beep in a new daemon thread.

        Daemon threads are automatically terminated when the main
        process exits, so no explicit cleanup is needed.
        """
        t = threading.Thread(target=_BEEP, args=(freq, dur), daemon=True)
        t.start()

    def _beep(self, freq: int, dur: int) -> None:
        """Conditionally play a beep — only fires when ``enabled``."""
        if self._enabled:
            self._play_async(freq, dur)

    # ── public sound API ──

    def play_eat(self) -> None:
        """Ascending beep: 800 → 1200 Hz, total ~120 ms.

        Two overlapping notes simulate a short rising chirp.
        """
        self._beep(800, 60)
        _ascend = threading.Thread(
            target=_BEEP, args=(1200, 60), daemon=True
        )
        _ascend.start()

    def play_die(self) -> None:
        """Descending sad beep: 400 → 200 Hz, total ~300 ms.

        Two overlapping notes simulate a falling "womp womp".
        """
        self._beep(400, 150)
        _descend = threading.Thread(
            target=_BEEP, args=(200, 150), daemon=True
        )
        _descend.start()

    def play_combo(self, level: int) -> None:
        """Higher-pitched beep for higher combo levels.

        The frequency climbs by 200 Hz per combo level
        (base = 1000 Hz) while the duration shortens slightly
        to reflect increasing urgency.

        Args:
            level: Current combo streak (>= 1).
        """
        freq = min(1000 + level * 200, 3000)  # cap at 3 kHz
        dur = max(80 - level * 5, 30)          # floor at 30 ms
        self._beep(freq, dur)

    def play_menu_click(self) -> None:
        """Short click at 600 Hz, 30 ms — for UI navigation."""
        self._beep(600, 30)

    def play_new_record(self) -> None:
        """Fanfare sequence: C5 → E5 → G5 → C6 (523 → 659 → 784 → 1047 Hz).

        Each note is played in its own thread for parallel overlap,
        giving a rich chord-like effect.
        """
        notes = [
            (523, 120),   # C5
            (659, 120),   # E5
            (784, 120),   # G5
            (1047, 200),  # C6 (final note held longer)
        ]
        for freq, dur in notes:
            t = threading.Thread(target=_BEEP, args=(freq, dur), daemon=True)
            t.start()

    def play_countdown(self) -> None:
        """Sharp tick at 900 Hz, 50 ms — used for the last 5 seconds of
        time-attack mode.  A single, percussive beep.
        """
        self._beep(900, 50)

    def play_game_start(self) -> None:
        """Short intro: two quick beeps (A4=440 Hz, A5=880 Hz).

        The two notes overlap slightly for a bright "da-ding!" feel.
        """
        t1 = threading.Thread(target=_BEEP, args=(440, 80), daemon=True)
        t2 = threading.Thread(target=_BEEP, args=(880, 80), daemon=True)
        t1.start()
        t2.start()

    def play_level_up(self) -> None:
        """Three ascending beeps: 400 → 600 → 800 Hz.

        Used when the snake reaches a milestone length or the
        game difficulty tier increases.
        """
        for freq in (400, 600, 800):
            t = threading.Thread(target=_BEEP, args=(freq, 100), daemon=True)
            t.start()

    def play_warning(self) -> None:
        """Urgent double-beep: 1000 Hz twice — for low-time warnings."""
        for _ in range(2):
            t = threading.Thread(target=_BEEP, args=(1000, 80), daemon=True)
            t.start()

    def play_pause(self) -> None:
        """Soft low beep (300 Hz, 100 ms) when the game is paused."""
        self._beep(300, 100)

    def play_unpause(self) -> None:
        """Short medium beep (700 Hz, 60 ms) when the game resumes."""
        self._beep(700, 60)

    # ── state management ──

    def toggle(self) -> None:
        """Flip the enabled flag.

        Thread-safe via an internal lock.  After calling this
        method, check ``.enabled`` to determine the new state.
        """
        with self._lock:
            self._enabled = not self._enabled

    def enable(self) -> None:
        """Force-enable sound output."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Force-disable sound output."""
        with self._lock:
            self._enabled = False

    def play_achievement(self) -> None:
        """Celebration jingle: two ascending pairs (400→800, 500→1000 Hz).

        A short "ding-ding!" that signifies an achievement unlock.
        """
        for base in (400, 500):
            t1 = threading.Thread(target=_BEEP, args=(base, 80), daemon=True)
            t2 = threading.Thread(target=_BEEP, args=(base * 2, 80), daemon=True)
            t1.start()
            t2.start()

    def __repr__(self) -> str:
        return f"<SoundManager enabled={self._enabled}>"
