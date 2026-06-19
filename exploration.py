"""Exploration scene: overworld map, player movement, zone transitions, interactions."""

import curses
import random
from engine import (Scene, Typewriter,
                    UP_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS,
                    INTERACT_KEYS, CONFIRM_KEYS, CANCEL_KEYS, PAUSE_KEYS)
from game_data import (TILE_WALL, TILE_FLOOR, TILE_FLOWER, TILE_SIGN,
                       TILE_SIGN2, TILE_TRIGGER, TILE_MONSTER, TILE_COLUMN,
                       TILE_PATH, TILE_VOID, TILE_PLAYER_START,
                       TILE_SAVE, TILE_EXIT, TILE_ITEM,
                       TILE_NPC, TILE_SWITCH, TILE_GATE, TILE_GATE_OPEN,
                       TILE_LOCKED, TILE_SECRET, TILE_PACIFIST, TILE_VAULT,
                       TILE_PUSH_BLOCK, TILE_SOCKET, TILE_ROUTER, TILE_MIRROR,
                       SOLID_TILES, SIGN_TEXT, SIGN2_TEXT, INTRO_TEXT)
from zones import get_zone
from items import add_item, ITEMS, use_item, item_usable_overworld, consume_key
from save_system import save_game
from lore import trace_lines

# Exploration sub-states
ST_PLAY = 0
ST_DIALOGUE = 1
ST_ENCOUNTER = 2
ST_NPC_DIALOGUE = 3
ST_SHOP = 4
ST_PAUSE = 5           # full-screen Status/Inventory pause menu
DIALOGUE_TEXT_LINES = 4

# Tile chars (2 chars each for "square" tiles)
CH_WALL      = '\u2588\u2588'  # ██
CH_WALL_TOP  = '\u2580\u2580'  # ▀▀
CH_FLOOR     = '  '
CH_FLOWER_A  = '* '
CH_FLOWER_B  = '+ '
CH_SIGN      = '! '
CH_COLUMN    = '\u2590\u258c'  # ▐▌
CH_VOID      = '  '
CH_PATH      = '. '           # dotted path
CH_MONSTER_A = 'V '           # monster idle frame 1
CH_MONSTER_B = 'v '           # monster idle frame 2
CH_PKMN_A    = '\u259c\u259b'  # ▜▛ substitute frame 1 (body + feet)
CH_PKMN_B    = '\u259f\u2599'  # ▟▙ substitute frame 2 (bounce)
CH_SAVE_A    = '\u2605 '      # ★ save point frame 1
CH_SAVE_B    = '\u2606 '      # ☆ save point frame 2
CH_EXIT      = '\u25a0 '      # ■ exit door
CH_ITEM_A    = '? '           # item pickup frame 1
CH_ITEM_B    = '! '           # item pickup frame 2
# Phase 1: new tile chars
CH_NPC_A     = '\u263a '      # ☺ NPC frame 1
CH_NPC_B     = '\u263b '      # ☻ NPC frame 2
CH_SWITCH_ON = '\u25a3 '      # ▣ switch (active)
CH_SWITCH_OFF= '\u25a2 '      # ▢ switch (inactive)
CH_GATE      = '\u2593\u2593'  # ▓▓ closed gate
CH_GATE_OPEN = ': '           # open gate (walkable)
CH_LOCKED_A  = '\u00a7 '      # § locked terminal frame 1
CH_LOCKED_B  = '\u00b6 '      # ¶ locked terminal frame 2
CH_PUSH_BLOCK = '▣ '          # movable data block
CH_SOCKET     = '◎ '          # target socket

DIAL_CHARS = {
    0: '^ ',
    1: '> ',
    2: 'v ',
    3: '< ',
}

# Ambient atmosphere messages
AMBIENT_MESSAGES = [
    "* Segmentation fault (ignored).",
    "* The filesystem hums\n  ominously.",
    "* A process died somewhere\n  nearby.",
    "* Connection timed out.",
    "* Permission denied.",
]


