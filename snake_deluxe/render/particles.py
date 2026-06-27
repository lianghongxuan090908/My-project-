"""
Particle system: lightweight visual effects for the terminal snake game.

Provides:
  - ``Particle`` — a single moving point with velocity, gravity, and fade.
  - ``ParticleSystem`` — a manager that emits, updates, and prunes particles.

Particles are rendered by the ``ScreenBuffer`` via the ``get_active()`` dict list.
"""

import math
import random
from typing import Any

from snake_deluxe.core.consts import FG


# ===================================================================
# Particle
# ===================================================================

class Particle:
    """A single particle with position, velocity, lifetime, and colour.

    Each frame the particle:
      1. Moves by (dx, dy).
      2. Has gravity added (dy += 0.05).
      3. Is slowed by air resistance (* 0.98).
      4. Loses one unit of life.

    When ``life`` reaches 0 the particle is considered dead.
    """

    __slots__ = (
        "x", "y", "dx", "dy",
        "life", "max_life",
        "color", "char",
    )

    def __init__(
        self,
        x: float,
        y: float,
        dx: float,
        dy: float,
        life: float,
        max_life: float,
        color: str = "",
        char: str = "*",
    ) -> None:
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.life = life
        self.max_life = max_life
        self.color = color
        self.char = char

    def tick(self) -> None:
        """Advance the particle by one frame."""
        self.x += self.dx
        self.y += self.dy
        # Apply gravity pulling the particle downward
        self.dy += 0.05
        # Air resistance (slight damping so particles slow over time)
        self.dx *= 0.98
        self.dy *= 0.98
        # Decrease remaining lifetime
        self.life -= 1.0

    def alive(self) -> bool:
        """Return ``True`` if the particle still has life remaining."""
        return self.life > 0.0

    # ── alpha / fade helpers ──

    @property
    def progress(self) -> float:
        """Normalised lifetime progress: ``0.0`` = birth, ``1.0`` = death."""
        if self.max_life <= 0:
            return 1.0
        return 1.0 - (self.life / self.max_life)

    @property
    def brightness(self) -> float:
        """Fade curve: full brightness for the first 30 %, then linear fade.

        Returns a value in ``[0.0, 1.0]``.
        """
        p = self.progress
        if p < 0.3:
            return 1.0
        return max(0.0, 1.0 - (p - 0.3) / 0.7)

    def __repr__(self) -> str:
        return (
            f"<Particle ({self.x:.1f},{self.y:.1f}) "
            f"life={self.life:.0f}/{self.max_life:.0f}>"
        )


# ===================================================================
# ParticleSystem
# ===================================================================

class ParticleSystem:
    """Manages a collection of particles with emission and update.

    Typical usage::

        ps = ParticleSystem()
        ps.emit(10, 5, count=12, color=FG.RED, char="*")
        while True:
            ps.tick()
            active = ps.get_active()   # feed to ScreenBuffer
            ...
    """

    def __init__(self) -> None:
        self.particles: list[Particle] = []

    # ── emission ──

    def emit(
        self,
        x: float,
        y: float,
        count: int,
        color: str = "",
        char: str = "*",
        speed: float = 1.0,
    ) -> None:
        """Emit *count* particles from point (x, y) in random directions.

        Each particle receives:
          - Random angle (0 – 2π radians)
          - Velocity between 0.3× and 1.0× **speed**
          - Lifetime between 8 and 20 frames

        Gravity (dy += 0.05 per tick) is applied automatically.

        Args:
            x, y:  Origin point in logical cell coordinates.
            count: Number of particles to spawn.
            color: ANSI colour escape (default bright yellow).
            char:  Display character (default ``"*"``).
            speed: Global speed multiplier (default 1.0).
        """
        if not color:
            color = FG.BYEL

        for _ in range(count):
            angle = random.uniform(0.0, 2.0 * math.pi)
            vel = random.uniform(0.3, 1.0) * speed
            dx = math.cos(angle) * vel
            dy = math.sin(angle) * vel
            life = random.uniform(8.0, 20.0)

            p = Particle(
                x=x,
                y=y,
                dx=dx,
                dy=dy,
                life=life,
                max_life=life,
                color=color,
                char=char,
            )
            self.particles.append(p)

    # ── emission presets ──

    def emit_fountain(
        self,
        x: float,
        y: float,
        count: int,
        color: str = "",
        char: str = "\u25CF",
    ) -> None:
        """Emit particles shooting upward (fountain effect).

        Angles cluster around [-π, 0] (upward) with narrower spread
        and higher initial velocity than the generic ``emit``.
        """
        if not color:
            color = FG.CYAN

        for _ in range(count):
            angle = random.uniform(math.pi * 0.6, math.pi * 1.4)
            vel = random.uniform(1.0, 2.5)
            dx = math.cos(angle) * vel
            dy = math.sin(angle) * vel - 0.5  # extra upward kick
            life = random.uniform(12.0, 28.0)
            self.particles.append(Particle(
                x=x, y=y, dx=dx, dy=dy,
                life=life, max_life=life,
                color=color, char=char,
            ))

    def emit_explosion(
        self,
        x: float,
        y: float,
        color: str = "",
        char: str = "\u2605",
    ) -> None:
        """A quick burst of 20 particles for death / collision effects."""
        self.emit(x, y, count=20, color=color or FG.RED, char=char, speed=2.0)

    def emit_trail(
        self,
        x: float,
        y: float,
        color: str = "",
        char: str = "\u00B7",
    ) -> None:
        """A single lingering particle for tail / movement trails."""
        if not color:
            color = FG.GREEN
        p = Particle(
            x=x, y=y,
            dx=random.uniform(-0.1, 0.1),
            dy=random.uniform(-0.1, 0.1),
            life=6.0, max_life=6.0,
            color=color, char=char,
        )
        self.particles.append(p)

    # ── update ──

    def tick(self) -> None:
        """Advance all particles by one frame and remove dead ones."""
        for p in self.particles:
            p.tick()
        self.particles = [p for p in self.particles if p.alive()]

    # ── queries ──

    def count(self) -> int:
        """Return the number of currently active particles."""
        return len(self.particles)

    def get_active(self) -> list[dict[str, Any]]:
        """Return a list of dicts suitable for the ``ScreenBuffer``.

        Each dict contains::

            {"x": int, "y": int, "char": str,
             "color": str, "brightness": float}

        Particles whose ``brightness`` is below 0.05 are omitted.
        """
        result: list[dict[str, Any]] = []
        for p in self.particles:
            if p.brightness < 0.05:
                continue
            result.append({
                "x": round(p.x),
                "y": round(p.y),
                "char": p.char,
                "color": p.color,
                "brightness": p.brightness,
            })
        return result

    def clear(self) -> None:
        """Remove all particles immediately."""
        self.particles.clear()

    def __repr__(self) -> str:
        return f"<ParticleSystem count={len(self.particles)}>"
