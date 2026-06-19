"""Title screen: themed boot console, main menu, difficulty select, name entry."""

import curses
import json
import random

from engine import (Scene,
                    UP_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS,
                    CONFIRM_KEYS, CANCEL_KEYS)
from save_system import save_exists, load_game, get_save_path


# ─── ASCII Art Title ──────────────────────────────────────────────────

TITLE_ART = [
    "██    ██ ███    ██ ██████  ███████ ██████  ███████ ██   ██ ███████ ██      ██     ",
    "██    ██ ████   ██ ██   ██ ██      ██   ██ ██      ██   ██ ██      ██      ██     ",
    "██    ██ ██ ██  ██ ██   ██ █████   ██████  ███████ ███████ █████   ██      ██     ",
    "██    ██ ██  ██ ██ ██   ██ ██      ██   ██      ██ ██   ██ ██      ██      ██     ",
    " ██████  ██   ████ ██████  ███████ ██   ██ ███████ ██   ██ ███████ ███████ ███████",
]

COMPACT_TITLE_ART = [
    "██╗   ██╗███╗  ██╗██████╗ ███████╗██████╗  ███████╗",
    "██║   ██║████╗ ██║██╔══██╗██╔════╝██╔══██╗ ██╔════╝",
    "██║   ██║██╔██╗██║██║  ██║█████╗  ██████╔╝ ███████╗",
    "██║   ██║██║╚████║██║  ██║██╔══╝  ██╔══██╗ ╚════██║",
    "╚██████╔╝██║ ╚███║██████╔╝███████╗██║  ██║ ███████║",
    "          S H E L L          ",
]

VERSION = "v1.2"

SUBTITLES = [
    "> RECOVERY FORK WAITING_",
    "> LAST ARCHIVE NODE ONLINE",
    "> SECTOR 7: PANIC RECORDED",
    "> PPID LOST / INTENT UNKNOWN",
    "> ^C TO SPARE / TERM TO END",
]

BOOT_LINES = [
    ("NODE", "archive-12"),
    ("RING", "offline"),
    ("PID", "unassigned"),
    ("PPID", "lost"),
]

DATA_CHARS = "01:/._<>"


# ─── Title Scene ──────────────────────────────────────────────────────

