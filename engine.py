"""Core game engine: renderer, color manager, input, scene base, game loop."""

import curses
import time
import sys
import os
import locale

# Ensure UTF-8
locale.setlocale(locale.LC_ALL, '')

# ─── Key Constants ────────────────────────────────────────────────────
UP_KEYS = {ord('w'), ord('W'), curses.KEY_UP}
DOWN_KEYS = {ord('s'), ord('S'), curses.KEY_DOWN}
LEFT_KEYS = {ord('a'), ord('A'), curses.KEY_LEFT}
RIGHT_KEYS = {ord('d'), ord('D'), curses.KEY_RIGHT}
CONFIRM_KEYS = {ord('z'), ord('Z'), ord('\n'), 10, curses.KEY_ENTER}
CANCEL_KEYS = {ord('x'), ord('X')}
INTERACT_KEYS = {ord('e'), ord('E'), ord('z'), ord('Z'), ord('\n'), 10}
PAUSE_KEYS = {ord('i'), ord('I'), ord('\t'), 9}

MIN_WIDTH = 80
MIN_HEIGHT = 24


# ─── Color Manager ────────────────────────────────────────────────────
class ColorManager:
    """Manages curses 256-color pairs."""

    def __init__(self):
        self.pairs = {}
        self._next = 1
        self._256 = False

    def init(self):
        curses.start_color()
        curses.use_default_colors()
        self._256 = curses.COLORS >= 256
        self._build_palette()

    def _pair(self, name, fg, bg):
        if self._next >= curses.COLOR_PAIRS - 1:
            return
        try:
            curses.init_pair(self._next, fg, bg)
            self.pairs[name] = curses.color_pair(self._next)
            self._next += 1
        except curses.error:
            pass

    def _build_palette(self):
        if self._256:
            BK = 0
            # Exploration — dark atmosphere
            self._pair('default',      15,  BK)
            self._pair('wall',         53,  52)    # deep purple on dark brown
            self._pair('wall_top',     97,  52)
            self._pair('wall_shadow',  54,  BK)
            self._pair('floor',        237, 234)   # darker gray floor
            self._pair('floor_alt',    238, 235)
            self._pair('player',       226, BK)
            self._pair('player_alt',   228, BK)
            self._pair('flower',       226, 234)
            self._pair('flower2',      214, 234)
            self._pair('sign',         34,  234)
            self._pair('column',       97,  234)
            self._pair('void',         BK,  BK)
            # New tile colors
            self._pair('save_point',   220, 234)   # golden star
            self._pair('exit_tile',    51,  234)    # cyan door
            self._pair('item_tile',    83,  234)    # green item
            # Combat - UI
            self._pair('ui_border',    15,  BK)
            self._pair('ui_text',      15,  BK)
            self._pair('ui_dim',       245, BK)
            self._pair('soul',         196, BK)
            # HP
            self._pair('hp_full',      34,  BK)
            self._pair('hp_med',       226, BK)
            self._pair('hp_low',       196, BK)
            self._pair('hp_bg',        238, BK)
            # Menu
            self._pair('fight',        208, BK)
            self._pair('fight_sel',    BK,  208)
            self._pair('act',          51,  BK)
            self._pair('act_sel',      BK,  51)
            self._pair('item',         213, BK)
            self._pair('item_sel',     BK,  213)
            self._pair('mercy',        83,  BK)
            self._pair('mercy_sel',    BK,  83)
            # Monster & combat
            self._pair('monster',      15,  BK)
            self._pair('monster_name', 15,  BK)
            self._pair('bullet',       15,  BK)
            self._pair('damage',       196, BK)
            self._pair('miss',         245, BK)
            self._pair('heal',         83,  BK)
            self._pair('timing_crit',  82,  BK)
            self._pair('timing_good',  226, BK)
            self._pair('timing_miss',  196, BK)
            self._pair('timing_bar',   240, BK)
            # Effects
            self._pair('flash_white',  15,  15)
            self._pair('flash_black',  BK,  BK)
            self._pair('flash_inv',    BK,  15)
            self._pair('title',        226, BK)
            self._pair('title_red',    196, BK)
            self._pair('title_core',   51,  BK)
            self._pair('title_frame',  33,  BK)
            self._pair('title_dim',    240, BK)
            self._pair('title_warn',   214, BK)
            self._pair('subtitle',     245, BK)
            # Exploration UI
            self._pair('exp_ui',       15,  BK)
            self._pair('exp_ui_dim',   240, BK)
            self._pair('exp_ui_loc',   226, BK)
            # Atmosphere
            self._pair('ominous',      88,  BK)    # dark red
            self._pair('gold_text',    220, BK)
            self._pair('buf_full',     51,  BK)
            self._pair('buf_bg',       238, BK)
            self._pair('pkmn_tile',    249, 234)   # light gray on floor
            # Phase 1: NPC, puzzle, shop colors
            self._pair('npc_tile',     51,  234)   # bright cyan on floor
            self._pair('switch_tile',  226, 234)   # bright yellow on floor
            self._pair('gate_tile',    88,  234)   # dark red on floor
            self._pair('locked_tile',  135, 234)   # purple on floor
            self._pair('shop_title',   220, BK)    # gold
            self._pair('cycles_text',  226, BK)    # yellow
            self._pair('buf_ability',  51,  BK)    # cyan for BUF menu
            self._pair('scan_safe',    83,  BK)    # green for scan safe cols
        else:
            # 8-color fallback
            BK = curses.COLOR_BLACK
            W = curses.COLOR_WHITE
            self._pair('default',      W, BK)
            self._pair('wall',         curses.COLOR_MAGENTA, BK)
            self._pair('wall_top',     curses.COLOR_MAGENTA, BK)
            self._pair('wall_shadow',  curses.COLOR_MAGENTA, BK)
            self._pair('floor',        W, BK)
            self._pair('floor_alt',    W, BK)
            self._pair('player',       curses.COLOR_YELLOW, BK)
            self._pair('player_alt',   curses.COLOR_YELLOW, BK)
            self._pair('flower',       curses.COLOR_YELLOW, BK)
            self._pair('flower2',      curses.COLOR_YELLOW, BK)
            self._pair('sign',         curses.COLOR_GREEN, BK)
            self._pair('column',       curses.COLOR_MAGENTA, BK)
            self._pair('void',         BK, BK)
            self._pair('save_point',   curses.COLOR_YELLOW, BK)
            self._pair('exit_tile',    curses.COLOR_CYAN, BK)
            self._pair('item_tile',    curses.COLOR_GREEN, BK)
            self._pair('ui_border',    W, BK)
            self._pair('ui_text',      W, BK)
            self._pair('ui_dim',       W, BK)
            self._pair('soul',         curses.COLOR_RED, BK)
            self._pair('hp_full',      curses.COLOR_GREEN, BK)
            self._pair('hp_med',       curses.COLOR_YELLOW, BK)
            self._pair('hp_low',       curses.COLOR_RED, BK)
            self._pair('hp_bg',        W, BK)
            self._pair('fight',        curses.COLOR_RED, BK)
            self._pair('fight_sel',    BK, curses.COLOR_RED)
            self._pair('act',          curses.COLOR_CYAN, BK)
            self._pair('act_sel',      BK, curses.COLOR_CYAN)
            self._pair('item',         curses.COLOR_MAGENTA, BK)
            self._pair('item_sel',     BK, curses.COLOR_MAGENTA)
            self._pair('mercy',        curses.COLOR_GREEN, BK)
            self._pair('mercy_sel',    BK, curses.COLOR_GREEN)
            self._pair('monster',      W, BK)
            self._pair('monster_name', W, BK)
            self._pair('bullet',       W, BK)
            self._pair('damage',       curses.COLOR_RED, BK)
            self._pair('miss',         W, BK)
            self._pair('heal',         curses.COLOR_GREEN, BK)
            self._pair('timing_crit',  curses.COLOR_GREEN, BK)
            self._pair('timing_good',  curses.COLOR_YELLOW, BK)
            self._pair('timing_miss',  curses.COLOR_RED, BK)
            self._pair('timing_bar',   W, BK)
            self._pair('flash_white',  W, W)
            self._pair('flash_black',  BK, BK)
            self._pair('flash_inv',    BK, W)
            self._pair('title',        curses.COLOR_YELLOW, BK)
            self._pair('title_red',    curses.COLOR_RED, BK)
            self._pair('title_core',   curses.COLOR_CYAN, BK)
            self._pair('title_frame',  curses.COLOR_BLUE, BK)
            self._pair('title_dim',    W, BK)
            self._pair('title_warn',   curses.COLOR_YELLOW, BK)
            self._pair('subtitle',     W, BK)
            self._pair('exp_ui',       W, BK)
            self._pair('exp_ui_dim',   W, BK)
            self._pair('exp_ui_loc',   curses.COLOR_YELLOW, BK)
            self._pair('ominous',      curses.COLOR_RED, BK)
            self._pair('gold_text',    curses.COLOR_YELLOW, BK)
            self._pair('buf_full',     curses.COLOR_CYAN, BK)
            self._pair('buf_bg',       W, BK)
            self._pair('pkmn_tile',    W, BK)
            # Phase 1 fallbacks
            self._pair('npc_tile',     curses.COLOR_CYAN, BK)
            self._pair('switch_tile',  curses.COLOR_YELLOW, BK)
            self._pair('gate_tile',    curses.COLOR_RED, BK)
            self._pair('locked_tile',  curses.COLOR_MAGENTA, BK)
            self._pair('shop_title',   curses.COLOR_YELLOW, BK)
            self._pair('cycles_text',  curses.COLOR_YELLOW, BK)
            self._pair('buf_ability',  curses.COLOR_CYAN, BK)
            self._pair('scan_safe',    curses.COLOR_GREEN, BK)

    def get(self, name, bold=False):
        attr = self.pairs.get(name, curses.color_pair(0))
        if bold:
            attr |= curses.A_BOLD
        return attr


