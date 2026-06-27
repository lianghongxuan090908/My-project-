"""
Main game engine — orchestrates gameplay, menus, rendering, and state machine.
"""

from __future__ import annotations

import importlib
import os
import random
import sys
import time
from typing import Any, Optional

from snake_deluxe.core.consts import (
    CLS, HOME, HIDE_CURSOR, SHOW_CURSOR, BOLD, RESET, FG,
    UP, DOWN, LEFT, RIGHT, ALL_DIRS, OPPOSITE,
    DIFFICULTIES, GAME_MODES, MODE_LABELS,
)
from snake_deluxe.core.timing import GameTimer
from snake_deluxe.core.input import InputHandler
from snake_deluxe.core.input import (
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_PAUSE, ACTION_RESTART, ACTION_QUIT, ACTION_ENTER,
    ACTION_MENU, ACTION_STATS, ACTION_LEADER, ACTION_THEME,
    ACTION_NONE,
)
from snake_deluxe.modes.registry import MODE_CONFIGS
from snake_deluxe.entities.snake import Snake
from snake_deluxe.entities.food import Food
from snake_deluxe.entities.powerup import PowerUpManager
from snake_deluxe.themes import ThemeManager
from snake_deluxe.ui import (
    render_hud,
    draw_main_menu, draw_pause, draw_game_over,
    draw_leaderboard, draw_settings, draw_stats,
    draw_help, draw_theme_browser,
)

# ── Lazy module loaders (modules built by async agents) ──

_MODULE_CACHE: dict[str, Any] = {}


def _lazy_mod(name: str) -> Any:
    """Import a module once, return None on failure."""
    if name not in _MODULE_CACHE:
        try:
            _MODULE_CACHE[name] = importlib.import_module(name)
        except (ImportError, ModuleNotFoundError):
            _MODULE_CACHE[name] = None
    return _MODULE_CACHE[name]


def _get_class(mod_name: str, cls_name: str) -> Optional[type]:
    mod = _lazy_mod(mod_name)
    return getattr(mod, cls_name, None) if mod else None


# ── Application ──