class TitleScene(Scene):

    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["New Game", "Continue", "Quit"]
        self.menu_sel = 0
        self.confirm_new_game = False
        self.confirm_sel = 0
        self.has_save = save_exists()
        self.anim_t = 0.0
        self.reveal_t = 0.0
        self.reveal_done = False
        self.glitch_timer = 0.0
        self.glitch_chars = {}  # (row, col) -> timer
        self.subtitle_idx = 0
        self.subtitle_timer = 0.0
        self.save_preview = None

    def _title_art(self):
        width = self.game.renderer.width if self.game.renderer else 999
        if max(len(line) for line in TITLE_ART) <= width:
            return TITLE_ART
        return COMPACT_TITLE_ART

    def on_enter(self):
        # Refresh save state in case the user deleted/created a save
        # since the title was last shown (e.g. returning from an ending).
        self.has_save = save_exists()
        self.save_preview = self._load_save_preview() if self.has_save else None
        if self.game.audio:
            self.game.audio.play_bgm("title", volume=0.34)

    def _load_save_preview(self):
        try:
            with open(get_save_path(), "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return {
            "name": data.get("player_name", "UNKNOWN"),
            "zone": data.get("current_zone", "UNKNOWN"),
            "lv": data.get("player_lv", "?"),
            "hp": data.get("player_hp", "?"),
            "max_hp": data.get("player_max_hp", "?"),
            "difficulty": data.get("difficulty", "UNKNOWN"),
        }

    def update(self, dt, keys):
        self.anim_t += dt
        self.reveal_t += dt

        # Reveal animation: chars appear over 1.5 seconds
        if not self.reveal_done and self.reveal_t > 1.8:
            self.reveal_done = True

        # Rotate subtitle lines every ~4s once reveal is done.
        if self.reveal_done:
            self.subtitle_timer += dt
            if self.subtitle_timer > 4.0:
                self.subtitle_timer = 0.0
                self.subtitle_idx = (self.subtitle_idx + 1) % len(SUBTITLES)

        # Glitch effect: random chars flash red periodically
        self.glitch_timer += dt
        if self.glitch_timer > 2.5 and self.reveal_done:
            self.glitch_timer = 0.0
            art = self._title_art()
            # Pick a few random positions
            for _ in range(random.randint(2, 5)):
                row = random.randint(0, len(art) - 1)
                col = random.randint(0, len(art[row]) - 1)
                if art[row][col] != ' ':
                    self.glitch_chars[(row, col)] = 0.15

        # Decay glitch timers
        expired = []
        for pos, t in self.glitch_chars.items():
            self.glitch_chars[pos] = t - dt
            if self.glitch_chars[pos] <= 0:
                expired.append(pos)
        for pos in expired:
            del self.glitch_chars[pos]

        # Menu navigation
        if not self.reveal_done:
            # Any key skips the reveal
            if keys:
                self.reveal_done = True
            return

        if self.confirm_new_game:
            self._update_new_game_confirm(keys)
            return

        for k in keys:
            if k in UP_KEYS:
                self.menu_sel = (self.menu_sel - 1) % len(self.menu_items)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.menu_sel = (self.menu_sel + 1) % len(self.menu_items)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                self._select()
                break

    def _select(self):
        choice = self.menu_items[self.menu_sel]
        if choice == "New Game":
            if self.has_save:
                self.confirm_new_game = True
                self.confirm_sel = 0
                if self.game.audio:
                    self.game.audio.play('select')
            else:
                self._start_new_game()
        elif choice == "Continue":
            if not self.has_save:
                return  # grayed out
            if self.game.audio:
                self.game.audio.play('select')
            if load_game(self.game):
                from exploration import ExplorationScene
                self.game.change_scene(
                    ExplorationScene(self.game, self.game.current_zone))
        elif choice == "Quit":
            self.game.running = False

    def _start_new_game(self):
        if self.game.audio:
            self.game.audio.play('select')
        self.game.change_scene(DifficultyScene(self.game))

    def _update_new_game_confirm(self, keys):
        for k in keys:
            if k in LEFT_KEYS or k in RIGHT_KEYS or k in UP_KEYS or k in DOWN_KEYS:
                self.confirm_sel = 1 - self.confirm_sel
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CANCEL_KEYS:
                self.confirm_new_game = False
                self.confirm_sel = 0
                if self.game.audio:
                    self.game.audio.play('select')
                break
            elif k in CONFIRM_KEYS:
                if self.confirm_sel == 0:
                    self.confirm_new_game = False
                else:
                    self._start_new_game()
                break

    def render(self, r):
        self._draw_theme_background(r)
        self._draw_status_strip(r)

        art = self._title_art()
        art_w = max(len(line) for line in art)
        art_x = max(0, (r.width - art_w) // 2)
        art_y = 3
        self._draw_logo(r, art, art_x, art_y)

        sub_y = art_y + len(art) + 1
        self._draw_subtitle(r, sub_y)

        if self.reveal_done:
            panel_y = sub_y + 2
            menu_y = panel_y + 5
            self._draw_boot_panel(r, panel_y)
            self._draw_menu_panel(r, menu_y)

            # Bottom hint and version tag.
            hint = '[W/S] Select   [Z] Confirm'
            r.put(r.height - 2, (r.width - len(hint)) // 2, hint, 'title_dim')
            r.put(r.height - 2, r.width - len(VERSION) - 2, VERSION, 'title_dim')

        if self.confirm_new_game:
            self._draw_new_game_confirm(r)

    def _draw_theme_background(self, r):
        r.fill(0, 0, r.width, r.height, ' ', 'default')
        # Deterministic data rain: lively without random full-screen flicker.
        quiet_left = max(0, (r.width - 64) // 2)
        quiet_right = min(r.width, quiet_left + 64)
        for x in range(2, r.width - 2, 5):
            if quiet_left <= x <= quiet_right:
                continue
            offset = (x * 7) % max(1, r.height)
            y = int((self.anim_t * 4 + offset) % max(1, r.height))
            ch = DATA_CHARS[(x + int(self.anim_t * 3)) % len(DATA_CHARS)]
            color = 'title_frame' if x % 3 == 0 else 'title_dim'
            r.put(y, x, ch, color)
            if y + 1 < r.height and x % 4 == 0:
                r.put(y + 1, x, '·', 'title_dim')

        # Terminal frame. It sells the theme without boxing the whole UI
        # into a heavy card.
        top = "╭─ UNDERSHELL // RECOVERY CONSOLE "
        right = " ARCHIVE NODE 12/12 ─╮"
        if len(top) + len(right) < r.width:
            r.put(0, 1, top, 'title_frame', bold=True)
            r.put(0, r.width - len(right) - 1, right, 'title_frame', bold=True)
            r.hline(0, len(top) + 1,
                    r.width - len(top) - len(right) - 2, 'title_dim')
        else:
            r.put(0, 2, "UNDERSHELL // RECOVERY CONSOLE", 'title_frame', bold=True)

        if r.height > 4:
            footer = "╰─ filesystem mounted read-only ─ recovery child unscheduled ─╯"
            r.put(r.height - 1, max(1, (r.width - len(footer)) // 2),
                  footer[:r.width - 2], 'title_dim')

    def _draw_status_strip(self, r):
        y = 1
        x = 3
        for label, value in BOOT_LINES:
            text = f"{label}:{value}"
            color = 'title_warn' if value in ("offline", "lost") else 'title_core'
            r.put(y, x, text, color, bold=label in ("PID", "PPID"))
            x += len(text) + 4
            if x > r.width - 18:
                break

    def _draw_logo(self, r, art, art_x, art_y):
        total_chars = sum(len(line) for line in art)
        chars_revealed = total_chars
        if not self.reveal_done:
            chars_revealed = int(total_chars * min(1.0, self.reveal_t / 1.5))

        art_w = max(len(line) for line in art)
        r.fill(art_y - 1, art_x - 2, art_w + 4, len(art) + 2,
               ' ', 'default')

        char_count = 0
        for row_i, line in enumerate(art):
            for col_i, ch in enumerate(line):
                if ch == ' ':
                    char_count += 1
                    continue
                char_count += 1
                if not self.reveal_done and char_count > chars_revealed:
                    continue
                if (row_i, col_i) in self.glitch_chars:
                    color = 'title_red'
                elif row_i == len(art) - 1 and art is COMPACT_TITLE_ART:
                    color = 'title_core'
                else:
                    color = 'title'
                r.put(art_y + row_i, art_x + col_i, ch, color, bold=True)

    def _draw_subtitle(self, r, y):
        sub = SUBTITLES[self.subtitle_idx]
        sub_x = (r.width - len(sub)) // 2
        r.fill(y, max(0, sub_x - 4), len(sub) + 8, 1, ' ', 'default')
        if self.reveal_done or self.reveal_t > 1.2:
            fading = self.reveal_done and self.subtitle_timer > 3.6
            color = 'title_dim' if fading else 'title_core'
            r.put(y, sub_x, sub, color, bold=not fading)

    def _draw_boot_panel(self, r, y):
        box_w = min(62, r.width - 6)
        box_h = 4
        bx = (r.width - box_w) // 2
        r.fill(y, bx, box_w, box_h, ' ', 'default')
        r.box(y, bx, box_w, box_h, 'title_frame', title="BOOT TRACE")

        if self.save_preview:
            save_line = (
                f"save: {self.save_preview['name']}  "
                f"LV {self.save_preview['lv']}  "
                f"HP {self.save_preview['hp']}/{self.save_preview['max_hp']}"
            )
            loc_line = (
                f"mount: {self.save_preview['zone']}  "
                f"mode: {self.save_preview['difficulty']}"
            )
        else:
            save_line = "save: no checkpoint found"
            loc_line = "mount: /home/lost pending  mode: normal boot"

        r.put(y + 1, bx + 3, save_line[:box_w - 6],
              'title_core' if self.save_preview else 'title_dim')
        r.put(y + 2, bx + 3, loc_line[:box_w - 6], 'subtitle')

    def _draw_menu_panel(self, r, y):
        panel_w = 28
        panel_x = (r.width - panel_w) // 2
        r.fill(y - 1, panel_x - 4, panel_w + 8, 7, ' ', 'default')
        for i, item in enumerate(self.menu_items):
            disabled = item == "Continue" and not self.has_save
            label = item.upper()
            status = "locked" if disabled else (
                "ready" if item != "Quit" else "exit")
            line = f"{label:<10} {status}"
            mx = panel_x
            row = y + i * 2
            if disabled:
                r.put(row, mx, line, 'title_dim')
            elif i == self.menu_sel:
                pulse = '>' if int(self.anim_t * 6) % 2 == 0 else '◆'
                r.put(row, mx - 3, pulse, 'soul', bold=True)
                r.put(row, mx, line, 'title_core', bold=True)
            else:
                r.put(row, mx, line, 'ui_dim')

    def _draw_new_game_confirm(self, r):
        box_w = min(54, r.width - 6)
        box_h = 8
        bx = (r.width - box_w) // 2
        by = max(2, (r.height - box_h) // 2)
        r.fill(by, bx, box_w, box_h, ' ', 'default')
        r.box(by, bx, box_w, box_h, 'ominous', title="EXISTING SAVE", double=True)

        lines = [
            "Starting a new process will overwrite",
            "the current checkpoint.",
        ]
        for i, line in enumerate(lines):
            r.put(by + 2 + i, bx + 3, line[:box_w - 6], 'ui_text')

        options = ["Cancel", "Overwrite"]
        ox = bx + 8
        oy = by + box_h - 3
        for i, label in enumerate(options):
            text = f"[{label}]"
            if i == self.confirm_sel:
                r.put(oy, ox - 2, '>', 'soul', bold=True)
                r.put(oy, ox, text, 'mercy' if i == 0 else 'ominous', bold=True)
            else:
                r.put(oy, ox, text, 'ui_dim')
            ox += len(text) + 6

        r.put(by + box_h - 2, bx + 3,
              '[<- ->] Select   [Z] Confirm   [X] Back', 'ui_dim')


# ─── Difficulty Scene ─────────────────────────────────────────────────

class DifficultyScene(Scene):

    def __init__(self, game):
        super().__init__(game)
        self.options = [
            ("EASY",   "Safe mode. More memory,",
             "slower processes."),
            ("NORMAL", "Standard boot.",
             "Default parameters."),
            ("HARD",   "Kernel panic. Less memory,",
             "hostile environment."),
        ]
        self.sel = 1  # default to NORMAL

    def on_enter(self):
        if self.game.audio:
            self.game.audio.play_bgm("title", volume=0.34)

    def update(self, dt, keys):
        for k in keys:
            if k in UP_KEYS:
                self.sel = (self.sel - 1) % len(self.options)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.sel = (self.sel + 1) % len(self.options)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                if self.game.audio:
                    self.game.audio.play('select')
                difficulty = self.options[self.sel][0]
                self.game.change_scene(NameEntryScene(self.game, difficulty))
                break
            elif k in CANCEL_KEYS:
                self.game.change_scene(TitleScene(self.game))
                break

    def render(self, r):
        title = "Choose your path."
        r.put(3, (r.width - len(title)) // 2, title, 'ui_text', bold=True)

        y = 7
        for i, (label, line1, line2) in enumerate(self.options):
            lx = (r.width - 40) // 2
            if i == self.sel:
                r.put(y, lx - 3, '> ', 'soul', bold=True)
                color = 'ominous' if label == "HARD" else 'ui_text'
                r.put(y, lx, f'[{label}]', color, bold=True)
                r.put(y + 1, lx + 2, line1, 'subtitle')
                r.put(y + 2, lx + 2, line2, 'ui_dim')
            else:
                r.put(y, lx, f'[{label}]', 'ui_dim')
            y += 4

        r.put(r.height - 2, (r.width - 36) // 2,
              '[W/S] Select  [Z] Confirm  [X] Back', 'ui_dim')


# ─── Name Entry Scene ────────────────────────────────────────────────

class NameEntryScene(Scene):

    def __init__(self, game, difficulty):
        super().__init__(game)
        self.difficulty = difficulty
        self.name = ""
        self.max_len = 8
        self.blink_t = 0.0

    def on_enter(self):
        if self.game.audio:
            self.game.audio.play_bgm("title", volume=0.34)

    def update(self, dt, keys):
        self.blink_t += dt

        for k in keys:
            if k in CONFIRM_KEYS:
                if len(self.name) > 0:
                    if self.game.audio:
                        self.game.audio.play('select')
                    self.game.reset_for_new_game(self.difficulty, self.name.upper())
                    from exploration import ExplorationScene
                    self.game.change_scene(
                        ExplorationScene(self.game, "RUINS_1"))
                    return
            elif k in CANCEL_KEYS:
                self.game.change_scene(DifficultyScene(self.game))
                return
            elif k == curses.KEY_BACKSPACE or k == 127 or k == 8:
                if self.name:
                    self.name = self.name[:-1]
            elif 32 <= k <= 126 and len(self.name) < self.max_len:
                self.name += chr(k)

    def render(self, r):
        prompt = "Name the new process."
        r.put(5, (r.width - len(prompt)) // 2, prompt, 'ui_text', bold=True)

        # Name display with cursor
        display_y = 9
        name_display = self.name
        if int(self.blink_t * 3) % 2 == 0:
            name_display += '_'
        else:
            name_display += ' '

        box_w = self.max_len + 6
        box_x = (r.width - box_w) // 2
        r.box(display_y - 1, box_x, box_w, 3, 'ui_border')
        r.put(display_y, box_x + 3, name_display, 'title', bold=True)

        # Hints
        r.put(display_y + 4, (r.width - 36) // 2,
              'Type a name (max 8 characters)', 'ui_dim')
        r.put(display_y + 5, (r.width - 40) // 2,
              '[Z/Enter] Confirm   [X] Back', 'ui_dim')

        # Show selected difficulty
        diff_text = f"Difficulty: {self.difficulty}"
        r.put(display_y + 7, (r.width - len(diff_text)) // 2,
              diff_text, 'subtitle')