# ─── Renderer ─────────────────────────────────────────────────────────
class Renderer:
    """Handles all terminal drawing with double-buffered curses."""

    def __init__(self, stdscr, colors):
        self.scr = stdscr
        self.colors = colors
        self.height, self.width = stdscr.getmaxyx()

    def update_size(self):
        self.height, self.width = self.scr.getmaxyx()

    def clear(self):
        self.scr.erase()

    def refresh(self):
        self.scr.noutrefresh()
        curses.doupdate()

    def put(self, y, x, text, color='default', bold=False):
        """Safely draw a string. Handles out-of-bounds and truncation."""
        if y < 0 or y >= self.height or x >= self.width:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        attr = self.colors.get(color, bold)
        max_len = self.width - x
        if max_len <= 0:
            return
        # Avoid writing to the very last cell (bottom-right) which causes error
        if y == self.height - 1 and x + len(text) >= self.width:
            text = text[:max_len - 1]
        else:
            text = text[:max_len]
        if not text:
            return
        try:
            self.scr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def put_char(self, y, x, ch, color='default', bold=False):
        """Safely draw a single character (uses addstr for Unicode safety)."""
        self.put(y, x, ch, color, bold)

    def fill(self, y, x, w, h, ch=' ', color='default'):
        attr = self.colors.get(color)
        row_str = ch * w
        for row in range(y, min(y + h, self.height)):
            if row < 0:
                continue
            actual_w = min(w, self.width - x)
            if actual_w <= 0:
                continue
            safe = row_str[:actual_w]
            # Avoid bottom-right corner
            if row == self.height - 1 and x + actual_w >= self.width:
                safe = safe[:actual_w - 1]
            try:
                self.scr.addstr(row, max(0, x), safe, attr)
            except curses.error:
                pass

    def box(self, y, x, w, h, color='ui_border', title=None, double=False):
        if w < 2 or h < 2:
            return
        if double:
            tl, tr, bl, br, hz, vt = '\u2554', '\u2557', '\u255a', '\u255d', '\u2550', '\u2551'
        else:
            tl, tr, bl, br, hz, vt = '\u250c', '\u2510', '\u2514', '\u2518', '\u2500', '\u2502'
        self.put(y, x, tl + hz * (w - 2) + tr, color)
        for row in range(y + 1, y + h - 1):
            self.put(row, x, vt, color)
            self.put(row, x + w - 1, vt, color)
        self.put(y + h - 1, x, bl + hz * (w - 2) + br, color)
        if title:
            t = f' {title} '
            tx = x + (w - len(t)) // 2
            self.put(y, tx, t, color, bold=True)

    def hline(self, y, x, w, color='ui_border'):
        self.put(y, x, '\u2500' * w, color)