class Game:
    """Main application — owns the state machine and all sub-systems."""

    # ── State constants ──
    S_MENU = "MENU"
    S_PLAYING = "PLAYING"
    S_PAUSED = "PAUSED"
    S_GAMEOVER = "GAMEOVER"
    S_SETTINGS = "SETTINGS"
    S_LEADERBOARD = "LEADERBOARD"
    S_STATS = "STATS"
    S_HELP = "HELP"
    S_THEME = "THEME"

    # ── Construction ──

    def __init__(self) -> None:
        self.running = True
        self.state = self.S_MENU
        self.frame = 0

        # Core sub-systems
        self.theme_mgr = ThemeManager()
        self.input = InputHandler()
        self.timer = GameTimer()

        # Current theme (lazy-refreshed via _apply_theme())
        self._theme_id: str = "classic"
        self._theme: dict[str, Any] = self.theme_mgr.current

        # Game config
        self._diff_keys: list[str] = list(DIFFICULTIES.keys())
        self._diff_idx: int = 1                       # "Normal"
        self._mode_idx: int = 0                       # "classic"
        self._ai_enabled: bool = False
        self._sound_on: bool = True
        self._menu_frame: int = 0

        # In-game objects (re-created by _start_game)
        self.snake: Optional[Snake] = None
        self.food: Optional[Food] = None
        self.obstacles: set[tuple[int, int]] = set()
        self.w: int = 22
        self.h: int = 16

        # Score / statistics
        self.score: int = 0
        self.highscore: int = 0
        self.combo: int = 0
        self.combo_timer: float = 0.0
        self._msg: str = ""
        self._msg_ttl: float = 0.0
        self._timer_paused: bool = False
        self.time_remaining: int = 0
        self._speed_factor: float = 1.0

        # Reverse mode state
        self._reversed: bool = False
        self._reverse_flip_frame: int = 0

        # Blind mode state
        self._blind_radius: int = 3

        # Player stats
        self.stats: dict[str, Any] = self._default_stats()

        # Optional sub-systems
        self._sound_mgr: Any = None
        self._save_mgr: Any = None
        self._ai: Any = None
        self._particles: Any = None
        self._init_optional_modules()

        # Power-ups
        self._powerups = PowerUpManager()
        self._invincible = False
        self._ghost = False
        self._score_mult = 1.0
        self._shrink_pending = 0
        self._grow_extra = 0
        self._food_frozen = False

        # Leaderboard (in-memory + possibly saved)
        self._lb_entries: list[tuple[int, str, str]] = []
        self._lb_last_diff: str = ""
        self._lb_last_mode: str = ""

        # Theme browser state
        self._tb_idx: int = 0

    # ── Initialisation helpers ──

    def _default_stats(self) -> dict[str, Any]:
        return {
            "games_played": 0,
            "total_score": 0,
            "high_score": 0,
            "food_eaten": 0,
            "longest_snake": 3,
            "time_played": 0.0,
            "max_combo": 0,
        }

    def _init_optional_modules(self) -> None:
        # Sound
        SoundCls = _get_class("snake_deluxe.audio.sounds", "SoundManager")
        if SoundCls:
            try:
                self._sound_mgr = SoundCls()
            except Exception:
                self._sound_mgr = None

        # Persistence
        SaveCls = _get_class("snake_deluxe.persistence", "SaveManager")
        if SaveCls:
            try:
                self._save_mgr = SaveCls("snake_deluxe_data.json")
                data = self._save_mgr.load()
                self.highscore = data.get("highscore", 0)
                self.stats = data.get("stats", self._default_stats())
                self._lb_entries = data.get("leaderboard", [])
            except Exception:
                self._save_mgr = None

        # AI
        AICls = _get_class("snake_deluxe.ai.bfs", "BFS_SnakeAI")
        if AICls:
            try:
                self._ai = AICls()
            except Exception:
                self._ai = None

        # Particles
        PartCls = _get_class("snake_deluxe.render.particles", "ParticleSystem")
        if PartCls:
            try:
                self._particles = PartCls()
            except Exception:
                self._particles = None

    # ── Properties ──

    @property
    def difficulty(self) -> str:
        return self._diff_keys[self._diff_idx]

    @property
    def mode(self) -> str:
        return GAME_MODES[self._mode_idx]

    @property
    def theme(self) -> dict[str, Any]:
        return self._theme

    @property
    def diff_cfg(self) -> dict[str, Any]:
        return DIFFICULTIES[self.difficulty]

    # ── Sound helpers ──

    def _play_sound(self, name: str) -> None:
        if not self._sound_mgr or not self._sound_on:
            return
        try:
            if name == "eat":
                self._sound_mgr.play_eat()
            elif name in ("death", "die"):
                self._sound_mgr.play_die()
            elif name == "combo":
                self._sound_mgr.play_combo(self.combo)
            elif name == "menu":
                self._sound_mgr.play_menu_click()
            elif name == "record":
                self._sound_mgr.play_new_record()
            elif name == "countdown":
                self._sound_mgr.play_countdown()
            elif name == "levelup":
                self._sound_mgr.play_level_up()
            elif name == "warning":
                self._sound_mgr.play_warning()
            elif name == "pause":
                self._sound_mgr.play_pause()
            elif name == "unpause":
                self._sound_mgr.play_unpause()
        except Exception:
            pass

    # ── Theme helpers ──

    def _apply_theme(self, theme_id: str) -> None:
        try:
            self.theme_mgr.apply(theme_id)
            self._theme = self.theme_mgr.current
            self._theme_id = theme_id
        except KeyError:
            pass

    # ── Game lifecycle ──

    def _start_game(self) -> None:
        """Initialise / reset game state for a new round."""
        cfg = self.diff_cfg
        self.w = cfg["w"]
        self.h = cfg["h"]
        speed = cfg["speed"]
        num_obs = cfg["obs"]

        cx, cy = self.w // 2, self.h // 2
        self.snake = Snake(cx, cy, 3)

        # Obstacles
        self.obstacles = set()
        if self.mode == "maze":
            MazeGen = _get_class("snake_deluxe.maps.generator", "MazeGenerator")
            if MazeGen:
                try:
                    maze = MazeGen()
                    self.obstacles = set(maze.generate(self.w, self.h))
                except Exception:
                    pass
        elif num_obs:
            self._gen_obstacles(num_obs, cx, cy)

        # Ensure spawn area is clear of obstacles (maze mode etc.)
        spawn_clear: set[tuple[int, int]] = set()
        for i in range(4):
            spawn_clear.add((cx + i, cy))
            spawn_clear.add((cx - i, cy))
            spawn_clear.add((cx, cy + i))
            spawn_clear.add((cx, cy - i))
        self.obstacles -= spawn_clear

        # Food
        self.food = Food(self.w, self.h)
        self.food.spawn(self._occupied())

        self.timer.reset(speed)
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self._msg = ""
        self._msg_ttl = 0.0
        self._timer_paused = False
        self._speed_factor = 1.0
        self._powerups.reset()
        self._invincible = False
        self._ghost = False
        self._score_mult = 1.0
        self._shrink_pending = 0
        self._grow_extra = 0
        self._food_frozen = False
        self._reversed = MODE_CONFIGS.get(self.mode, {}).get("reverse", False)
        self._reverse_flip_frame = 0

        cfg_timer = MODE_CONFIGS.get(self.mode, {}).get("timer")
        if cfg_timer is not None:
            self.time_remaining = cfg_timer
        else:
            self.time_remaining = 0

        if self._ai and self._ai_enabled:
            self._ai.reset()

        self.state = self.S_PLAYING

    def _gen_obstacles(self, count: int, sx: int, sy: int) -> None:
        """Place N random obstacles avoiding the snake spawn area."""
        occupied = {(sx - i, sy) for i in range(-2, 4)}
        for _ in range(count * 20):  # give up after 20× tries
            if len(self.obstacles) >= count:
                break
            x = random.randint(1, self.w - 2)
            y = random.randint(1, self.h - 2)
            if (x, y) not in occupied and (x, y) not in self.obstacles:
                self.obstacles.add((x, y))

    def _occupied(self) -> set[tuple[int, int]]:
        occ = self.snake.occupied_set() if self.snake else set()
        occ.update(self.obstacles)
        return occ

    def _show_msg(self, text: str, ttl: float = 2.0) -> None:
        self._msg = text
        self._msg_ttl = ttl

    # ── Game-over ──

    def _die(self) -> None:
        """End the current game."""
        self.stats["games_played"] = self.stats.get("games_played", 0) + 1
        self.stats["total_score"] = self.stats.get("total_score", 0) + self.score
        if self.score > self.stats.get("high_score", 0):
            self.stats["high_score"] = self.score
        if self.score > self.highscore:
            self.highscore = self.score
        sl = self.snake.length() if self.snake else 3
        if sl > self.stats.get("longest_snake", 3):
            self.stats["longest_snake"] = sl

        self._play_sound("death")

        # Leaderboard entry
        if self.score > 0:
            self._lb_entries.append((self.score, self.difficulty, self.mode))
            self._lb_entries.sort(key=lambda e: e[0], reverse=True)
            self._lb_entries = self._lb_entries[:10]

        self._try_save()

        self.state = self.S_GAMEOVER

    def _try_save(self) -> None:
        if self._save_mgr:
            try:
                self._save_mgr.save({
                    "highscore": self.highscore,
                    "stats": self.stats,
                    "leaderboard": self._lb_entries,
                })
            except Exception:
                pass

    # ── Power-ups ──

    def _handle_powerups(self) -> None:
        """Spawn, collect, and tick power-ups."""
        if self._powerups is None:
            return

        # Collect if snake head is on a power-up
        head = self.snake.head() if self.snake else None
        gs: dict = {}
        if head:
            gs = {
                "_speed_factor": self._speed_factor,
                "_score_mult": self._score_mult,
                "_invincible": self._invincible,
                "_ghost": self._ghost,
                "_food_frozen": False,
                "_shrink": 0,
                "_grow_extra": 0,
                "_msg": "",
                "_msg_ttl": 0.0,
            }
            ptype = self._powerups.collect(head, gs)
            if ptype:
                self._speed_factor = gs.get("_speed_factor", 1.0)
                self._score_mult = gs.get("_score_mult", 1.0)
                self._invincible = gs.get("_invincible", False)
                self._ghost = gs.get("_ghost", False)
                self._msg = gs.get("_msg", "")
                self._msg_ttl = gs.get("_msg_ttl", 0.0)
                shrink = gs.get("_shrink", 0)
                if shrink and self.snake:
                    for _ in range(shrink):
                        if self.snake.length() > 2:
                            self.snake.body.pop()
                grow = gs.get("_grow_extra", 0)
                if grow and self.snake:
                    self.snake.grow(grow)
                if self.mode != "speedrun":
                    self.timer.speed = self.diff_cfg["speed"] / max(0.1, self._speed_factor)
                self._play_sound("eat")

        # Tick (also handles effect expiry — expire callbacks modify gs)
        self._powerups.tick(gs)

        # Read back gs changes from expire callbacks
        if gs:
            self._speed_factor = gs.get("_speed_factor", self._speed_factor)
            self._score_mult = gs.get("_score_mult", self._score_mult)
            self._invincible = gs.get("_invincible", self._invincible)
            self._ghost = gs.get("_ghost", self._ghost)
            # Update timer if speed changed
            if self._speed_factor != 1.0 and self.mode != "speedrun":
                self.timer.speed = self.diff_cfg["speed"] / max(0.1, self._speed_factor)

        # Periodic spawn
        if random.random() < 0.015 and len(self._powerups.board_items) < 2:
            self._powerups.spawn_near(
                self.snake.head() if self.snake else (self.w // 2, self.h // 2),
                self._occupied(), self.w, self.h, radius=5
            )

    # ── Game tick ──

    def _tick(self) -> None:
        """Advance game state by one simulation step."""
        if self.snake is None or self.food is None:
            return

        # 1. AI override
        if self._ai and self._ai_enabled:
            try:
                obs_set = self._occupied()
                d = self._ai.think(self.snake, self.food, self.w, self.h,
                                   list(obs_set))
                self.snake.set_dir(d)
            except Exception:
                pass

        # 2. Player direction (may be overridden by AI above — order matters)
        dir_pressed = self.input.dir_pressed
        if dir_pressed and not self._ai_enabled:
            if self._reversed:
                dir_pressed = OPPOSITE.get(dir_pressed, dir_pressed)
            self.snake.turn(dir_pressed)

        # 3. Move
        self.snake.tick()

        # 4. Wrap (endless mode)
        head = self.snake.head()
        if self.mode == "endless" and not (0 <= head[0] < self.w and 0 <= head[1] < self.h):
            wx = head[0] % self.w
            wy = head[1] % self.h
            self.snake.body[0] = (wx, wy)
            head = (wx, wy)

        # 5. Self-collision
        if self.snake.hit_self() and self.mode not in ("endless", "zen"):
            if not self._invincible:
                self._die()
                return

        # 6. Obstacle collision
        if head in self.obstacles and not self._ghost:
            # In blind mode obstacles are invisible but still lethal
            self._die()
            return

        # 7. Wall collision (classic, timeattack, etc.)
        if not (0 <= head[0] < self.w and 0 <= head[1] < self.h):
            if self.mode != "endless" and not self._invincible:
                self._die()
                return

        # 8. Food
        if head == self.food.pos:
            self._eat()

        # 9. Mode-specific logic
        self._mode_tick()

        # 10. Combo decay
        if self.combo > 0:
            self.combo_timer -= self.timer.speed
            if self.combo_timer <= 0:
                self.combo = 0

        # 11. Message fade
        if self._msg_ttl > 0:
            self._msg_ttl -= self.timer.speed
            if self._msg_ttl <= 0:
                self._msg = ""
                self._msg_ttl = 0.0

        # 12. Power-ups
        self._handle_powerups()

    # ── Eating ──

    def _eat(self) -> None:
        """Handle food consumption."""
        if self.food is None:
            return
        pts = self.food.pts
        self.combo += 1
        self.combo_timer = 5.0
        bonus = min(self.combo * 5, 50)
        total = pts + int(pts * bonus / 100)
        self.score += int(total * self._score_mult)
        self.snake.grow(1)

        if self._ai:
            try:
                self._ai.on_eat()
            except Exception:
                pass

        self.stats["food_eaten"] = self.stats.get("food_eaten", 0) + 1
        if self.combo > self.stats.get("max_combo", 0):
            self.stats["max_combo"] = self.combo

        if self.combo > 1:
            self._show_msg(f"连击 x{self.combo}! +{bonus}%", 2.0)
            self._play_sound("combo")
        else:
            self._play_sound("eat")

        # Speedrun mode: speed up
        if self.mode == "speedrun":
            self._speed_factor = min(self._speed_factor / 0.98, 1.5)
            self.timer.speed = self.diff_cfg["speed"] / self._speed_factor

        # Spawn next food
        self.food.spawn(self._occupied())

        # Particles
        if self._particles:
            try:
                self._particles.emit(self.food.pos[0], self.food.pos[1], 5)
            except Exception:
                pass

    # ── Mode-specific per-tick logic ──

    def _mode_tick(self) -> None:
        if self.mode in ("timeattack", "speedrun"):
            if not self._timer_paused:
                self.time_remaining = max(0, self.time_remaining - 1)
                if self.time_remaining <= 0:
                    self._die()

        elif self.mode == "reverse":
            # Snake shrinks every 10 moves
            self._reverse_flip_frame += 1
            if self._reverse_flip_frame > 0 and self._reverse_flip_frame % 10 == 0:
                if self.snake and self.snake.length() > 2:
                    self.snake.body.pop()

        elif self.mode == "zen":
            # Spawn food automatically when eaten
            if self.food and self.food.pos is None:
                self.food.spawn(self._occupied())

    # ── Board rendering ──

    def _render(self) -> None:
        """Render the complete frame (HUD + board)."""
        lines: list[str] = []
        lines.append(HOME + HIDE_CURSOR)

        # HUD
        gs = self._game_state_dict()
        hud = render_hud(gs)
        lines.extend(hud)

        # Game board
        board = self._build_board()
        lines.extend(board)

        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()

    def _game_state_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "highscore": self.highscore,
            "combo": self.combo,
            "combo_bonus": min(self.combo * 5, 50),
            "diff": self.difficulty,
            "mode": self.mode,
            "ai_enabled": self._ai_enabled and self._ai is not None,
            "theme": self._theme.get("name", self._theme_id),
            "food_ch": self.food.ch if self.food else "★",
            "food_label": self.food.label if self.food else "Basic",
            "food_pts": self.food.pts if self.food else 10,
            "msg": self._msg,
            "msg_time": self._msg_ttl,
            "time_remaining": self.time_remaining,
            "width": self.w * 2 + 4,
            "active_powerups": self._powerups.active_names() if self._powerups else [],
            "powerup_count": len(self._powerups.board_items) if self._powerups else 0,
        }

    def _build_board(self) -> list[str]:
        """Build the ASCII board lines."""
        t = self._theme
        tc = t["colors"]
        wall_ch = t.get("wall", "#")
        floor_ch = t.get("floor", " ")
        head_ch = t.get("snake_head", "@")
        body_ch = t.get("snake_body", "o")
        obs_ch = t.get("obstacle", "X")

        is_blind = (self.mode == "blind")
        if is_blind:
            hx, hy = self.snake.head() if self.snake else (0, 0)

        # Build fast power-up position lookup (sparse dict, max 3 items)
        pu_map: dict[tuple[int, int], "ActivePowerUp"] = {}
        if self._powerups:
            for pu in self._powerups.board_items:
                pu_map[pu.pos] = pu

        lines: list[str] = []
        for y in range(self.h):
            row_bits: list[str] = []
            for x in range(self.w):
                # Blind mode: hide far cells
                if is_blind:
                    hx, hy = self.snake.head() if self.snake else (0, 0)
                    if abs(x - hx) > self._blind_radius or abs(y - hy) > self._blind_radius:
                        row_bits.append(f"{FG.WHITE}·{RESET}")
                        continue

                if self.food and (x, y) == self.food.pos:
                    row_bits.append(f"{self.food.color}{BOLD}{self.food.ch}{RESET}")
                elif (x, y) in pu_map:
                    pu = pu_map[(x, y)]
                    row_bits.append(f"{pu.color}{BOLD}{pu.ch}{RESET}")
                elif self.snake and (x, y) == self.snake.head():
                    row_bits.append(f"{tc['snake_head']}{BOLD}{head_ch}{RESET}")
                elif self.snake and (x, y) in self.snake.body:
                    row_bits.append(f"{tc['snake_body']}{body_ch}{RESET}")
                elif (x, y) in self.obstacles:
                    row_bits.append(f"{tc['obstacle']}{obs_ch}{RESET}")
                elif x == 0 or x == self.w - 1 or y == 0 or y == self.h - 1:
                    row_bits.append(f"{tc['wall']}{wall_ch}{RESET}")
                else:
                    row_bits.append(floor_ch)
            lines.append("".join(row_bits))

        # HUD border under board
        board_w = self.w
        borders = []
        borders.append(f"{tc.get('hud_border', FG.CYAN)}╘{'═' * board_w}╛{RESET}")
        lines.extend(borders)
        return lines

    # ── State handlers ──

    # ─── MENU ───

    def _handle_menu(self) -> None:
        """Main menu — input handling + rendering."""
        draw_main_menu(self._menu_frame, self.difficulty, self.mode,
                       self._theme.get("name", self._theme_id))
        key = self.input.get_menu_key()

        if key == ACTION_ENTER:
            self._start_game()
            return
        if key == ACTION_QUIT:
            self.running = False
            return
        if key == ACTION_UP:
            self._diff_idx = (self._diff_idx - 1) % len(self._diff_keys)
        if key == ACTION_DOWN:
            self._diff_idx = (self._diff_idx + 1) % len(self._diff_keys)
        # WASD support in menu: W/S for difficulty, A for AI toggle
        if isinstance(key, str):
            k = key.lower()
            if k == "w":
                self._diff_idx = (self._diff_idx - 1) % len(self._diff_keys)
            elif k == "s":
                self._diff_idx = (self._diff_idx + 1) % len(self._diff_keys)
        if key == ACTION_LEFT:
            self._mode_idx = (self._mode_idx - 1) % len(GAME_MODES)
        if key == ACTION_RIGHT:
            self._mode_idx = (self._mode_idx + 1) % len(GAME_MODES)
        # Toggle AI with 'A' key
        if isinstance(key, str) and key.lower() == "a":
            self._ai_enabled = not self._ai_enabled

        # Sub-screen shortcuts: S=设置, H=排行, T=主题浏览
        if key == ACTION_STATS:
            self.state = self.S_STATS; return
        if key == ACTION_LEADER:
            self.state = self.S_LEADERBOARD; return
        if key == ACTION_THEME:
            self.state = self.S_THEME; return

        self._menu_frame += 1
        time.sleep(0.04)

    # ─── PLAYING ───

    def _handle_playing(self) -> None:
        """Real-time gameplay loop."""
        self.input.poll()

        act = self.input.action
        if act == ACTION_PAUSE:
            self.state = self.S_PAUSED
            return
        if act == ACTION_QUIT:
            self.state = self.S_MENU
            return

        if self.timer.should_move():
            self._tick()
            if self.state != self.S_PLAYING:
                return

        self._render()
        time.sleep(self.timer.frame_delay())

    # ─── PAUSED ───

    def _handle_paused(self) -> None:
        draw_pause(self._menu_frame)
        key = self.input.get_menu_key()
        if key == ACTION_ENTER or (isinstance(key, str) and key.lower() == "p"):
            self.state = self.S_PLAYING
            return
        if key == ACTION_QUIT:
            self.state = self.S_MENU
            return
        self._menu_frame += 1
        time.sleep(0.04)

    # ─── GAME OVER ───

    def _handle_gameover(self) -> None:
        new_record = self.score == self.highscore and self.score > 0
        stats_line = (
            f"食物: {self.stats.get('food_eaten', 0)}  "
            f"连击: x{self.combo}  "
            f"局数: {self.stats.get('games_played', 0)}"
        )
        draw_game_over(self._menu_frame, self.score, self.highscore,
                       new_record, stats_line)
        key = self.input.get_menu_key()
        if key is not None:
            self.state = self.S_MENU
            return
        self._menu_frame += 1
        time.sleep(0.04)

    # ─── SETTINGS ───

    def _handle_settings(self) -> None:
        draw_settings(self._theme.get("name", self._theme_id),
                      self._sound_on)
        key = self.input.get_menu_key()
        if key == ACTION_QUIT:  # ESC
            self.state = self.S_MENU
            return
        if key == ACTION_LEFT:
            tid = self._get_prev_theme()
            self._apply_theme(tid)
        if key == ACTION_RIGHT:
            tid = self._get_next_theme()
            self._apply_theme(tid)
        if isinstance(key, str) and key.lower() == "s":
            self._sound_on = not self._sound_on
        time.sleep(0.04)

    def _get_prev_theme(self) -> str:
        themes = self.theme_mgr.list_themes()
        idx = themes.index(self._theme_id) if self._theme_id in themes else 0
        return themes[(idx - 1) % len(themes)]

    def _get_next_theme(self) -> str:
        themes = self.theme_mgr.list_themes()
        idx = themes.index(self._theme_id) if self._theme_id in themes else 0
        return themes[(idx + 1) % len(themes)]

    # ─── LEADERBOARD ───

    def _handle_leaderboard(self) -> None:
        # entries stored as (score, difficulty, mode); display as (score, "diff / mode_label", "")
        entries: list[tuple[int, str, str]] = []
        for s, d, m in self._lb_entries:
            mode_label = MODE_LABELS.get(m, m.title())
            entries.append((s, f"{d} / {mode_label}", ""))
        draw_leaderboard(entries[:5], self.difficulty, self.mode)
        key = self.input.get_menu_key()
        if key is not None:
            self.state = self.S_MENU
            return
        time.sleep(0.04)

    # ─── STATS ───

    def _handle_stats(self) -> None:
        achievements: list[str] = []
        s = self.stats
        if s.get("games_played", 0) > 0:
            achievements.append("初次游戏")
        if s.get("food_eaten", 0) > 0:
            achievements.append("初尝食物")
        if s.get("high_score", 0) > 100:
            achievements.append("百分达人 (100分)")
        if s.get("high_score", 0) > 500:
            achievements.append("高分玩家 (500分)")
        if s.get("max_combo", 0) >= 5:
            achievements.append("连击之王 (x5)")
        if s.get("longest_snake", 0) >= 20:
            achievements.append("长蛇 (20节)")

        draw_stats(s, achievements)
        key = self.input.get_menu_key()
        if key is not None:
            self.state = self.S_MENU
            return
        time.sleep(0.04)

    # ─── HELP ───

    def _handle_help(self) -> None:
        draw_help()
        key = self.input.get_menu_key()
        if key is not None:
            self.state = self.S_MENU
            return
        time.sleep(0.04)

    # ─── THEME BROWSER ───

    def _handle_theme_browser(self) -> None:
        themes = self.theme_mgr.list_themes()
        if not themes:
            self.state = self.S_MENU
            return
        self._tb_idx = max(0, min(self._tb_idx, len(themes) - 1))
        tid = themes[self._tb_idx]
        prev = self.theme_mgr.get(tid)
        draw_theme_browser(
            [self.theme_mgr.get(t).get("name", t) for t in themes],
            self._tb_idx,
            prev,
        )
        key = self.input.get_menu_key()
        if key == ACTION_QUIT:
            self.state = self.S_MENU
            return
        if key == ACTION_LEFT:
            self._tb_idx = (self._tb_idx - 1) % len(themes)
        if key == ACTION_RIGHT:
            self._tb_idx = (self._tb_idx + 1) % len(themes)
        if key == ACTION_ENTER:
            selected = themes[self._tb_idx]
            self._apply_theme(selected)
            self.state = self.S_MENU
            return
        time.sleep(0.04)

    # ── Main loop ──

    def run(self) -> None:
        """Main application loop — state machine dispatcher."""
        try:
            # Initialise timer
            self._menu_frame = 0
            while self.running:
                self.frame += 1
                dispatch = {
                    self.S_MENU: self._handle_menu,
                    self.S_PLAYING: self._handle_playing,
                    self.S_PAUSED: self._handle_paused,
                    self.S_GAMEOVER: self._handle_gameover,
                    self.S_SETTINGS: self._handle_settings,
                    self.S_LEADERBOARD: self._handle_leaderboard,
                    self.S_STATS: self._handle_stats,
                    self.S_HELP: self._handle_help,
                    self.S_THEME: self._handle_theme_browser,
                }
                handler = dispatch.get(self.state)
                if handler:
                    handler()
                else:
                    self.state = self.S_MENU
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Restore terminal and save state."""
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()
        self._try_save()