class ExplorationScene(Scene):

    def __init__(self, game, zone_name=None):
        super().__init__(game)
        self.zone_name = zone_name or game.current_zone
        self.zone_data = get_zone(self.zone_name)

        # Copy map (mutable)
        self.tilemap = [list(row) for row in self.zone_data["map"]]
        self.map_h = len(self.tilemap)
        self.map_w = len(self.tilemap[0]) if self.tilemap else 0

        # Find player start or use saved position
        if game.current_zone == self.zone_name and game.player_x > 0:
            self.px, self.py = game.player_x, game.player_y
        else:
            start = self._find('P')
            if start == (1, 1) and self.tilemap[1][1] != TILE_PLAYER_START:
                # No explicit 'P' — find first walkable floor tile
                start = self._first_walkable() or (self.map_w // 2, 1)
            self.px, self.py = start

        # Replace player start tile with floor
        for y in range(self.map_h):
            for x in range(self.map_w):
                if self.tilemap[y][x] == TILE_PLAYER_START:
                    self.tilemap[y][x] = TILE_FLOOR

        # Remove defeated monsters from tilemap
        for (mx, my), mname in self.zone_data.get("monsters", {}).items():
            key = f"{self.zone_name}:{mx},{my}"
            if key in game.defeated_monsters:
                self.tilemap[my][mx] = TILE_FLOOR

        # Remove collected items from tilemap
        for (ix, iy), iname in self.zone_data.get("items", {}).items():
            key = f"{self.zone_name}:{ix},{iy}"
            if key in game.collected_items:
                self.tilemap[iy][ix] = TILE_FLOOR

        # Restore puzzle state: open gates that were already toggled
        # Only restore permanent puzzles; timed puzzles reset on zone entry
        for puzzle_id, pdata in self.zone_data.get("puzzles", {}).items():
            state_key = f"{self.zone_name}:{puzzle_id}"
            is_timed = pdata.get("timer_duration") is not None
            if is_timed:
                # Timed puzzles always reset — ensure state is cleared
                game.puzzle_state[state_key] = False
            elif game.puzzle_state.get(state_key, pdata.get("default_state", False)):
                for (gx, gy) in pdata["gate_positions"]:
                    self.tilemap[gy][gx] = TILE_GATE_OPEN

        # Restore hacked locked terminals (convert to sign)
        for (lx, ly), ldata in self.zone_data.get("locked", {}).items():
            flag = ldata.get("flag")
            if flag and game.flags.get(flag):
                self.tilemap[ly][lx] = TILE_SIGN

        # Open or close lore/protocol gates based on current story flags.
        for gdata in self.zone_data.get("conditional_gates", {}).values():
            gate_tile = (TILE_GATE_OPEN if self._requirements_met(
                gdata.get("required_flags", [])) else TILE_GATE)
            for (gx, gy) in gdata.get("gate_positions", []):
                if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                    self.tilemap[gy][gx] = gate_tile

        self._restore_push_puzzles()
        self._restore_dial_puzzles()

        # Map revisions can make older save coordinates land inside a wall or
        # object. Rescue the player to the first valid floor instead of letting
        # a stale save soft-lock exploration.
        if not self._walkable(self.px, self.py):
            self.px, self.py = self._first_walkable() or (self.map_w // 2, 1)
            game.player_x = self.px
            game.player_y = self.py

        # State
        self.state = ST_PLAY
        self.anim_t = 0.0
        self.anim_frame = 0
        self.move_cd = 0.0
        self.facing = 0  # 0=down 1=up 2=left 3=right
        # Dialogue
        self.typewriter = None
        # Multi-page dialogue
        self.dialogue_pages = []
        self.dialogue_page_idx = 0
        self.current_npc = None
        # Shop
        self.shop_items = []
        self.shop_sel = 0
        # Encounter transition
        self.enc_timer = 0.0
        self.enc_duration = 1.4
        self.enc_monster_name = None
        self.enc_monster_pos = None
        self.enc_is_pkmn = False
        # Auto-intro on first zone
        self.show_intro = (self.zone_name == "RUINS_1"
                           and len(game.defeated_monsters) == 0
                           and len(game.collected_items) == 0
                           and not game.flags.get("intro_shown"))
        # Timed puzzles (countdown switches)
        self.timed_puzzles = {}  # state_key -> {"remaining": float, "puzzle_data": dict}
        # Gate bump feedback (show message once per gate)
        self.gate_msg_shown = set()
        # Ambient message timer
        self.ambient_timer = 0.0
        self.ambient_interval = random.uniform(15.0, 30.0)
        # Juice: zone banner, item pickup banner, sequence puzzle feedback
        self.zone_banner_timer = 0.0
        self.item_banner_text = None
        self.item_banner_timer = 0.0
        self.sequence_flash_timer = 0.0
        self.sequence_flash_color = 'mercy'
        # Pause menu (Tab / I)
        self.pause_tab = 0          # 0=status, 1=inventory, 2=trace, 3=help
        self.pause_sel = 0          # selected item inside inventory
        self.pause_msg = ""         # transient message (usage feedback)
        self.pause_msg_timer = 0.0
        # Update game position tracking
        game.current_zone = self.zone_name

    def _find(self, ch):
        for y, row in enumerate(self.tilemap):
            for x, c in enumerate(row):
                if c == ch:
                    return (x, y)
        return (1, 1)

    def _first_walkable(self):
        for y, row in enumerate(self.tilemap):
            for x, c in enumerate(row):
                if c == TILE_FLOOR:
                    return (x, y)
        return None

    def _requirements_met(self, requirements):
        return all(self.game.flags.get(flag) for flag, _ in requirements)

    def _missing_requirement_labels(self, requirements):
        return [
            label for flag, label in requirements
            if not self.game.flags.get(flag)
        ]

    def _format_missing_requirements(self, requirements):
        missing = self._missing_requirement_labels(requirements)
        return ", ".join(missing)

    def _requirement_message(self, msg, requirements):
        if not msg:
            return msg
        if "{missing}" in msg:
            return msg.format(
                missing=self._format_missing_requirements(requirements))
        return msg

    def _conditional_gate_message(self, x, y):
        for gdata in self.zone_data.get("conditional_gates", {}).values():
            gate_positions = {tuple(pos) for pos in gdata.get("gate_positions", [])}
            if (x, y) not in gate_positions:
                continue
            requirements = gdata.get("required_flags", [])
            if self._requirements_met(requirements):
                return None
            return gdata.get("fail_msg") or (
                "* Gate is sealed.\n"
                f"  Requires: {self._format_missing_requirements(requirements)}.")
        return None

    def _puzzle_gate_message(self, x, y):
        """Return useful feedback for gates owned by a puzzle."""
        for pdata in self.zone_data.get("dial_puzzles", {}).values():
            gate_positions = {tuple(pos) for pos in pdata.get("gate_positions", [])}
            if (x, y) not in gate_positions:
                continue
            requirements = pdata.get("required_flags", [])
            if not self._requirements_met(requirements):
                return self._requirement_message(
                    pdata.get("fail_msg"), requirements) or (
                    "* Gate is sealed.\n"
                    f"  Requires: {self._format_missing_requirements(requirements)}.")
            return pdata.get("gate_msg") or (
                "* Gate is sealed.\n"
                "  The route is ready, but\n"
                "  the puzzle is unsolved.")

        for pdata in self.zone_data.get("push_puzzles", {}).values():
            gate_positions = {tuple(pos) for pos in pdata.get("gate_positions", [])}
            if (x, y) not in gate_positions:
                continue
            requirements = pdata.get("required_flags", [])
            if not self._requirements_met(requirements):
                return self._requirement_message(
                    pdata.get("fail_msg"), requirements)
            return pdata.get("gate_msg") or (
                "* Gate is sealed.\n"
                "  Seat the data block in\n"
                "  its socket.")

        return None

    def _puzzle_requirements_met(self, pdata):
        requirements = pdata.get("required_flags", [])
        if self._requirements_met(requirements):
            return True
        msg = self._requirement_message(pdata.get("fail_msg"), requirements) or (
            "* The switch rejects you.\n"
            f"  Requires: {self._format_missing_requirements(requirements)}.")
        self._open_dialogue(msg)
        return False

    def _state_key(self, puzzle_id, suffix=None):
        base = f"{self.zone_name}:{puzzle_id}"
        return f"{base}:{suffix}" if suffix else base

    def _restore_push_puzzles(self):
        for puzzle_id, pdata in self.zone_data.get("push_puzzles", {}).items():
            state_key = self._state_key(puzzle_id)
            blocks_key = self._state_key(puzzle_id, "blocks")
            initial_blocks = [tuple(pos) for pos in pdata.get("blocks", [])]
            sockets = {tuple(pos) for pos in pdata.get("sockets", [])}

            for (bx, by) in initial_blocks:
                if 0 <= by < self.map_h and 0 <= bx < self.map_w:
                    self.tilemap[by][bx] = (
                        TILE_SOCKET if (bx, by) in sockets else TILE_FLOOR)

            for (sx, sy) in sockets:
                if 0 <= sy < self.map_h and 0 <= sx < self.map_w:
                    self.tilemap[sy][sx] = TILE_SOCKET

            saved_blocks = self.game.puzzle_state.get(blocks_key)
            block_positions = (
                [tuple(pos) for pos in saved_blocks]
                if saved_blocks else initial_blocks
            )
            for (bx, by) in block_positions:
                if 0 <= by < self.map_h and 0 <= bx < self.map_w:
                    self.tilemap[by][bx] = TILE_PUSH_BLOCK

            solved = self.game.puzzle_state.get(state_key, False)
            if (not solved and sockets.issubset(set(block_positions))
                    and self._requirements_met(pdata.get("required_flags", []))):
                solved = True
                self.game.puzzle_state[state_key] = True

            gate_tile = TILE_GATE_OPEN if solved else TILE_GATE
            for (gx, gy) in pdata.get("gate_positions", []):
                if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                    self.tilemap[gy][gx] = gate_tile

    def _restore_dial_puzzles(self):
        for puzzle_id, pdata in self.zone_data.get("dial_puzzles", {}).items():
            state_key = self._state_key(puzzle_id)
            solved = self.game.puzzle_state.get(state_key, False)
            for (gx, gy) in pdata.get("gate_positions", []):
                if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                    self.tilemap[gy][gx] = TILE_GATE_OPEN if solved else TILE_GATE

    def on_enter(self):
        bgm = self.zone_data.get("bgm", "overworld")
        if self.game.audio:
            self.game.audio.play_bgm(bgm)
        # Zone announcement banner (Zelda-style). Skipped on the very
        # first entry to RUINS_1 since the boot-sequence intro plays instead.
        if not self.show_intro:
            self.zone_banner_timer = 1.8
        # Quiet auto-save whenever the player lands in an overworld
        # zone — softens the blow of dying mid-exploration without
        # making the player hunt for save points.
        try:
            save_game(self.game)
        except Exception:
            pass
        # Show intro dialogue automatically (multi-page)
        if self.show_intro:
            self.show_intro = False
            self.game.flags["intro_shown"] = True
            if isinstance(INTRO_TEXT, list):
                self._open_multi_dialogue(INTRO_TEXT)
            else:
                self.state = ST_DIALOGUE
                self.typewriter = Typewriter(INTRO_TEXT, speed=0.03)

    def on_exit(self):
        if self.game.audio:
            self.game.audio.stop_bgm()

    # ── Update ────────────────────────────────────────────────

    def update(self, dt, keys):
        self.anim_t += dt
        if self.anim_t >= 0.45:
            self.anim_t -= 0.45
            self.anim_frame = 1 - self.anim_frame

        # Decay overlay timers regardless of sub-state
        self.zone_banner_timer = max(0.0, self.zone_banner_timer - dt)
        self.item_banner_timer = max(0.0, self.item_banner_timer - dt)
        self.sequence_flash_timer = max(0.0, self.sequence_flash_timer - dt)

        if self.state == ST_PLAY:
            self._update_play(dt, keys)
        elif self.state == ST_DIALOGUE:
            self._update_dialogue(dt, keys)
        elif self.state == ST_NPC_DIALOGUE:
            self._update_npc_dialogue(dt, keys)
        elif self.state == ST_SHOP:
            self._update_shop(dt, keys)
        elif self.state == ST_ENCOUNTER:
            self._update_encounter(dt, keys)
        elif self.state == ST_PAUSE:
            self._update_pause(dt, keys)
        # Decay transient pause message
        self.pause_msg_timer = max(0.0, self.pause_msg_timer - dt)

    def _update_play(self, dt, keys):
        self.move_cd = max(0.0, self.move_cd - dt)

        # Open pause menu (Status / Inventory) on I or Tab.
        for k in keys:
            if k in PAUSE_KEYS:
                self.state = ST_PAUSE
                self.pause_tab = 0
                self.pause_sel = 0
                self.pause_msg = ""
                self.pause_msg_timer = 0.0
                if self.game.audio:
                    self.game.audio.play('menu_open')
                return

        # Update timed puzzles
        self._update_timed_puzzles(dt)

        # Ambient messages
        self.ambient_timer += dt
        if self.ambient_timer >= self.ambient_interval:
            self.ambient_timer = 0.0
            self.ambient_interval = random.uniform(15.0, 30.0)
            msg = random.choice(AMBIENT_MESSAGES)
            self._open_dialogue(msg)
            return

        if self.move_cd > 0:
            return

        dx, dy = 0, 0
        for k in keys:
            if k in UP_KEYS:
                dy = -1; self.facing = 1; break
            elif k in DOWN_KEYS:
                dy = 1; self.facing = 0; break
            elif k in LEFT_KEYS:
                dx = -1; self.facing = 2; break
            elif k in RIGHT_KEYS:
                dx = 1; self.facing = 3; break

        if dx != 0 or dy != 0:
            nx, ny = self.px + dx, self.py + dy
            if self._walkable(nx, ny):
                self.px, self.py = nx, ny
                self.move_cd = 0.11
                # Update game tracking
                self.game.player_x = self.px
                self.game.player_y = self.py
                if self.game.audio:
                    self.game.audio.play('step')
                # Check tile interactions
                tile_here = self.tilemap[ny][nx]
                if tile_here == TILE_MONSTER:
                    self._start_encounter(nx, ny)
                    return
                elif tile_here == TILE_EXIT:
                    self._handle_exit()
                    return
                elif tile_here == TILE_ITEM:
                    self._handle_item_pickup(nx, ny)
                    return
                elif tile_here == TILE_SWITCH:
                    self._handle_switch(nx, ny)
                    return
            else:
                if (0 <= nx < self.map_w and 0 <= ny < self.map_h
                        and self.tilemap[ny][nx] == TILE_PUSH_BLOCK):
                    self._try_push_block(nx, ny, dx, dy)
                    return
                # Gate bump feedback
                if (0 <= nx < self.map_w and 0 <= ny < self.map_h
                        and self.tilemap[ny][nx] == TILE_GATE):
                    gate_msg = self._conditional_gate_message(nx, ny)
                    if not gate_msg:
                        gate_msg = self._puzzle_gate_message(nx, ny)
                    if gate_msg:
                        self._open_dialogue(gate_msg)
                        return
                    if (nx, ny) in self.gate_msg_shown:
                        return
                    self.gate_msg_shown.add((nx, ny))
                    self._open_dialogue(
                        "* Gate is sealed.\n"
                        "  Find a switch to open it.")
                return

        # Interact (Z/E near signs / save points / NPCs / locked terminals)
        for k in keys:
            if k in INTERACT_KEYS:
                self._try_interact()
                break

    def _walkable(self, x, y):
        if x < 0 or y < 0 or x >= self.map_w or y >= self.map_h:
            return False
        tile = self.tilemap[y][x]
        # Secret tile: looks like wall, but is always walkable.
        if tile == TILE_SECRET:
            return True
        # Pacifist tile: walkable only on a clean run (zero kills).
        if tile == TILE_PACIFIST:
            return self.game.kill_count == 0
        return tile not in SOLID_TILES

    def _push_puzzle_for_block(self, x, y):
        for puzzle_id, pdata in self.zone_data.get("push_puzzles", {}).items():
            blocks_key = self._state_key(puzzle_id, "blocks")
            block_positions = self.game.puzzle_state.get(blocks_key)
            if block_positions is None:
                block_positions = pdata.get("blocks", [])
            if (x, y) in {tuple(pos) for pos in block_positions}:
                return puzzle_id, pdata
        return None, None

    def _push_under_tile(self, x, y, pdata):
        sockets = {tuple(pos) for pos in pdata.get("sockets", [])}
        return TILE_SOCKET if (x, y) in sockets else TILE_FLOOR

    def _block_can_move_to(self, x, y):
        if x < 0 or y < 0 or x >= self.map_w or y >= self.map_h:
            return False
        return self.tilemap[y][x] in (TILE_FLOOR, TILE_SOCKET,
                                      TILE_PATH, TILE_GATE_OPEN)

    def _try_push_block(self, bx, by, dx, dy):
        puzzle_id, pdata = self._push_puzzle_for_block(bx, by)
        if not pdata:
            return
        tx, ty = bx + dx, by + dy
        if not self._block_can_move_to(tx, ty):
            self._open_dialogue(
                "* The data block refuses\n"
                "  to move that way.")
            return

        blocks_key = self._state_key(puzzle_id, "blocks")
        block_positions = [
            tuple(pos) for pos in self.game.puzzle_state.get(
                blocks_key, pdata.get("blocks", []))
        ]
        block_positions = [
            (tx, ty) if pos == (bx, by) else pos
            for pos in block_positions
        ]
        self.game.puzzle_state[blocks_key] = [list(pos) for pos in block_positions]

        self.tilemap[by][bx] = self._push_under_tile(bx, by, pdata)
        self.tilemap[ty][tx] = TILE_PUSH_BLOCK
        self.px, self.py = bx, by
        self.game.player_x = self.px
        self.game.player_y = self.py
        self.move_cd = 0.13
        if self.game.audio:
            self.game.audio.play('step')

        self._check_push_puzzle(puzzle_id, pdata, block_positions)
        try:
            save_game(self.game)
        except Exception:
            pass

    def _check_push_puzzle(self, puzzle_id, pdata, block_positions):
        sockets = {tuple(pos) for pos in pdata.get("sockets", [])}
        if not sockets.issubset(set(block_positions)):
            return

        if not self._requirements_met(pdata.get("required_flags", [])):
            msg = pdata.get("fail_msg") or (
                "* The socket lights up,\n"
                "  but the checksum is\n"
                "  still missing.")
            self._open_dialogue(msg)
            return

        state_key = self._state_key(puzzle_id)
        if self.game.puzzle_state.get(state_key):
            return
        self.game.puzzle_state[state_key] = True
        for (gx, gy) in pdata.get("gate_positions", []):
            if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                self.tilemap[gy][gx] = TILE_GATE_OPEN
        if self.game.audio:
            self.game.audio.play('seq_solve')
        self._open_dialogue(pdata.get(
            "success_msg",
            "* > SOCKET LOCKED\n"
            "  A gate opened somewhere."))

    def _dial_puzzle_at(self, x, y):
        for puzzle_id, pdata in self.zone_data.get("dial_puzzles", {}).items():
            for pos in pdata.get("nodes", {}):
                if tuple(pos) == (x, y):
                    return puzzle_id, pdata
        return None, None

    def _dial_node_data(self, pdata, x, y):
        return pdata.get("nodes", {}).get((x, y), {})

    def _dial_key(self, puzzle_id, x, y):
        return self._state_key(puzzle_id, f"dial:{x},{y}")

    def _dial_state_at(self, x, y):
        puzzle_id, pdata = self._dial_puzzle_at(x, y)
        if not pdata:
            return 0
        node = self._dial_node_data(pdata, x, y)
        return int(self.game.puzzle_state.get(
            self._dial_key(puzzle_id, x, y), node.get("initial", 0)))

    def _interact_dial(self, x, y):
        puzzle_id, pdata = self._dial_puzzle_at(x, y)
        if not pdata:
            return
        if self.game.puzzle_state.get(self._state_key(puzzle_id)):
            self._open_dialogue(pdata.get(
                "solved_msg",
                "* The alignment is stable."))
            return
        if not self._puzzle_requirements_met(pdata):
            return

        node = self._dial_node_data(pdata, x, y)
        states = int(node.get("states", pdata.get("states", 4)))
        key = self._dial_key(puzzle_id, x, y)
        current = self._dial_state_at(x, y)
        self.game.puzzle_state[key] = (current + 1) % states
        if self.game.audio:
            self.game.audio.play('select')

        if self._dial_puzzle_solved(pdata):
            state_key = self._state_key(puzzle_id)
            if not self.game.puzzle_state.get(state_key):
                self.game.puzzle_state[state_key] = True
                for (gx, gy) in pdata.get("gate_positions", []):
                    if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                        self.tilemap[gy][gx] = TILE_GATE_OPEN
                if self.game.audio:
                    self.game.audio.play('seq_solve')
                self._open_dialogue(pdata.get(
                    "success_msg",
                    "* > ROUTE ACCEPTED\n"
                    "  A gate opened somewhere."))
        else:
            self.game.puzzle_state[self._state_key(puzzle_id)] = False
            for (gx, gy) in pdata.get("gate_positions", []):
                if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                    self.tilemap[gy][gx] = TILE_GATE

        try:
            save_game(self.game)
        except Exception:
            pass

    def _dial_puzzle_solved(self, pdata):
        for (x, y), node in pdata.get("nodes", {}).items():
            if self._dial_state_at(x, y) != node.get("solution"):
                return False
        return True

    def _try_interact(self):
        # Check current tile and adjacent tiles for interactables
        for ddx, ddy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = self.px + ddx, self.py + ddy
            if 0 <= ny < self.map_h and 0 <= nx < self.map_w:
                tile = self.tilemap[ny][nx]

                if tile in (TILE_ROUTER, TILE_MIRROR):
                    self._interact_dial(nx, ny)
                    return

                # NPC interaction (highest priority)
                if tile == TILE_NPC:
                    self._interact_npc(nx, ny)
                    return

                # Locked terminal
                if tile == TILE_LOCKED:
                    self._interact_locked(nx, ny)
                    return

                # Vault gate (door form of locked terminal — needs keys)
                if tile == TILE_VAULT:
                    self._interact_vault(nx, ny)
                    return

                # Per-zone sign text (Phase 1)
                zone_signs = self.zone_data.get("signs", {})
                if (nx, ny) in zone_signs:
                    sign_text = zone_signs[(nx, ny)]
                    if isinstance(sign_text, (list, tuple)):
                        self.current_npc = None
                        self._open_multi_dialogue(sign_text)
                    else:
                        self._open_dialogue(sign_text)
                    return

                # Legacy sign tiles
                if tile == TILE_SIGN:
                    self._open_dialogue(SIGN_TEXT)
                    return
                elif tile == TILE_SIGN2:
                    self._open_dialogue(SIGN2_TEXT)
                    return

                # Save point
                if tile == TILE_SAVE:
                    self._handle_save()
                    return

    def _interact_npc(self, nx, ny):
        """Start NPC dialogue."""
        from npcs import get_npc, resolve_dialogue
        npcs_data = self.zone_data.get("npcs", {})
        npc_name = npcs_data.get((nx, ny))
        if not npc_name:
            return
        npc = get_npc(npc_name)
        if not npc:
            return

        self.current_npc = npc
        pages = resolve_dialogue(npc, self.game)
        self._open_multi_dialogue(pages)

    def _interact_locked(self, nx, ny):
        """Attempt to hack a locked terminal."""
        locked_data = self.zone_data.get("locked", {})
        ldata = locked_data.get((nx, ny))
        if not ldata:
            return

        flag = ldata.get("flag")
        # Already hacked
        if flag and self.game.flags.get(flag):
            self._open_dialogue(ldata["lore"])
            return

        # Some terminals require a narrative flag (e.g. having talked to ssh)
        required_flag = ldata.get("required_flag")
        if required_flag and not self.game.flags.get(required_flag):
            self._open_dialogue(ldata.get(
                "required_msg",
                "* This terminal is locked\n  by a missing credential."))
            return

        buf_cost = ldata.get("buf_cost", 0)
        if self.game.player_buf < buf_cost:
            self._open_dialogue(
                f"* Locked terminal.\n"
                f"  Requires {buf_cost} BUF to hack.\n"
                f"  (Current BUF: "
                f"{self.game.player_buf})")
            return

        if buf_cost > 0:
            self.game.player_buf -= buf_cost
            access_header = (
                f"* > HACKING TERMINAL...\n"
                f"  > BUF -{buf_cost}\n"
                f"  > ACCESS GRANTED")
        else:
            access_header = (
                "* > HACKING TERMINAL...\n"
                "  > KEY ACCEPTED\n"
                "  > ACCESS GRANTED")
        if flag:
            self.game.flags[flag] = True
        # Convert tile to sign (for re-reading)
        self.tilemap[ny][nx] = TILE_SIGN
        if self.game.audio:
            self.game.audio.play('select')
        self._open_multi_dialogue([access_header, ldata["lore"]])
        # Persist the hack — BUF spent + flag set shouldn't roll back on death.
        try:
            save_game(self.game)
        except Exception:
            pass

    def _interact_vault(self, nx, ny):
        """Vault gates ("V") can require protocol flags or inventory keys."""
        vault_data = self.zone_data.get("vaults", {})
        vdata = vault_data.get((nx, ny))
        if not vdata:
            return

        flag = vdata.get("flag")
        if flag and self.game.flags.get(flag):
            self._open_dialogue(vdata.get("lore",
                "* The vault is open."))
            return

        required_flags = vdata.get("required_flags", [])
        missing_flags = [
            label for flag, label in required_flags
            if not self.game.flags.get(flag)
        ]
        required_keys = vdata.get("required_keys", [])
        missing_keys = [k for k in required_keys if k not in self.game.inventory]
        missing = missing_flags + missing_keys
        if missing:
            need = ", ".join(missing)
            self._open_dialogue(
                f"* VAULT — locked.\n"
                f"  Requires: {need}.\n"
                f"  Resolve those processes\n"
                f"  to sync their protocols.")
            return

        # Consume legacy inventory keys if a vault still asks for them.
        for k in required_keys:
            consume_key(self.game, k)
        if flag:
            self.game.flags[flag] = True

        # Open all the gate positions associated with this vault
        for (gx, gy) in vdata.get("gate_positions", []):
            if 0 <= gy < self.map_h and 0 <= gx < self.map_w:
                self.tilemap[gy][gx] = TILE_FLOOR
        # Convert the vault tile itself to floor too
        self.tilemap[ny][nx] = TILE_FLOOR

        # Optionally reward an item
        reward = vdata.get("reward")
        if reward and add_item(self.game, reward):
            self.item_banner_text = reward
            self.item_banner_timer = 2.4

        if self.game.audio:
            self.game.audio.play('seq_solve')

        # Show lore + reward feedback
        intro = (
            f"* > VAULT UNSEALED\n"
            f"  Protocol signatures: OK\n"
            f"  Access granted.")
        pages = [intro, vdata.get("lore", "* The vault is open.")]
        if reward:
            pages.append(f"* You also found {reward}!")
        self._open_multi_dialogue(pages)

        try:
            save_game(self.game)
        except Exception:
            pass

    def _handle_switch(self, sx, sy):
        """Toggle a puzzle switch and open/close its gates."""
        puzzles = self.zone_data.get("puzzles", {})

        # Sequence puzzles (multiple switches pressed in a set order)
        for puzzle_id, pdata in puzzles.items():
            if pdata.get("type") != "sequence":
                continue
            for sw in pdata["switches"]:
                if tuple(sw["pos"]) == (sx, sy):
                    if not self._puzzle_requirements_met(pdata):
                        return
                    self._handle_sequence_switch(puzzle_id, pdata, sw["id"])
                    return

        for puzzle_id, pdata in puzzles.items():
            if pdata.get("type") == "sequence":
                continue
            if pdata["switch_pos"] == (sx, sy):
                if not self._puzzle_requirements_met(pdata):
                    return
                state_key = f"{self.zone_name}:{puzzle_id}"
                is_timed = pdata.get("timer_duration") is not None

                if is_timed:
                    # Timed switch: always activate (re-stepping resets timer)
                    self.game.puzzle_state[state_key] = True
                    for (gx, gy) in pdata["gate_positions"]:
                        self.tilemap[gy][gx] = TILE_GATE_OPEN
                    # Register/reset timer
                    duration = pdata["timer_duration"]
                    self.timed_puzzles[state_key] = {
                        "remaining": duration,
                        "puzzle_data": pdata,
                    }
                    if self.game.audio:
                        self.game.audio.play('select')
                    secs = int(duration)
                    self._open_dialogue(
                        "* > SWITCH ACTIVATED\n"
                        f"  Gate open for {secs}s. Hurry!")
                else:
                    # Permanent switch: toggle
                    current = self.game.puzzle_state.get(
                        state_key, pdata.get("default_state", False))
                    new_state = not current
                    self.game.puzzle_state[state_key] = new_state
                    for (gx, gy) in pdata["gate_positions"]:
                        if new_state:
                            self.tilemap[gy][gx] = TILE_GATE_OPEN
                        else:
                            self.tilemap[gy][gx] = TILE_GATE
                    if self.game.audio:
                        self.game.audio.play('select')
                    if new_state:
                        self._open_dialogue(
                            "* > SWITCH ACTIVATED\n"
                            "  A gate opened somewhere.")
                    else:
                        self._open_dialogue(
                            "* > SWITCH DEACTIVATED\n"
                            "  A gate closed.")
                return

    def _handle_sequence_switch(self, puzzle_id, pdata, switch_id):
        """Handle a press on a switch that belongs to a sequence puzzle.

        Already-pressed switches in the current attempt are ignored so
        the player can walk back over them without re-triggering.
        """
        state_key = f"{self.zone_name}:{puzzle_id}"
        progress_key = f"{state_key}:progress"

        # Already solved — no-op.
        if self.game.puzzle_state.get(state_key):
            return

        progress = list(self.game.puzzle_state.get(progress_key, []))

        # Debounce: pressing an already-registered switch is a no-op.
        if switch_id in progress:
            return

        correct = pdata["correct_order"]

        # Lookup label for this switch (for nicer feedback text).
        label = next((sw.get("label", sw["id"]) for sw in pdata["switches"]
                      if sw["id"] == switch_id), switch_id)

        progress.append(switch_id)

        if progress == correct[:len(progress)]:
            self.game.puzzle_state[progress_key] = progress
            if len(progress) == len(correct):
                self.game.puzzle_state[state_key] = True
                for (gx, gy) in pdata["gate_positions"]:
                    self.tilemap[gy][gx] = TILE_GATE_OPEN
                self.sequence_flash_timer = 0.8
                self.sequence_flash_color = 'mercy'
                if self.game.audio:
                    self.game.audio.play('seq_solve')
                self._open_dialogue(
                    "* > SEQUENCE ACCEPTED\n"
                    "  Boot gates unlocked.")
                # Persist the puzzle solution immediately.
                try:
                    save_game(self.game)
                except Exception:
                    pass
            else:
                self.sequence_flash_timer = 0.4
                self.sequence_flash_color = 'timing_good'
                if self.game.audio:
                    self.game.audio.play('seq_step')
                self._open_dialogue(
                    f"* > STEP {len(progress)}/{len(correct)}\n"
                    f"  {label} accepted.")
        else:
            # Wrong — reset progress.
            self.game.puzzle_state[progress_key] = []
            self.sequence_flash_timer = 0.6
            self.sequence_flash_color = 'damage'
            if self.game.audio:
                self.game.audio.play('seq_reject')
            self._open_dialogue(
                f"* > SEQUENCE REJECTED\n"
                f"  {label} was wrong.\n"
                f"  Boot order reset.")

    def _update_timed_puzzles(self, dt):
        """Tick down timed puzzle timers and close gates on expiry."""
        if not self.timed_puzzles:
            return
        expired = []
        for state_key, tdata in self.timed_puzzles.items():
            tdata["remaining"] -= dt
            if tdata["remaining"] <= 0:
                expired.append(state_key)
        for state_key in expired:
            tdata = self.timed_puzzles.pop(state_key)
            pdata = tdata["puzzle_data"]
            blocked_by_player = False
            for (gx, gy) in pdata["gate_positions"]:
                if (gx, gy) == (self.px, self.py):
                    # Grace: player is standing on gate, delay closure
                    blocked_by_player = True
                else:
                    self.tilemap[gy][gx] = TILE_GATE
            if blocked_by_player:
                # Re-add with short grace period
                tdata["remaining"] = 0.5
                self.timed_puzzles[state_key] = tdata
            else:
                # Fully expired
                self.game.puzzle_state[state_key] = False
                if self.game.audio:
                    self.game.audio.play('encounter')

    def _handle_save(self):
        """Save the game at a save point."""
        self.game.player_x = self.px
        self.game.player_y = self.py
        save_game(self.game)
        if self.game.audio:
            self.game.audio.play('save')
        self._open_dialogue(
            "* > checkpoint saved.\n"
            f"  PID: {self.game.player_name} - LV {self.game.player_lv}\n"
            f"  {self.zone_data.get('name', self.zone_name)}")

    def _handle_item_pickup(self, x, y):
        """Pick up an item from the ground."""
        items_data = self.zone_data.get("items", {})
        item_name = items_data.get((x, y))
        if not item_name:
            return

        key = f"{self.zone_name}:{x},{y}"
        if key in self.game.collected_items:
            return

        if add_item(self.game, item_name):
            self.game.collected_items.add(key)
            self.tilemap[y][x] = TILE_FLOOR
            if self.game.audio:
                self.game.audio.play('item')
            # Headline banner + detailed dialogue.
            self.item_banner_text = item_name
            self.item_banner_timer = 2.2
            self._open_dialogue(
                f"* You found {item_name}!\n"
                f"  ({ITEMS[item_name]['desc']})")
            # Persist pickup so Retry after death doesn't lose the loot.
            try:
                save_game(self.game)
            except Exception:
                pass
        else:
            self._open_dialogue("* Your pockets are full.\n  (Max 8 items)")

    def _handle_exit(self):
        """Handle zone exit transition."""
        exit_data = self.zone_data.get("exit", {})

        # Check exit conditions first (boss gates)
        conditions = exit_data.get("conditions")
        if conditions:
            for cond in conditions:
                if cond["type"] == "defeat_monster":
                    pos = cond["pos"]
                    key = f"{self.zone_name}:{pos[0]},{pos[1]}"
                    if key not in self.game.defeated_monsters:
                        self._open_dialogue(cond.get("fail_msg",
                            "* Something blocks your path."))
                        return

        target = exit_data.get("target_zone")
        if target is None:
            self._open_dialogue(
                "* The path continues...\n"
                "  But there is nothing\n"
                "  beyond here. Yet.")
            return

        if target == "ENDING":
            # Launch the bifurcated ending based on run stats.
            from endings import resolve_ending, EndingScene
            ending_type = resolve_ending(self.game)
            save_game(self.game)
            self.game.change_scene(EndingScene(self.game, ending_type))
            return

        spawn = exit_data.get("spawn", (1, 1))
        self.game.player_x = spawn[0]
        self.game.player_y = spawn[1]
        self.game.current_zone = target
        save_game(self.game)

        self.game.change_scene(ExplorationScene(self.game, target))

    # ── Dialogue ────────────────────────────────────────────

    def _open_dialogue(self, text):
        self.state = ST_DIALOGUE
        self.typewriter = Typewriter(text)
        if self.game.audio:
            self.game.audio.play('select')

    def _paginate_dialogue_pages(self, pages):
        paginated = []
        for page in pages:
            lines = str(page).split('\n')
            for i in range(0, len(lines), DIALOGUE_TEXT_LINES):
                paginated.append('\n'.join(lines[i:i + DIALOGUE_TEXT_LINES]))
        return paginated or [""]

    def _open_multi_dialogue(self, pages):
        """Open a multi-page dialogue (used for NPC dialogue and intro)."""
        self.dialogue_pages = self._paginate_dialogue_pages(pages)
        self.dialogue_page_idx = 0
        self.current_npc_for_pages = self.current_npc  # remember NPC context
        self.state = ST_NPC_DIALOGUE
        self.typewriter = Typewriter(self.dialogue_pages[0])
        if self.game.audio:
            self.game.audio.play('select')

    def _update_dialogue(self, dt, keys):
        self.typewriter.update(dt)
        for k in keys:
            if k in CONFIRM_KEYS:
                if self.typewriter.done:
                    self.state = ST_PLAY
                    self.typewriter = None
                else:
                    self.typewriter.skip()
                break

    def _update_npc_dialogue(self, dt, keys):
        """Multi-page dialogue: Z advances pages."""
        self.typewriter.update(dt)
        for k in keys:
            if k in CONFIRM_KEYS:
                if not self.typewriter.done:
                    self.typewriter.skip()
                else:
                    self.dialogue_page_idx += 1
                    if self.dialogue_page_idx < len(self.dialogue_pages):
                        self.typewriter = Typewriter(
                            self.dialogue_pages[self.dialogue_page_idx])
                    else:
                        # Dialogue finished — set any narrative flag,
                        # then open the shop if applicable.
                        npc = self.current_npc_for_pages
                        flag_set = False
                        if npc:
                            flag = npc.get("on_complete_flag")
                            if flag and not self.game.flags.get(flag):
                                self.game.flags[flag] = True
                                flag_set = True
                        if npc and npc.get("is_shop"):
                            self._open_shop(npc)
                        else:
                            self.state = ST_PLAY
                            self.typewriter = None
                            self.current_npc = None
                        if flag_set:
                            # Persist the narrative flag so ssh's key
                            # and similar one-shots survive a death+retry.
                            try:
                                save_game(self.game)
                            except Exception:
                                pass
                break

    # ── Shop ────────────────────────────────────────────────

    def _open_shop(self, npc):
        """Open the shop UI after NPC dialogue."""
        self.shop_items = list(npc.get("shop_items", []))
        self.shop_sel = 0
        self.state = ST_SHOP
        self.current_npc = npc

    def _update_shop(self, dt, keys):
        """Navigate shop: UP/DOWN select, Z buys, X exits."""
        # +1 for the "Exit" option at the end
        total = len(self.shop_items) + 1
        for k in keys:
            if k in UP_KEYS:
                self.shop_sel = (self.shop_sel - 1) % total
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.shop_sel = (self.shop_sel + 1) % total
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                if self.shop_sel >= len(self.shop_items):
                    # Exit selected
                    self.state = ST_PLAY
                    self.current_npc = None
                    return
                self._buy_item()
                break
            elif k in CANCEL_KEYS:
                self.state = ST_PLAY
                self.current_npc = None
                return

    def _buy_item(self):
        """Attempt to buy the currently selected shop item."""
        item_name = self.shop_items[self.shop_sel]
        item = ITEMS.get(item_name)
        if not item:
            return

        price = item.get("price", 10)
        if self.game.gold < price:
            self._open_dialogue(
                f"* Not enough cycles.\n"
                f"  Need {price}, have {self.game.gold}.")
            return
        if len(self.game.inventory) >= 8:
            self._open_dialogue("* Your pockets are full.\n  (Max 8 items)")
            return

        self.game.gold -= price
        add_item(self.game, item_name)
        if self.game.audio:
            self.game.audio.play('item')
        self._open_dialogue(
            f"* Bought {item_name}!\n"
            f"  (-{price} cycles)")

    # ── Pause menu (Status / Inventory) ─────────────────────

    def _update_pause(self, dt, keys):
        inv = self.game.inventory
        for k in keys:
            if k in CANCEL_KEYS or k in PAUSE_KEYS:
                self.state = ST_PLAY
                if self.game.audio:
                    # Subtle "back" sfx — menu_open is for opening only.
                    self.game.audio.play('select')
                return
            if k in LEFT_KEYS:
                self.pause_tab = (self.pause_tab - 1) % 4
                self.pause_sel = 0
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in RIGHT_KEYS:
                self.pause_tab = (self.pause_tab + 1) % 4
                self.pause_sel = 0
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in UP_KEYS and self.pause_tab == 1 and inv:
                self.pause_sel = (self.pause_sel - 1) % len(inv)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS and self.pause_tab == 1 and inv:
                self.pause_sel = (self.pause_sel + 1) % len(inv)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS and self.pause_tab == 1 and inv:
                name = inv[self.pause_sel]
                if not item_usable_overworld(name):
                    self.pause_msg = "Can't use that outside combat."
                    self.pause_msg_timer = 1.6
                    continue
                result = use_item(self.game, self.pause_sel)
                if result:
                    value, msg, item_type = result
                    if item_type == 'key_item':
                        # Key items have multi-line lore — exit the pause
                        # menu and show it as a proper dialogue.
                        self.state = ST_PLAY
                        self._open_dialogue(msg)
                    else:
                        self.pause_msg = msg.split('\n')[0].lstrip('* ').strip()
                        self.pause_msg_timer = 1.8
                    if self.pause_sel >= len(self.game.inventory):
                        self.pause_sel = max(0, len(self.game.inventory) - 1)
                    if self.game.audio:
                        sfx = 'heal' if item_type == 'heal' else (
                            'save' if item_type == 'key_item' else 'select')
                        self.game.audio.play(sfx)
                    # Inventory shrank — persist the change immediately.
                    try:
                        save_game(self.game)
                    except Exception:
                        pass
                    if item_type == 'key_item':
                        return

    def _draw_pause(self, r):
        box_w = min(60, r.width - 4)
        box_h = min(20, r.height - 2)
        bx = (r.width - box_w) // 2
        by = max(1, (r.height - box_h) // 2)

        r.fill(by, bx, box_w, box_h, ' ', 'default')
        r.box(by, bx, box_w, box_h, 'ui_border', title="PAUSED", double=True)

        # Tabs
        tabs = ["STATUS", "INVENTORY", "TRACE", "HELP"]
        tab_y = by + 2
        tab_x = bx + 3
        for i, name in enumerate(tabs):
            label = f"[{name}]"
            if i == self.pause_tab:
                r.put(tab_y, tab_x, label, 'mercy', bold=True)
            else:
                r.put(tab_y, tab_x, label, 'ui_dim')
            tab_x += len(label) + 2

        # Divider
        r.hline(by + 3, bx + 1, box_w - 2, 'ui_border')

        if self.pause_tab == 0:
            self._draw_pause_status(r, bx, by, box_w, box_h)
        elif self.pause_tab == 1:
            self._draw_pause_inventory(r, bx, by, box_w, box_h)
        elif self.pause_tab == 2:
            self._draw_pause_trace(r, bx, by, box_w, box_h)
        else:
            self._draw_pause_help(r, bx, by, box_w, box_h)

        # Transient message
        if self.pause_msg_timer > 0 and self.pause_msg:
            msg_y = by + box_h - 3
            r.put(msg_y, bx + 2, self.pause_msg[:box_w - 4],
                  'cycles_text', bold=True)

        # Controls hint
        hint_y = by + box_h - 2
        if self.pause_tab == 0:
            hint = "[<- ->] Tab   [X] Close"
        elif self.pause_tab == 1:
            hint = "[<- ->] Tab  [W/S] Item  [Z] Use  [X] Close"
        elif self.pause_tab == 2:
            hint = "[<- ->] Tab   TRACE updates with story flags"
        else:
            hint = "[<- ->] Tab   [X] Close"
        r.put(hint_y, bx + 2, hint, 'ui_dim')

    def _draw_pause_status(self, r, bx, by, bw, bh):
        g = self.game
        y = by + 5
        # Name + LV
        r.put(y, bx + 3, g.player_name, 'ui_text', bold=True)
        r.put(y, bx + 3 + len(g.player_name) + 2,
              f"LV {g.player_lv}", 'cycles_text', bold=True)

        # HP bar
        y += 2
        r.put(y, bx + 3, 'HP', 'ui_text', bold=True)
        bar_x = bx + 7
        bar_w = 20
        ratio = g.player_hp / max(g.player_max_hp, 1)
        filled = max(0, int(bar_w * ratio))
        color = ('hp_full' if ratio > 0.5
                 else ('hp_med' if ratio > 0.25 else 'hp_low'))
        r.put(y, bar_x, '█' * filled, color)
        r.put(y, bar_x + filled, '░' * (bar_w - filled), 'hp_bg')
        r.put(y, bar_x + bar_w + 2,
              f"{g.player_hp}/{g.player_max_hp}", 'ui_text')

        # BUF bar
        y += 1
        r.put(y, bx + 3, 'BUF', 'buf_full', bold=True)
        buf_w = g.player_max_buf
        buf_filled = max(0, min(buf_w, g.player_buf))
        r.put(y, bar_x, '█' * buf_filled, 'buf_full')
        r.put(y, bar_x + buf_filled, '░' * (buf_w - buf_filled), 'buf_bg')
        r.put(y, bar_x + buf_w + 2,
              f"{g.player_buf}/{g.player_max_buf}", 'buf_full')

        # Core stats
        y += 2
        r.put(y, bx + 3, f"ATK {g.player_atk}", 'ui_text')
        r.put(y, bx + 13, f"${g.gold} cycles", 'cycles_text', bold=True)

        # Identity
        y += 2
        ppid_str = f"{g.ppid} (init)" if g.ppid == 1 else (
            str(g.ppid) if g.ppid is not None else "???")
        r.put(y, bx + 3, f"PPID  {ppid_str}", 'ui_text')

        y += 1
        r.put(y, bx + 3, f"Difficulty  {g.difficulty}", 'ui_dim')

        # Run morality
        y += 2
        r.put(y, bx + 3, f"♥ {g.spare_count} spared", 'mercy', bold=True)
        r.put(y, bx + 17, f"✕ {g.kill_count} killed",
              'ominous' if g.kill_count > 0 else 'ui_dim',
              bold=g.kill_count > 0)

        # Flags (short)
        y += 2
        hacked = sum(1 for k in g.flags if k.startswith('terminal_')
                     and g.flags[k])
        r.put(y, bx + 3,
              f"Terminals hacked: {hacked}", 'ui_dim')

    def _draw_pause_inventory(self, r, bx, by, bw, bh):
        inv = self.game.inventory
        if not inv:
            r.put(by + 6, bx + 3, "(empty)", 'ui_dim')
            return

        list_y = by + 5
        max_lines = bh - 10
        start = max(0, min(len(inv) - max_lines, self.pause_sel - max_lines // 2))
        end = min(len(inv), start + max_lines)

        for i in range(start, end):
            oy = list_y + (i - start)
            name = inv[i]
            usable = item_usable_overworld(name)
            marker = '>' if i == self.pause_sel else ' '
            marker_color = 'soul' if i == self.pause_sel else 'ui_dim'
            name_color = ('item' if i == self.pause_sel and usable else
                          ('ui_dim' if not usable else 'ui_text'))
            r.put(oy, bx + 3, marker, marker_color, bold=True)
            r.put(oy, bx + 5, name, name_color, bold=(i == self.pause_sel))

        # Description of the selected item
        if 0 <= self.pause_sel < len(inv):
            name = inv[self.pause_sel]
            item = ITEMS.get(name, {})
            desc_y = by + bh - 5
            desc = item.get("desc", "")
            r.put(desc_y, bx + 3, desc[:bw - 6], 'ui_dim')

    def _draw_pause_trace(self, r, bx, by, bw, bh):
        lines = trace_lines(self.game)
        y = by + 5
        for label, text in lines:
            if y >= by + bh - 4:
                break
            if not label and not text:
                y += 1
                continue
            if label:
                color = 'mercy' if label == 'OK' else (
                    'ui_dim' if label == '--' else 'cycles_text')
                r.put(y, bx + 3, label[:10], color, bold=label != '--')
                r.put(y, bx + 15, text[:bw - 18], 'ui_text')
            else:
                r.put(y, bx + 15, text[:bw - 18], 'ui_text')
            y += 1

    def _draw_pause_help(self, r, bx, by, bw, bh):
        lines = [
            ("Move", "WASD / arrows"),
            ("Interact", "Z / Enter / E"),
            ("Pause", "I / Tab"),
            ("Tiles", "@ you   ! log   ? item   ☺ NPC"),
            ("", "★ save   # switch   ▓ gate   ■ exit"),
            ("", "▣ block  ◎ socket  ^>v< rotors"),
            ("Combat", "ACT to resolve, TERM to kill"),
            ("Spare", "^C works when the name turns green"),
            ("BUF", "Perfect dodges restore buffer"),
            ("BUF menu", "Shield, Slow, Predict spend BUF"),
        ]
        y = by + 5
        for label, text in lines:
            if y >= by + bh - 4:
                break
            if label:
                r.put(y, bx + 3, label, 'cycles_text', bold=True)
                r.put(y, bx + 15, text[:bw - 18], 'ui_text')
            else:
                r.put(y, bx + 15, text[:bw - 18], 'ui_text')
            y += 1

    # ── Encounter ───────────────────────────────────────────

    def _start_encounter(self, mx, my):
        from monsters import get_monster
        monsters_data = self.zone_data.get("monsters", {})
        self.enc_monster_name = monsters_data.get((mx, my), "Cursor")
        self.enc_monster_pos = (mx, my)
        self.state = ST_ENCOUNTER
        self.enc_timer = 0.0
        self.enc_is_pkmn = False
        mdata = get_monster(self.enc_monster_name)
        enc_sfx = mdata.get("encounter_sfx") if mdata else None
        if enc_sfx:
            self.enc_is_pkmn = True
            self.enc_duration = mdata.get("encounter_duration", 2.6)
        else:
            self.enc_duration = 1.4
        if self.game.audio:
            self.game.audio.stop_bgm()
            self.game.audio.play(enc_sfx or 'encounter')

    def _update_encounter(self, dt, keys):
        self.enc_timer += dt
        if self.enc_timer >= self.enc_duration:
            from combat import CombatScene
            self.game.change_scene(
                CombatScene(self.game, self.enc_monster_name,
                            self.zone_name, self.enc_monster_pos))

    # ── Render ────────────────────────────────────────────────

    def render(self, r):
        if self.state == ST_ENCOUNTER:
            self._render_encounter_transition(r)
            return

        ui_h = 3  # bottom UI lines
        view_h = r.height - ui_h
        map_pixel_w = self.map_w * 2
        offset_x = max(0, (r.width - map_pixel_w) // 2)

        # Camera
        if self.map_h <= view_h:
            cam_y = 0
        else:
            cam_y = self.py - view_h // 2
            cam_y = max(0, min(cam_y, self.map_h - view_h))

        # Fill void behind map
        if offset_x > 0:
            for sy in range(view_h):
                r.put(sy, 0, ' ' * offset_x, 'void')
                right_start = offset_x + map_pixel_w
                if right_start < r.width:
                    r.put(sy, right_start, ' ' * (r.width - right_start), 'void')

        # Draw tiles
        for sy in range(view_h):
            my = cam_y + sy
            if my < 0 or my >= self.map_h:
                r.put(sy, offset_x, CH_VOID * self.map_w, 'void')
                continue
            for mx in range(self.map_w):
                scr_x = offset_x + mx * 2
                if scr_x + 1 >= r.width:
                    break
                tile = self.tilemap[my][mx]
                self._draw_tile(r, sy, scr_x, tile, mx, my)

        # Draw player on top
        psx = offset_x + self.px * 2
        psy = self.py - cam_y
        if 0 <= psy < view_h and 0 <= psx < r.width - 1:
            pc, pc_color = self._player_char()
            r.put(psy, psx, pc, pc_color, bold=True)

        # Bottom UI
        self._draw_ui(r, view_h)

        # Dialogue overlay
        if self.state in (ST_DIALOGUE, ST_NPC_DIALOGUE) and self.typewriter:
            self._draw_dialogue(r)

        # Shop overlay
        if self.state == ST_SHOP:
            self._draw_shop(r)

        # Pause menu overlay (full-screen, draws last so it covers everything)
        if self.state == ST_PAUSE:
            self._draw_pause(r)
            return

        # Zone announcement (fades out over ~1.8s).
        if self.zone_banner_timer > 0:
            self._draw_zone_banner(r)

        # Item pickup banner (on top of any dialogue box).
        if self.item_banner_timer > 0 and self.item_banner_text:
            self._draw_item_banner(r)

    def _draw_zone_banner(self, r):
        zone_name = self.zone_data.get('name', self.zone_name)
        big = f"  {zone_name}  "
        # Fade to dim in the last 0.4s
        fading = self.zone_banner_timer < 0.4
        color = 'ui_dim' if fading else 'title'
        by = 1
        bx = (r.width - len(big) - 4) // 2
        width = len(big) + 4
        # Background stripe
        r.fill(by, bx, width, 3, ' ', 'default')
        r.box(by, bx, width, 3, 'ui_border', double=True)
        r.put(by + 1, bx + 2, big, color, bold=not fading)

    def _draw_item_banner(self, r):
        text = f"▸ GOT {self.item_banner_text.upper()}"
        fading = self.item_banner_timer < 0.5
        color = 'ui_dim' if fading else 'gold_text'
        # Top center
        bw = len(text) + 4
        bx = (r.width - bw) // 2
        by = 0
        r.fill(by, bx, bw, 1, ' ', 'default')
        r.put(by, bx + 2, text, color, bold=not fading)

    def _draw_tile(self, r, sy, sx, tile, mx, my):
        if tile == TILE_WALL:
            above = self.tilemap[my - 1][mx] if my > 0 else TILE_WALL
            if above != TILE_WALL:
                r.put(sy, sx, CH_WALL_TOP, 'wall_top')
            else:
                r.put(sy, sx, CH_WALL, 'wall')
        elif tile == TILE_FLOWER:
            if self.anim_frame == 0:
                r.put(sy, sx, CH_FLOWER_A, 'flower', bold=True)
            else:
                r.put(sy, sx, CH_FLOWER_B, 'flower2', bold=True)
        elif tile == TILE_SIGN or tile == TILE_SIGN2:
            r.put(sy, sx, CH_SIGN, 'sign', bold=True)
        elif tile == TILE_COLUMN:
            r.put(sy, sx, CH_COLUMN, 'column', bold=True)
        elif tile == TILE_PATH:
            r.put(sy, sx, CH_PATH, 'exp_ui_dim')
        elif tile == TILE_MONSTER:
            is_pkmn = self.zone_data.get("monsters", {}).get((mx, my)) == "Pkmn"
            if is_pkmn:
                ch = CH_PKMN_A if self.anim_frame == 0 else CH_PKMN_B
                r.put(sy, sx, ch, 'pkmn_tile', bold=True)
            elif self.anim_frame == 0:
                r.put(sy, sx, CH_MONSTER_A, 'damage', bold=True)
            else:
                r.put(sy, sx, CH_MONSTER_B, 'damage', bold=True)
        elif tile == TILE_SAVE:
            if self.anim_frame == 0:
                r.put(sy, sx, CH_SAVE_A, 'save_point', bold=True)
            else:
                r.put(sy, sx, CH_SAVE_B, 'save_point', bold=True)
        elif tile == TILE_EXIT:
            r.put(sy, sx, CH_EXIT, 'exit_tile', bold=True)
        elif tile == TILE_ITEM:
            if self.anim_frame == 0:
                r.put(sy, sx, CH_ITEM_A, 'item_tile', bold=True)
            else:
                r.put(sy, sx, CH_ITEM_B, 'item_tile', bold=True)
        # Phase 1 tiles
        elif tile == TILE_NPC:
            if self.anim_frame == 0:
                r.put(sy, sx, CH_NPC_A, 'npc_tile', bold=True)
            else:
                r.put(sy, sx, CH_NPC_B, 'npc_tile', bold=True)
        elif tile == TILE_SWITCH:
            # Switch visual: lit if the owning puzzle is solved, or if
            # it's part of an in-progress sequence step already pressed.
            activated = False
            pressed_in_sequence = False
            for pid, pdata in self.zone_data.get("puzzles", {}).items():
                if pdata.get("type") == "sequence":
                    ids_here = [sw["id"] for sw in pdata["switches"]
                                if tuple(sw["pos"]) == (mx, my)]
                    if not ids_here:
                        continue
                    state_key = f"{self.zone_name}:{pid}"
                    if self.game.puzzle_state.get(state_key):
                        activated = True
                    else:
                        progress = self.game.puzzle_state.get(
                            f"{state_key}:progress", [])
                        if ids_here[0] in progress:
                            pressed_in_sequence = True
                    break
                if pdata.get("switch_pos") == (mx, my):
                    state_key = f"{self.zone_name}:{pid}"
                    activated = self.game.puzzle_state.get(
                        state_key, pdata.get("default_state", False))
                    break
            if activated:
                r.put(sy, sx, CH_SWITCH_ON, 'switch_tile', bold=True)
            elif pressed_in_sequence:
                r.put(sy, sx, CH_SWITCH_ON, 'scan_safe', bold=True)
            else:
                r.put(sy, sx, CH_SWITCH_OFF, 'switch_tile', bold=True)
        elif tile == TILE_GATE:
            r.put(sy, sx, CH_GATE, 'gate_tile', bold=True)
        elif tile == TILE_GATE_OPEN:
            r.put(sy, sx, CH_GATE_OPEN, 'exp_ui_dim')
        elif tile == TILE_LOCKED:
            if self.anim_frame == 0:
                r.put(sy, sx, CH_LOCKED_A, 'locked_tile', bold=True)
            else:
                r.put(sy, sx, CH_LOCKED_B, 'locked_tile', bold=True)
        elif tile == TILE_VAULT:
            # Vault gate: renders like a thick locked door
            r.put(sy, sx, '▉▉', 'gold_text', bold=True)
        elif tile == TILE_PUSH_BLOCK:
            r.put(sy, sx, CH_PUSH_BLOCK, 'gold_text', bold=True)
        elif tile == TILE_SOCKET:
            r.put(sy, sx, CH_SOCKET, 'scan_safe', bold=True)
        elif tile == TILE_ROUTER:
            ch = DIAL_CHARS.get(self._dial_state_at(mx, my), '? ')
            r.put(sy, sx, ch, 'buf_full', bold=True)
        elif tile == TILE_MIRROR:
            ch = DIAL_CHARS.get(self._dial_state_at(mx, my), '? ')
            r.put(sy, sx, ch, 'save_point', bold=True)
        elif tile == TILE_SECRET:
            # Renders identical to a wall — only the player ever notices
            # the difference by walking into it.
            above = self.tilemap[my - 1][mx] if my > 0 else TILE_WALL
            if above != TILE_WALL and above != TILE_SECRET:
                r.put(sy, sx, CH_WALL_TOP, 'wall_top')
            else:
                r.put(sy, sx, CH_WALL, 'wall')
        elif tile == TILE_PACIFIST:
            # Same: looks like wall regardless. Walkability is gated by
            # kill_count == 0 in _walkable.
            above = self.tilemap[my - 1][mx] if my > 0 else TILE_WALL
            if above != TILE_WALL and above != TILE_PACIFIST:
                r.put(sy, sx, CH_WALL_TOP, 'wall_top')
            else:
                r.put(sy, sx, CH_WALL, 'wall')
        elif tile == TILE_VOID or tile == ' ':
            r.put(sy, sx, CH_VOID, 'void')
        else:
            # Floor (including old 'T' trigger — looks like floor)
            alt = (mx + my) % 2 == 0
            r.put(sy, sx, CH_FLOOR, 'floor' if alt else 'floor_alt')

    def _player_char(self):
        if self.anim_frame == 0:
            return ('@', 'player')
        else:
            return ('@', 'player_alt')

    def _draw_ui(self, r, y_start):
        r.hline(y_start, 0, r.width, 'exp_ui_dim')
        y = y_start + 1
        g = self.game
        r.put(y, 2, '\u2665', 'soul', bold=True)
        r.put(y, 4, g.player_name, 'exp_ui', bold=True)
        lv_x = 4 + len(g.player_name) + 1
        r.put(y, lv_x, f'LV {g.player_lv}', 'exp_ui_dim')

        hp_x = lv_x + 6
        r.put(y, hp_x, 'HP', 'exp_ui')
        bar_x = hp_x + 3
        bar_w = 16
        ratio = g.player_hp / max(g.player_max_hp, 1)
        filled = int(bar_w * ratio)
        color = 'hp_full' if ratio > 0.5 else ('hp_med' if ratio > 0.25 else 'hp_low')
        r.put(y, bar_x, '\u2588' * filled, color)
        r.put(y, bar_x + filled, '\u2591' * (bar_w - filled), 'hp_bg')
        hp_num = f'{g.player_hp}/{g.player_max_hp}'
        r.put(y, bar_x + bar_w + 1, hp_num, 'exp_ui')

        # Buffer bar
        buf_x = bar_x + bar_w + 1 + len(hp_num) + 2
        r.put(y, buf_x, 'BUF', 'buf_full', bold=True)
        buf_bar_x = buf_x + 4
        buf_bar_w = g.player_max_buf
        buf_filled = max(0, min(buf_bar_w, g.player_buf))
        r.put(y, buf_bar_x, '\u2588' * buf_filled, 'buf_full')
        r.put(y, buf_bar_x + buf_filled, '\u2591' * (buf_bar_w - buf_filled), 'buf_bg')
        r.put(y, buf_bar_x + buf_bar_w + 1, f'{g.player_buf}/{g.player_max_buf}', 'buf_full')

        # Cycles (gold) display
        cycles_x = buf_bar_x + buf_bar_w + 1 + len(f'{g.player_buf}/{g.player_max_buf}') + 2
        if cycles_x + 10 < r.width - 2:
            r.put(y, cycles_x, f'${g.gold}', 'cycles_text', bold=True)

        # Run stats (spared/killed) — tiny, to the left of zone name.
        zone_disp = self.zone_data.get('name', self.zone_name)
        stats_str = f"♥{g.spare_count} ✕{g.kill_count}"
        zone_x = r.width - len(zone_disp) - 2
        stats_x = zone_x - len(stats_str) - 2
        if stats_x > cycles_x + 10:
            r.put(y, stats_x, f"♥{g.spare_count}", 'mercy', bold=True)
            r.put(y, stats_x + len(f"♥{g.spare_count}") + 1,
                  f"✕{g.kill_count}", 'ominous', bold=True)

        # Zone name (right side)
        r.put(y, zone_x, zone_disp, 'exp_ui_dim')

        # Timed puzzle countdown display (above UI bar)
        if self.timed_puzzles:
            timer_y = y_start - 1
            if timer_y >= 0:
                tx = r.width - 14
                for state_key, tdata in self.timed_puzzles.items():
                    remaining = tdata["remaining"]
                    if remaining <= 3.0:
                        # Red + blinking when critical
                        color = 'hp_low'
                        blink = self.anim_frame == 0
                        if blink:
                            label = f"GATE: {remaining:.1f}s"
                        else:
                            label = f"GATE: {remaining:.1f}s"
                        r.put(timer_y, tx, label, color, bold=blink)
                    else:
                        label = f"GATE: {remaining:.1f}s"
                        r.put(timer_y, tx, label, 'cycles_text', bold=True)
                    timer_y -= 1
                    if timer_y < 0:
                        break

    def _draw_dialogue(self, r):
        box_w = min(60, r.width - 4)
        box_h = 7
        bx = (r.width - box_w) // 2
        by = r.height - box_h - 4
        r.fill(by, bx, box_w, box_h, ' ', 'default')
        r.box(by, bx, box_w, box_h, 'ui_border')

        # If multi-page, show NPC name in title
        if self.state == ST_NPC_DIALOGUE and self.current_npc_for_pages:
            title = self.current_npc_for_pages.get("display_name", "")
            if title:
                t = f' {title} '
                tx = bx + (box_w - len(t)) // 2
                r.put(by, tx, t, 'npc_tile', bold=True)

        text = self.typewriter.visible()
        lines = text.split('\n')
        max_text_lines = DIALOGUE_TEXT_LINES
        for i, line in enumerate(lines[:max_text_lines]):
            r.put(by + 1 + i, bx + 2, line, 'ui_text')
        if self.typewriter.done:
            indicator_y = by + box_h - 2
            # Show page indicator for multi-page
            if self.state == ST_NPC_DIALOGUE and len(self.dialogue_pages) > 1:
                page_str = f'{self.dialogue_page_idx + 1}/{len(self.dialogue_pages)}'
                r.put(indicator_y, bx + 2, page_str, 'ui_dim')
            r.put(indicator_y, bx + box_w - 12, '> [Z/Enter]', 'ui_dim')

    def _draw_shop(self, r):
        """Draw the shop overlay."""
        box_w = min(50, r.width - 6)
        box_h = min(len(self.shop_items) + 5, r.height - 6)
        bx = (r.width - box_w) // 2
        by = max(1, (r.height - box_h) // 2)

        r.fill(by, bx, box_w, box_h, ' ', 'default')
        r.box(by, bx, box_w, box_h, 'ui_border')

        # Title
        npc_name = self.current_npc.get("display_name", "SHOP") if self.current_npc else "SHOP"
        title = f' {npc_name} '
        tx = bx + (box_w - len(title)) // 2
        r.put(by, tx, title, 'shop_title', bold=True)

        # Cycles display
        r.put(by + 1, bx + 2, f'Cycles: ${self.game.gold}', 'cycles_text', bold=True)

        # Items
        for i, item_name in enumerate(self.shop_items):
            oy = by + 3 + i
            if oy >= by + box_h - 2:
                break
            item = ITEMS.get(item_name, {})
            price = item.get("price", 10)
            price_str = f'${price}'
            if i == self.shop_sel:
                r.put(oy, bx + 2, '>', 'soul', bold=True)
                r.put(oy, bx + 4, item_name, 'item', bold=True)
                r.put(oy, bx + box_w - len(price_str) - 2, price_str, 'cycles_text')
                # Show description on last line
                desc = item.get("desc", "")
                if desc:
                    r.put(by + box_h - 2, bx + 2,
                           desc[:box_w - 4], 'ui_dim')
            else:
                r.put(oy, bx + 4, item_name, 'ui_dim')
                r.put(oy, bx + box_w - len(price_str) - 2, price_str, 'ui_dim')

        # Exit option
        exit_y = by + 3 + len(self.shop_items)
        if exit_y < by + box_h - 2:
            if self.shop_sel >= len(self.shop_items):
                r.put(exit_y, bx + 2, '>', 'soul', bold=True)
                r.put(exit_y, bx + 4, 'Exit', 'mercy', bold=True)
            else:
                r.put(exit_y, bx + 4, 'Exit', 'ui_dim')

    # ── Encounter transition ──────────────────────────────────

    def _render_encounter_transition(self, r):
        if self.enc_is_pkmn:
            self._render_pkmn_encounter(r)
            return
        t = self.enc_timer
        if t < 0.3:
            cycle = int(t / 0.06)
            if cycle % 2 == 0:
                r.fill(0, 0, r.width, r.height, ' ', 'flash_white')
            else:
                r.fill(0, 0, r.width, r.height, ' ', 'flash_black')
        elif t < self.enc_duration - 0.2:
            r.fill(0, 0, r.width, r.height, ' ', 'default')
            progress = (t - 0.3) / (self.enc_duration - 0.5)
            progress = min(1.0, progress)
            bars = int(r.height * progress / 2) + 1
            for i in range(min(bars, r.height // 2 + 1)):
                r.put(i, 0, ' ' * r.width, 'flash_inv')
                r.put(r.height - 1 - i, 0, ' ' * r.width, 'flash_inv')
        else:
            r.fill(0, 0, r.width, r.height, ' ', 'flash_black')

    def _render_pkmn_encounter(self, r):
        t = self.enc_timer
        w, h = r.width, r.height

        if t < 0.8:
            progress = t / 0.8
            period = 0.14 - 0.10 * progress
            cycle = int(t / max(period, 0.02))
            if cycle % 2 == 0:
                r.fill(0, 0, w, h, ' ', 'flash_white')
            else:
                r.fill(0, 0, w, h, ' ', 'flash_black')
        elif t < 1.8:
            r.fill(0, 0, w, h, ' ', 'flash_black')
            progress = (t - 0.8) / 1.0
            band_h = max(2, h // 5)
            for i in range(5):
                band_y = i * (h // 5)
                if i % 2 == 0:
                    offset = int(progress * w)
                else:
                    offset = w - int(progress * w)
                bar_w = min(w, int(w * 0.6))
                start_x = max(0, min(offset - bar_w // 2, w - bar_w))
                for row in range(band_y, min(band_y + band_h, h)):
                    r.put(row, start_x, ' ' * bar_w, 'flash_inv')
        elif t < 2.1:
            r.fill(0, 0, w, h, ' ', 'flash_white')
        else:
            r.fill(0, 0, w, h, ' ', 'flash_black')