# ─── Typewriter Text ──────────────────────────────────────────────────
class Typewriter:
    """Character-by-character text reveal."""

    def __init__(self, text, speed=0.035):
        self.text = text
        self.speed = speed
        self.timer = 0.0
        self.index = 0
        self.done = False

    def update(self, dt):
        if self.done:
            return
        self.timer += dt
        while self.timer >= self.speed and not self.done:
            self.timer -= self.speed
            self.index += 1
            if self.index >= len(self.text):
                self.index = len(self.text)
                self.done = True

    def skip(self):
        self.index = len(self.text)
        self.done = True

    def visible(self):
        return self.text[:self.index]


# ─── Scene Base ───────────────────────────────────────────────────────
class Scene:
    def __init__(self, game):
        self.game = game

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def update(self, dt, keys):
        pass

    def render(self, r):
        pass


# ─── Game ─────────────────────────────────────────────────────────────
class Game:
    """Main game: loop, scene management, global state."""

    def __init__(self):
        self.running = True
        self.renderer = None
        self.colors = None
        self.audio = None
        self.stdscr = None
        self.target_fps = 30
        self.dt_cap = 1.0 / self.target_fps
        # Player state
        self.player_hp = 20
        self.player_max_hp = 20
        self.player_buf = 3
        self.player_max_buf = 3
        self.player_name = "HUMAN"
        self.player_lv = 1
        self.player_exp = 0
        self.player_atk = 10
        self.gold = 0
        # Difficulty
        self.difficulty = "NORMAL"
        # Inventory
        self.inventory = []
        # Zone / position
        self.current_zone = "RUINS_1"
        self.player_x = 10
        self.player_y = 3
        # Progression tracking
        self.defeated_monsters = set()   # "ZONE:x,y" strings
        self.collected_items = set()     # "ZONE:x,y" strings
        # Phase 1: flags, puzzles, kill/spare
        self.flags = {}              # str->bool, NPC conditions + lore
        self.puzzle_state = {}       # "ZONE:puzzle_id"->bool
        self.kill_count = 0
        self.spare_count = 0
        self.combat_atk_bonus = 0   # reset per battle
        self.combat_def_bonus = 0
        # Identity (unknown until adopted / chosen)
        self.ppid = None
        # Pending ending trigger ('pacifist', 'genocide', 'neutral_spare', 'neutral_kill')
        self.pending_ending = None
        # Scene
        self._scene = None
        self._next_scene = None

    def reset_for_new_game(self, difficulty, name):
        """Set up a fresh game with given difficulty and player name."""
        from progression import DIFFICULTY
        from items import STARTING_ITEMS

        self.difficulty = difficulty
        self.player_name = name
        diff = DIFFICULTY.get(difficulty, DIFFICULTY["NORMAL"])
        self.player_max_hp = diff["base_max_hp"]
        self.player_hp = self.player_max_hp
        self.player_max_buf = diff.get("base_max_buf", 3)
        self.player_buf = self.player_max_buf
        self.player_lv = 1
        self.player_exp = 0
        self.player_atk = diff.get("base_atk", 10)
        self.gold = 0
        self.inventory = list(STARTING_ITEMS.get(difficulty, []))
        self.current_zone = "RUINS_1"
        self.player_x = 10
        self.player_y = 3
        self.defeated_monsters = set()
        self.collected_items = set()
        self.flags = {}
        self.puzzle_state = {}
        self.kill_count = 0
        self.spare_count = 0
        self.combat_atk_bonus = 0
        self.combat_def_bonus = 0
        self.ppid = None
        self.pending_ending = None

    def change_scene(self, scene):
        self._next_scene = scene

    def _autosave_if_exploring(self):
        """Save quietly when the player quits from the overworld."""
        from exploration import ExplorationScene
        from save_system import save_game
        if isinstance(self._scene, ExplorationScene):
            try:
                save_game(self)
            except Exception:
                pass

    def run(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        stdscr.timeout(16)  # ~60 reads/sec max

        # Check terminal size
        h, w = stdscr.getmaxyx()
        if h < MIN_HEIGHT or w < MIN_WIDTH:
            stdscr.nodelay(False)
            stdscr.addstr(0, 0, f"Terminal too small: {w}x{h}")
            stdscr.addstr(1, 0, f"Need at least {MIN_WIDTH}x{MIN_HEIGHT}.")
            stdscr.addstr(2, 0, "Resize terminal and restart.")
            stdscr.refresh()
            stdscr.getch()
            return

        # Colors
        self.colors = ColorManager()
        self.colors.init()

        # Renderer
        self.renderer = Renderer(stdscr, self.colors)

        # Audio (optional)
        try:
            from audio import AudioManager
            self.audio = AudioManager()
            self.audio.init()
        except Exception:
            self.audio = None

        # First scene - title screen
        from title import TitleScene
        self.change_scene(TitleScene(self))

        # ── Game Loop ─────────────────────────────────────────
        last = time.monotonic()
        while self.running:
            now = time.monotonic()
            dt = min(now - last, 0.1)  # cap to avoid spiral
            last = now

            # Scene transition
            if self._next_scene is not None:
                if self._scene:
                    self._scene.on_exit()
                self._scene = self._next_scene
                self._next_scene = None
                self._scene.on_enter()

            # Gather all buffered keys
            keys = []
            try:
                while True:
                    k = stdscr.getch()
                    if k == -1:
                        break
                    keys.append(k)
            except Exception:
                pass

            # Global quit
            if 27 in keys:  # ESC
                self._autosave_if_exploring()
                self.running = False
                break

            # Resize
            if curses.KEY_RESIZE in keys:
                self.renderer.update_size()

            # Update & render
            if self._scene:
                self._scene.update(dt, keys)
                self.renderer.clear()
                self._scene.render(self.renderer)
            self.renderer.refresh()

            # Frame limit
            elapsed = time.monotonic() - now
            sleep = self.dt_cap - elapsed
            if sleep > 0.001:
                time.sleep(sleep)

        # Cleanup
        if self.audio:
            self.audio.cleanup()
