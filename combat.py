"""Combat scene: protocol menus, termination timing, dodging, HP management."""

import curses
import random
import math
from enum import IntEnum

from engine import (Scene, Typewriter, Renderer,
                    UP_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS,
                    CONFIRM_KEYS, CANCEL_KEYS)
from battle_system import ProtocolEngine
from monsters import get_monster, get_art
from progression import gain_exp, get_difficulty_mod
from items import use_item
import pkmn_sprite


# ─── Combat States ────────────────────────────────────────────────────

class S(IntEnum):
    INTRO          = 0
    MENU           = 1
    FIGHT_TIMING   = 2
    FIGHT_RESULT   = 3
    ACT_MENU       = 4
    ACT_RESULT     = 5
    ENEMY_TURN_MSG = 6
    ENEMY_ATTACK   = 7
    TURN_END       = 8
    WIN            = 9
    SPARE          = 10
    GAME_OVER      = 11
    ENDING         = 12
    ITEM_MENU      = 13
    ITEM_RESULT    = 14
    LEVELUP        = 15
    CRY            = 16
    BUF_MENU       = 17
    ACT_TIMING     = 18   # skill-based ACT (Ping's Reply)
    ACT_MASH       = 19   # skill-based ACT (Daemon's Persist)
    GAME_OVER_MENU = 20   # post-death: Retry / Title / Quit
    DEATH_ANIM     = 21   # soul shatter before GAME_OVER typewriter


# ─── Bullet ───────────────────────────────────────────────────────────

class Bullet:
    __slots__ = ('x', 'y', 'vy', 'vx', 'bounces', 'prev_x', 'prev_y')

    def __init__(self, x, y, vx=0.0, vy=6.0, bounces=0):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.bounces = bounces
        self.prev_x = self.x
        self.prev_y = self.y

    def update(self, dt):
        self.prev_x = self.x
        self.prev_y = self.y
        self.x += self.vx * dt
        self.y += self.vy * dt


class ZigzagBullet(Bullet):
    """Lightning bolt that zigzags horizontally as it falls."""
    __slots__ = ('zigzag_timer', 'zigzag_period')

    def __init__(self, x, y, vx=3.0, vy=5.0, zigzag_period=0.2):
        super().__init__(x, y, vx, vy)
        self.zigzag_timer = 0.0
        self.zigzag_period = zigzag_period

    def update(self, dt):
        self.zigzag_timer += dt
        if self.zigzag_timer >= self.zigzag_period:
            self.zigzag_timer -= self.zigzag_period
            self.vx = -self.vx
        super().update(dt)


# ─── Blob Hazard ─────────────────────────────────────────────────────

class BlobHazard:
    """Expanding/shrinking blob for heap-leak pressure."""
    __slots__ = ('cx', 'cy', 'radius', 'max_radius', 'timer', 'lifetime',
                 'growing', 'spawned_child', 'can_branch')

    def __init__(self, cx, cy, lifetime=2.0, max_radius=2,
                 warning_time=0.35, can_branch=True):
        self.cx = cx
        self.cy = cy
        self.radius = 0
        self.max_radius = max_radius
        self.timer = -warning_time
        self.lifetime = lifetime
        self.growing = True
        self.spawned_child = False
        self.can_branch = can_branch

    def update(self, dt):
        self.timer += dt
        if self.timer < 0:
            self.radius = 0
            self.growing = True
            return
        half = self.lifetime / 2
        if self.timer < half:
            self.radius = int(self.max_radius * (self.timer / half))
            self.growing = True
        else:
            self.radius = int(self.max_radius * (1.0 - (self.timer - half) / half))
            self.growing = False

    @property
    def done(self):
        return self.timer >= self.lifetime

    def cells(self, preview=False):
        """Yield all (x, y) cells occupied by this hazard."""
        if self.timer < 0 and not preview:
            return
        radius = self.max_radius if self.timer < 0 and preview else self.radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                yield (self.cx + dx, self.cy + dy)


# ─── Floating Number (damage / feedback) ─────────────────────────────

class FloatingNumber:
    """Damage number that rises from a point and fades out."""
    __slots__ = ('x', 'y', 'text', 'color', 'timer', 'lifetime', 'vy', 'big', 'anchor')

    def __init__(self, x, y, text, color='damage', lifetime=0.9,
                 big=False, anchor='arena'):
        self.x = float(x)
        self.y = float(y)
        self.text = str(text)
        self.color = color
        self.timer = 0.0
        self.lifetime = lifetime
        self.vy = -2.4
        self.big = big
        self.anchor = anchor  # 'arena' or 'monster'

    def update(self, dt):
        self.timer += dt
        self.y += self.vy * dt
        self.vy *= 0.90

    @property
    def done(self):
        return self.timer >= self.lifetime

    @property
    def fading(self):
        return self.timer > self.lifetime * 0.55


# ─── Soul Shard (death animation) ────────────────────────────────────

class SoulShard:
    """One piece of the shattered soul, flying outward under gravity."""
    __slots__ = ('x', 'y', 'vx', 'vy', 'char', 'timer', 'lifetime')

    def __init__(self, x, y, angle, speed, char='♥'):
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.char = char
        self.timer = 0.0
        self.lifetime = 1.0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 10.0 * dt   # gravity pulls shards down
        self.timer += dt

    @property
    def done(self):
        return self.timer >= self.lifetime

    @property
    def fading(self):
        return self.timer > self.lifetime * 0.6


# ─── Blink Hazard ────────────────────────────────────────────────────

class BlinkHazard:
    """Stationary hazard zone that blinks on/off for the Cursor pattern."""
    __slots__ = ('x', 'y', 'on_time', 'off_time', 'timer', 'active', 'lifetime', 'cycles')

    def __init__(self, x, y, on_time=0.5, off_time=0.3, cycles=1,
                 warning_time=0.45):
        self.x = x
        self.y = y
        self.on_time = on_time
        self.off_time = off_time
        self.timer = -warning_time
        self.active = False
        self.cycles = cycles
        self.lifetime = cycles * (on_time + off_time)

    def update(self, dt):
        self.timer += dt
        if self.timer < 0:
            self.active = False
            return
        cycle_len = self.on_time + self.off_time
        phase = self.timer % cycle_len
        self.active = phase < self.on_time

    @property
    def done(self):
        return self.timer >= self.lifetime


class Telegraph:
    """Non-damaging warning cells for attacks that fire on the next beat."""
    __slots__ = ('cells_list', 'timer', 'lifetime')

    def __init__(self, cells, lifetime=0.45):
        self.cells_list = list(cells)
        self.timer = 0.0
        self.lifetime = lifetime

    def update(self, dt):
        self.timer += dt

    @property
    def done(self):
        return self.timer >= self.lifetime

    def cells(self):
        return self.cells_list


# ─── Combat Scene ─────────────────────────────────────────────────────

BASE_MENU_ITEMS = [
    ("TERM", "fight"),
    ("ACT",   "act"),
    ("ITEM",  "item"),
    ("^C",    "mercy"),
]

BUF_ABILITIES = [
    {"name": "Shield", "cost": 2, "desc": "Absorb 1 hit next turn"},
    {"name": "Slow",   "cost": 1, "desc": "Halve bullet speed 2s"},
    {"name": "Predict", "cost": 1, "desc": "Mark safe cells next attack"},
]


class CombatScene(Scene):

    def __init__(self, game, monster_name="Cursor",
                 zone_name=None, monster_pos=None):
        super().__init__(game)
        # Monster data
        self.m = get_monster(monster_name)
        if self.m is None:
            self.m = get_monster("Cursor")
        self.m_hp = self.m["max_hp"]
        self.m_name = self.m["name"]
        self.zone_name = zone_name
        self.monster_pos = monster_pos
        # ACT options from monster data
        self.act_options = self.m.get("act_options", ["Scan", "Compliment"])
        # State machine
        self.state = S.CRY if self.m_name == "Pkmn" else S.INTRO
        self.cry_timer = 0.0
        # Menu
        self.menu_sel = 0
        self.act_sel = 0
        self.item_sel = 0
        self.buf_sel = 0
        # Dynamic menu items (BUF inserted when player has BUF)
        self._rebuild_menu()
        # Typewriter (empty during CRY state; intro text set when CRY ends)
        self.tw = Typewriter("") if self.state == S.CRY else Typewriter(self.m["intro_text"])
        # Fight timing
        self.timing_pos = 0.0
        self.timing_dir = 1
        self.timing_speed = 28.0
        self.timing_stopped = False
        self.timing_result = 0.0
        self.result_timer = 0.0
        # Bullet hell — arena
        self.arena_w = 38
        self.arena_h = 6
        self.soul_x = self.arena_w // 2
        self.soul_y = self.arena_h - 2
        self.bullets = []
        self.hazards = []
        self.bullet_timer = 0.0
        self.attack_timer = 0.0
        self.attack_duration = self.m["attack_duration"]
        self.invuln = 0.0
        self.hit_flash = 0.0
        self.bullet_spawn_count = 0
        # Protocol engine: tracks ACT order, proof turns, and spare readiness.
        self.protocol = ProtocolEngine(self.m)
        self.spare_ok = self.protocol.can_spare
        self.spare_progress = self.protocol.progress_dict()
        # Turn counter
        self.turn = 0
        # Boss phase tracking
        self.is_boss = self.m.get("is_boss", False)
        self.boss_phase = "firewall"
        self.persist_count = 0
        self.spare_weakening = False
        self.weaken_start_turn = 0
        # Animation
        self.anim_t = 0.0
        self.anim_frame = 0
        # Damage flash on monster
        self.m_flash = 0.0
        # Level-up messages queue
        self.levelup_msgs = []
        # BUF abilities state
        self.buf_shield = False     # absorb 1 hit
        self.buf_slow_timer = 0.0   # slow bullets duration
        self.buf_scan_timer = 0.0   # Predict overlay duration
        self.buf_scan_cols = []     # legacy save-safe placeholder
        # Reset combat bonuses
        game.combat_atk_bonus = 0
        game.combat_def_bonus = 0
        # Hitless turn tracker (regen BUF only if survived without damage)
        self.hitless_turn = True
        # Juice: screen shake, floating damage numbers, dodge streak
        self.shake_timer = 0.0
        self.shake_mag = 0
        self.float_nums = []
        self.dodge_streak = 0
        self.streak_clock = 0.0
        self.streak_bonus_shown = 0
        self.streak_flash = 0.0
        # Null survival: once Acknowledge is done, the next enemy attack
        # decides the spare — no collisions at all => spare_ok.
        self.null_survival_pending = self.protocol.pending_survival
        # Skill-based ACT state
        self.act_current_name = None     # the ACT triggered (e.g. "reply")
        self.act_timing_pos = 0.0
        self.act_timing_dir = 1
        self.act_timing_speed = 30.0
        self.act_timing_stopped = False
        self.act_mash_count = 0
        self.act_mash_target = 0
        self.act_mash_timer = 0.0
        self.act_mash_window = 2.0
        # Game-over menu state
        self.gg_sel = 0
        # Victory summary tracking
        self.peak_streak = 0
        self.summary_reveal = 0.0      # timer for animated reveal
        self.battle_summary = None     # populated in _finish_battle
        # Death animation state (soul shatter before Game Over)
        self.death_timer = 0.0
        self.soul_shards = []
        # Last announced attack guide; reused in the arena header so the
        # rule remains visible while the player is dodging.
        self.current_attack_rule = self.m.get("attack_rule", "")
        self.current_attack_read = self.m.get("attack_read", "")

    def _rebuild_menu(self):
        """Build menu items list, inserting BUF between ITEM and ^C if player has BUF."""
        self.menu_items = list(BASE_MENU_ITEMS)
        if self.game.player_buf > 0:
            # Insert BUF before ^C (index 3)
            self.menu_items.insert(3, ("BUF", "buf_ability"))
        self.menu_count = len(self.menu_items)

    def on_enter(self):
        if self.m_name == "Pkmn":
            # Play cry SFX; BGM starts after CRY state ends
            if self.game.audio:
                self.game.audio.play("cry_pkmn")
        else:
            if self.game.audio:
                bgm = self.m.get("battle_bgm", "battle")
                self.game.audio.play_bgm(bgm)
        if self.m_name == "Pkmn" and self.game.colors:
            pkmn_sprite.register(self.game.colors)

    def on_exit(self):
        if self.game.audio:
            self.game.audio.stop_bgm()

    # ── Update ────────────────────────────────────────────────

    def update(self, dt, keys):
        self.anim_t += dt
        if self.anim_t >= 0.5:
            self.anim_t -= 0.5
            self.anim_frame = 1 - self.anim_frame

        self.m_flash = max(0, self.m_flash - dt)
        self.hit_flash = max(0, self.hit_flash - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.streak_flash = max(0.0, self.streak_flash - dt)
        if self.state == S.ENDING and self.battle_summary is not None:
            self.summary_reveal += dt
        if self.shake_timer <= 0:
            self.shake_mag = 0
        for fn in self.float_nums:
            fn.update(dt)
        self.float_nums = [fn for fn in self.float_nums if not fn.done]

        handler = {
            S.INTRO:          self._upd_text,
            S.MENU:           self._upd_menu,
            S.FIGHT_TIMING:   self._upd_timing,
            S.FIGHT_RESULT:   self._upd_text,
            S.ACT_MENU:       self._upd_act_menu,
            S.ACT_RESULT:     self._upd_text,
            S.ENEMY_TURN_MSG: self._upd_text,
            S.ENEMY_ATTACK:   self._upd_attack,
            S.TURN_END:       self._upd_turn_end,
            S.WIN:            self._upd_text,
            S.SPARE:          self._upd_text,
            S.GAME_OVER:      self._upd_text,
            S.ENDING:         self._upd_summary,
            S.ITEM_MENU:      self._upd_item_menu,
            S.ITEM_RESULT:    self._upd_text,
            S.LEVELUP:        self._upd_text,
            S.CRY:            self._upd_cry,
            S.BUF_MENU:       self._upd_buf_menu,
            S.ACT_TIMING:     self._upd_act_timing,
            S.ACT_MASH:       self._upd_act_mash,
            S.GAME_OVER_MENU: self._upd_gg_menu,
            S.DEATH_ANIM:     self._upd_death_anim,
        }.get(self.state)
        if handler:
            handler(dt, keys)

    def _upd_cry(self, dt, keys):
        """Pkmn cry state: vibrate sprite for ~0.8s, then start BGM + intro."""
        self.cry_timer += dt
        if self.cry_timer >= 0.8:
            if self.game.audio:
                bgm = self.m.get("battle_bgm", "battle")
                self.game.audio.play_bgm(bgm)
            self.tw = Typewriter(self.m["intro_text"])
            self.state = S.INTRO

    def _upd_text(self, dt, keys):
        self.tw.update(dt)
        for k in keys:
            if k in CONFIRM_KEYS:
                if self.tw.done:
                    self._advance_from_text()
                else:
                    self.tw.skip()
                break

    def _upd_summary(self, dt, keys):
        """Advance when reveal is complete; early Z snaps to full reveal."""
        for k in keys:
            if k in CONFIRM_KEYS:
                if self.summary_reveal < 0.9:
                    # Snap the reveal to done so the player sees all info.
                    self.summary_reveal = 0.95
                else:
                    self._advance_from_text()
                break

    def _advance_from_text(self):
        if self.state == S.INTRO:
            self.state = S.MENU
        elif self.state == S.FIGHT_RESULT:
            if self.m_hp <= 0:
                # Monster defeated
                exp = self.m["exp"]
                gold = self.m["gold"]
                win_text = self.m["win_text"].format(exp=exp, gold=gold)
                self.tw = Typewriter(win_text)
                self.state = S.WIN
                if self.game.audio:
                    self.game.audio.play('spare')
            else:
                self._start_enemy_turn()
        elif self.state == S.ACT_RESULT:
            self._start_enemy_turn()
        elif self.state == S.ITEM_RESULT:
            self._start_enemy_turn()
        elif self.state == S.ENEMY_TURN_MSG:
            self._start_bullet_hell()
        elif self.state == S.WIN:
            self._finish_battle(killed=True)
        elif self.state == S.SPARE:
            self._finish_battle(killed=False)
        elif self.state == S.LEVELUP:
            # Chain through level-up messages, then reveal the summary
            # panel — so kills that granted a level still get the payoff.
            if self.levelup_msgs:
                self.tw = Typewriter(self.levelup_msgs.pop(0))
            elif self.battle_summary is not None:
                self._enter_summary_state()
            else:
                self._return_to_exploration()
        elif self.state == S.ENDING:
            self._return_to_exploration()
        elif self.state == S.GAME_OVER:
            # Transition from the typewriter screen into the options menu.
            self.state = S.GAME_OVER_MENU
            self.gg_sel = 0

    def _upd_menu(self, dt, keys):
        self._rebuild_menu()
        for k in keys:
            if k in LEFT_KEYS:
                self.menu_sel = (self.menu_sel - 1) % self.menu_count
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in RIGHT_KEYS:
                self.menu_sel = (self.menu_sel + 1) % self.menu_count
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                self._select_menu()
                break

    def _select_menu(self):
        choice = self.menu_items[self.menu_sel][0]
        if choice == "TERM":
            self.state = S.FIGHT_TIMING
            self.timing_pos = 0.0
            self.timing_dir = 1
            self.timing_stopped = False
            self.result_timer = 0.0
            if self.game.audio:
                self.game.audio.play('select')
        elif choice == "ACT":
            self.state = S.ACT_MENU
            self.act_sel = 0
            if self.game.audio:
                self.game.audio.play('select')
        elif choice == "ITEM":
            if not self.game.inventory:
                self.tw = Typewriter("* Your pockets are empty.")
                self.state = S.ACT_RESULT
            else:
                self.state = S.ITEM_MENU
                self.item_sel = 0
                if self.game.audio:
                    self.game.audio.play('select')
        elif choice == "BUF":
            self.state = S.BUF_MENU
            self.buf_sel = 0
            if self.game.audio:
                self.game.audio.play('select')
        elif choice == "^C":
            if self.spare_ok:
                self.tw = Typewriter(self.m["spare_text"])
                self.state = S.SPARE
                if self.game.audio:
                    self.game.audio.play('spare')
            else:
                self.tw = Typewriter(self.m["spare_fail_text"])
                self.state = S.ACT_RESULT

    def _upd_timing(self, dt, keys):
        if not self.timing_stopped:
            self.timing_pos += self.timing_speed * self.timing_dir * dt
            bar_w = 30
            if self.timing_pos >= bar_w - 1:
                self.timing_pos = bar_w - 1
                self.timing_dir = -1
            elif self.timing_pos <= 0:
                self.timing_pos = 0
                self.timing_dir = 1

            for k in keys:
                if k in CONFIRM_KEYS:
                    self.timing_stopped = True
                    self._calc_damage()
                    break
        else:
            self.result_timer += dt
            if self.result_timer > 1.0:
                self.result_timer = 0
                self.tw = Typewriter(self._damage_text())
                self.state = S.FIGHT_RESULT

    def _calc_damage(self):
        bar_w = 30
        center = bar_w / 2
        dist = abs(self.timing_pos - center)
        if dist <= 2:
            mult = 1.0
        elif dist <= 6:
            mult = 0.7
        elif dist <= 10:
            mult = 0.4
        else:
            mult = 0.15
        base_atk = (self.game.player_atk + self.game.combat_atk_bonus) * mult
        defense = self.m["defense"]
        dmg = max(1, int(base_atk - defense * 0.3))
        self.timing_result = dmg

        # Invincible monsters can't be killed
        if self.m.get("invincible"):
            self.m_hp = max(1, self.m_hp - dmg)
        else:
            self.m_hp = max(0, self.m_hp - dmg)

        self.m_flash = 0.5

        # Clean termination timing rewards +1 BUF so precision feeds defense.
        if dist <= 2:
            before = self.game.player_buf
            self.game.player_buf = min(
                self.game.player_max_buf, self.game.player_buf + 1)
            self._trigger_shake(0.35, 2)
            if self.game.player_buf > before:
                # Show the reward so the player connects crit → BUF.
                self.float_nums.append(
                    FloatingNumber(3, 1, '+BUF', color='buf_full',
                                   big=True, anchor='monster',
                                   lifetime=1.1))
        elif dist <= 6:
            self._trigger_shake(0.20, 1)

        # Floating damage number rises from the monster sprite area.
        num_color = 'timing_crit' if dist <= 2 else (
            'damage' if dist <= 6 else 'timing_good')
        self.float_nums.append(
            FloatingNumber(0, 0, f'-{int(self.timing_result)}',
                           color=num_color, big=dist <= 2, anchor='monster',
                           lifetime=1.0))

        if self.game.audio:
            self.game.audio.play('attack')
            if dist <= 2:
                self.game.audio.play('critical')
            elif dist > 10:
                self.game.audio.play('whiff')

    def _trigger_shake(self, duration, magnitude):
        """Set (or extend) the screen shake effect."""
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_mag = max(self.shake_mag, magnitude)

    def _damage_text(self):
        bar_w = 30
        center = bar_w / 2
        dist = abs(self.timing_pos - center)
        dmg = int(self.timing_result)
        if self.m.get("invincible"):
            return (f"* {dmg} packets sent...\n"
                    "  But null discarded\n"
                    "  them all.")
        if dist <= 2:
            return f"* SIGTERM locked on.\n  {dmg} damage!"
        elif dist <= 6:
            return f"* Signal delivered.\n  {dmg} damage."
        elif dist <= 10:
            return f"* Signal clipped.\n  {dmg} damage."
        else:
            return f"* Signal drifted.\n  {dmg} damage."

    def _protocol_flag(self):
        slug = self.m_name.lower()
        return f"protocol_{slug}_resolved"

    def _sync_protocol_state(self):
        """Mirror ProtocolEngine state onto legacy fields used by attacks/UI."""
        self.spare_ok = self.protocol.can_spare
        self.null_survival_pending = self.protocol.pending_survival
        self.spare_progress = self.protocol.progress_dict()
        self.persist_count = self.protocol.count_for("persist")

    def _protocol_progress_lines(self):
        """Short, always-visible summary of the non-violent solution."""
        return self.protocol.progress_lines(self.turn)

    def _protocol_route_line(self):
        return self.protocol.route_line()

    def _protocol_next_line(self):
        return self.protocol.next_action_line(self.turn)

    def _act_hint(self, act_name):
        hints = self.m.get("act_hints", {})
        if act_name in hints:
            return hints[act_name]
        if act_name == "scan":
            return "Read stats, mercy route, and attack rule."
        current = self.protocol.current_step_name()
        if current == act_name:
            return "Recommended next mercy step."
        return "Not the current mercy step yet."

    # ── ACT ──────────────────────────────────────────────────

    def _upd_act_menu(self, dt, keys):
        for k in keys:
            if k in UP_KEYS:
                self.act_sel = (self.act_sel - 1) % len(self.act_options)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.act_sel = (self.act_sel + 1) % len(self.act_options)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                self._do_act()
                break
            elif k in CANCEL_KEYS:
                self.state = S.MENU
                break

    def _do_act(self):
        opt = self.act_options[self.act_sel]
        opt_lower = opt.lower()

        if opt_lower == "scan":
            self.tw = Typewriter(self.m["scan_text"])
            self.state = S.ACT_RESULT
            return

        if self.m.get("spare_steps"):
            # Multi-step spare system
            self._check_spare_step(opt_lower)
        else:
            text_key = f"{opt_lower}_text"
            text = self.m.get(text_key, f"* You tried {opt}.")
            self.tw = Typewriter(text)

            spare_condition = self.m.get("spare_condition")
            if spare_condition and spare_condition == opt_lower:
                self.spare_ok = True

        self.state = S.ACT_RESULT

    def _check_spare_step(self, act_name):
        """Advance the monster's explicit repair protocol."""
        was_spare = self.spare_ok
        result = self.protocol.use_act(act_name, self.turn)
        self._sync_protocol_state()

        if self.spare_ok and not was_spare and self.is_boss:
            self.spare_weakening = True
            self.weaken_start_turn = self.turn

        self.tw = Typewriter(result.text)

    # ── Skill-based ACT: timing mini-game ─────────────────────

    def _upd_act_timing(self, dt, keys):
        """Skill ACT: stop the bar near center to succeed."""
        if not self.act_timing_stopped:
            self.act_timing_pos += self.act_timing_speed * self.act_timing_dir * dt
            bar_w = 30
            if self.act_timing_pos >= bar_w - 1:
                self.act_timing_pos = bar_w - 1
                self.act_timing_dir = -1
            elif self.act_timing_pos <= 0:
                self.act_timing_pos = 0
                self.act_timing_dir = 1

            for k in keys:
                if k in CONFIRM_KEYS:
                    self.act_timing_stopped = True
                    break
        else:
            self.result_timer += dt
            if self.result_timer > 0.9:
                self.result_timer = 0
                bar_w = 30
                center = bar_w / 2
                dist = abs(self.act_timing_pos - center)
                success = dist <= 6  # anything outside "partial" zone fails
                if success:
                    self._check_spare_step(self.act_current_name)
                else:
                    locked_key = f"{self.act_current_name}_locked_text"
                    text = self.m.get(
                        locked_key,
                        f"* Your {self.act_current_name} missed.\n  The signal drifted.")
                    self.tw = Typewriter(text)
                self.state = S.ACT_RESULT

    # ── Skill-based ACT: mash mini-game ───────────────────────

    def _upd_act_mash(self, dt, keys):
        """Skill ACT: press Z N times before the window closes."""
        self.act_mash_timer += dt
        for k in keys:
            if k in CONFIRM_KEYS:
                self.act_mash_count += 1
                if self.game.audio:
                    self.game.audio.play('select')

        done = (self.act_mash_count >= self.act_mash_target
                or self.act_mash_timer >= self.act_mash_window)
        if done:
            success = self.act_mash_count >= self.act_mash_target
            if success:
                self._check_spare_step(self.act_current_name)
            else:
                locked_key = f"{self.act_current_name}_locked_text"
                text = self.m.get(
                    locked_key,
                    f"* You tried to {self.act_current_name},\n"
                    f"  but lost your nerve.\n"
                    f"  ({self.act_mash_count}/{self.act_mash_target})")
                self.tw = Typewriter(text)
            self.state = S.ACT_RESULT

    # ── Death animation ──────────────────────────────────────

    def _start_death_anim(self):
        """Kick off the soul-shatter sequence before the Game Over screen."""
        self.state = S.DEATH_ANIM
        self.death_timer = 0.0
        self.soul_shards = []
        # Freeze any bullets / hazards — visuals-only from here on
        self.bullets = []
        self.hazards = []
        if self.game.audio:
            self.game.audio.stop_bgm()
            # A short 'hit' on freeze, then the full 'death' wail at the
            # actual crack — aligns audio with the visual shatter.
            self.game.audio.play('hit')
        self._trigger_shake(0.25, 2)

    def _spawn_soul_shards(self):
        """Burst shards outward from the last soul position."""
        # 8 shards evenly spaced, alternating hearts and dashes
        chars = ['♥', '♡', '·', '♥', '♡', '·', '♥', '♡']
        for i in range(8):
            angle = i * (math.pi * 2 / 8) + random.uniform(-0.15, 0.15)
            # Negative y is up — give a bias upward for dramatic arc
            speed = random.uniform(8.0, 14.0)
            shard = SoulShard(self.soul_x, self.soul_y, angle, speed,
                              char=chars[i])
            # Lift the initial upward velocity a touch
            shard.vy -= 3.0
            self.soul_shards.append(shard)

    def _upd_death_anim(self, dt, keys):
        self.death_timer += dt
        # Crack point: shatter and spawn shards at ~0.35s.
        if self.death_timer >= 0.35 and not self.soul_shards:
            self._spawn_soul_shards()
            self._trigger_shake(0.55, 4)
            if self.game.audio:
                self.game.audio.play('death')

        for s in self.soul_shards:
            s.update(dt)
        self.soul_shards = [s for s in self.soul_shards if not s.done]

        # After 1.5s, hand off to the Game Over typewriter.
        if self.death_timer >= 1.5:
            self.state = S.GAME_OVER
            self.tw = Typewriter(
                "* Segmentation fault.\n\n"
                "  Your process has\n"
                "  terminated.\n\n"
                "  GAME OVER")

    # ── Game-over menu ────────────────────────────────────────

    def _gg_options(self):
        """Return the list of game-over options, filtering by availability."""
        from save_system import save_exists
        opts = []
        if save_exists():
            opts.append(("RETRY", "Reload last save"))
        opts.append(("TITLE", "Back to title screen"))
        opts.append(("QUIT",  "Exit the game"))
        return opts

    def _upd_gg_menu(self, dt, keys):
        opts = self._gg_options()
        for k in keys:
            if k in UP_KEYS or k in LEFT_KEYS:
                self.gg_sel = (self.gg_sel - 1) % len(opts)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS or k in RIGHT_KEYS:
                self.gg_sel = (self.gg_sel + 1) % len(opts)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                choice = opts[self.gg_sel][0]
                if choice == "RETRY":
                    self._gg_retry()
                elif choice == "TITLE":
                    self._gg_to_title()
                elif choice == "QUIT":
                    self.game.running = False
                break

    def _gg_retry(self):
        """Reload the save and drop into its exploration zone."""
        from save_system import load_game
        from exploration import ExplorationScene
        if load_game(self.game):
            self.game.change_scene(
                ExplorationScene(self.game, self.game.current_zone))
        else:
            # Shouldn't happen (RETRY only shown if save_exists), but guard.
            self._gg_to_title()

    def _gg_to_title(self):
        from title import TitleScene
        self.game.change_scene(TitleScene(self.game))

    # ── ITEM ─────────────────────────────────────────────────

    def _upd_item_menu(self, dt, keys):
        inv = self.game.inventory
        if not inv:
            self.state = S.MENU
            return

        for k in keys:
            if k in UP_KEYS:
                self.item_sel = (self.item_sel - 1) % len(inv)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.item_sel = (self.item_sel + 1) % len(inv)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                result = use_item(self.game, self.item_sel)
                if result:
                    value, msg, item_type = result
                    self.tw = Typewriter(msg)
                    self.state = S.ITEM_RESULT
                    if item_type == "heal":
                        if self.game.audio:
                            self.game.audio.play('heal')
                    elif item_type in ("combat_buff", "buf_restore", "key_item"):
                        if self.game.audio:
                            self.game.audio.play('select')
                break
            elif k in CANCEL_KEYS:
                self.state = S.MENU
                break

    # ── BUF Abilities ─────────────────────────────────────────

    def _upd_buf_menu(self, dt, keys):
        for k in keys:
            if k in UP_KEYS:
                self.buf_sel = (self.buf_sel - 1) % len(BUF_ABILITIES)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in DOWN_KEYS:
                self.buf_sel = (self.buf_sel + 1) % len(BUF_ABILITIES)
                if self.game.audio:
                    self.game.audio.play('select')
            elif k in CONFIRM_KEYS:
                self._use_buf_ability()
                break
            elif k in CANCEL_KEYS:
                self.state = S.MENU
                break

    def _use_buf_ability(self):
        ability = BUF_ABILITIES[self.buf_sel]
        cost = ability["cost"]
        if self.game.player_buf < cost:
            self.tw = Typewriter(
                f"* Not enough BUF.\n"
                f"  Need {cost}, have {self.game.player_buf}.")
            self.state = S.ACT_RESULT
            return

        self.game.player_buf -= cost
        name = ability["name"]

        if name == "Shield":
            self.buf_shield = True
            self.tw = Typewriter(
                "* > SHIELD ACTIVATED\n"
                "  Buffer shield absorbs\n"
                "  the next hit.")
        elif name == "Slow":
            self.buf_slow_timer = 2.0
            self.tw = Typewriter(
                "* > PROCESS SLOWDOWN\n"
                "  Enemy attacks decelerate\n"
                "  for 2 seconds.")
        elif name == "Predict":
            self.buf_scan_timer = self.m["attack_duration"] + 0.5
            self.buf_scan_cols = []
            self.tw = Typewriter(
                "* > PREDICTION BUFFERED\n"
                "  Safe cells will be\n"
                "  marked during the next\n"
                "  attack.")

        self.state = S.ACT_RESULT

    # ── Enemy Turn ───────────────────────────────────────────

    def _start_enemy_turn(self):
        self.turn += 1

        # Boss phase detection
        if self.is_boss:
            hp_ratio = self.m_hp / max(self.m["max_hp"], 1)
            if hp_ratio > 0.6 and self.turn < 4:
                self.boss_phase = "firewall"
            elif hp_ratio > 0.3 or self.turn < 7:
                self.boss_phase = "storm"
            else:
                self.boss_phase = "panic"

            # Phase-specific attack text
            attack_texts = self.m.get("attack_texts", {})
            if self.spare_weakening and self.boss_phase == "panic":
                atk_txt = attack_texts.get("weakening", self.m["attack_text"])
            else:
                atk_txt = attack_texts.get(self.boss_phase, self.m["attack_text"])
        else:
            attack_sequence = self.m.get("attack_sequence_texts")
            if attack_sequence:
                atk_txt = attack_sequence[min(self.turn - 1,
                                              len(attack_sequence) - 1)]
            else:
                atk_txt = self.m["attack_text"]

        rule, read = self._attack_guide_for_current_turn()
        self.current_attack_rule = rule
        self.current_attack_read = read

        txt = atk_txt
        if rule or read:
            txt += "\n\n"
            if rule:
                txt += f"* RULE: {rule}"
            if read:
                if rule:
                    txt += "\n"
                txt += f"  READ: {read}"

        self.tw = Typewriter(txt)
        self.state = S.ENEMY_TURN_MSG

    def _attack_guide_for_current_turn(self):
        """Return the current attack's RULE/READ pair."""
        if self.is_boss:
            phase_guides = self.m.get("attack_phase_guides", {})
            guide = phase_guides.get(self.boss_phase, {})
            return (
                guide.get("rule", self.m.get("attack_rule", "")),
                guide.get("read", self.m.get("attack_read", "")),
            )

        rules = self.m.get("attack_rule_sequence")
        reads = self.m.get("attack_read_sequence")
        idx = max(0, self.turn - 1)
        rule = (
            rules[min(idx, len(rules) - 1)]
            if rules else self.m.get("attack_rule", "")
        )
        read = (
            reads[min(idx, len(reads) - 1)]
            if reads else self.m.get("attack_read", "")
        )
        return rule, read

    def _start_bullet_hell(self):
        self.state = S.ENEMY_ATTACK
        self.soul_x = self.arena_w // 2
        self.soul_y = self.arena_h - 2
        self.bullets = []
        self.hazards = []
        self.bullet_timer = 0.0
        self.attack_timer = 0.0
        self.invuln = 0.0
        self.bullet_spawn_count = 0
        # Track hit-free phase for BUF regen and Null survival spare.
        self.hitless_turn = True
        # Reset per-phase streak timing so survival doesn't bleed across
        # turns (leftover clock could grant a free dodge at phase start).
        self.streak_clock = 0.0
        # Play monster's attack start sound
        atk_snd = self.m.get("atk_sound")
        if atk_snd and self.game.audio:
            self.game.audio.play(atk_snd)

    def _upd_attack(self, dt, keys):
        self.attack_timer += dt
        self.invuln = max(0.0, self.invuln - dt)

        # Dodge streak: +1 per 1.2s of hitless survival during attack.
        self.streak_clock += dt
        if self.streak_clock >= 1.2:
            self.streak_clock -= 1.2
            self.dodge_streak += 1
            self.peak_streak = max(self.peak_streak, self.dodge_streak)
            self.streak_flash = 0.35
            # Every 5 dodges: free BUF refill as a reward.
            if self.dodge_streak % 5 == 0 and self.dodge_streak > self.streak_bonus_shown:
                self.streak_bonus_shown = self.dodge_streak
                self.game.player_buf = min(
                    self.game.player_max_buf, self.game.player_buf + 1)
                self.float_nums.append(
                    FloatingNumber(self.arena_w // 2, 1,
                                   '+BUF', color='buf_full', big=True,
                                   lifetime=1.1))
                if self.game.audio:
                    self.game.audio.play('streak')

        # BUF ability timers
        self.buf_slow_timer = max(0.0, self.buf_slow_timer - dt)
        self.buf_scan_timer = max(0.0, self.buf_scan_timer - dt)

        if self.attack_timer >= self.attack_duration:
            self.state = S.TURN_END
            return

        # Soul movement
        move_x, move_y = 0, 0
        for k in keys:
            if k in UP_KEYS:
                move_y = -1
            if k in DOWN_KEYS:
                move_y = 1
            if k in LEFT_KEYS:
                move_x = -1
            if k in RIGHT_KEYS:
                move_x = 1

        self.soul_x = max(0, min(self.arena_w - 1, self.soul_x + move_x))
        self.soul_y = max(0, min(self.arena_h - 1, self.soul_y + move_y))

        # Difficulty-scaled bullet parameters
        speed_mult = get_difficulty_mod(self.game, "bullet_speed_mult")
        rate_mult = get_difficulty_mod(self.game, "bullet_rate_mult")

        # BUF Slow: halve bullet speed
        if self.buf_slow_timer > 0:
            speed_mult *= 0.5

        # Escalation: attacks intensify as they progress
        progress = min(1.0, self.attack_timer / self.attack_duration)

        # Boss weakening: slow bullets when spare is unlocked
        if self.spare_weakening:
            weaken_turns = self.turn - self.weaken_start_turn
            weaken_factor = min(1.0, weaken_turns / 3.0)
            speed_mult *= (1.0 - 0.4 * weaken_factor)

        # Spawn bullets/hazards based on pattern
        pattern = self.m.get("bullet_pattern", "default")
        rate = self.m["bullet_rate"] * rate_mult * (1.0 - 0.45 * progress)
        self.bullet_timer += dt
        while self.bullet_timer >= rate:
            self.bullet_timer -= rate
            if pattern == "daemon":
                self._spawn_daemon(speed_mult, progress)
            elif pattern == "tears":
                self._spawn_tears(speed_mult, progress)
            elif pattern == "blink":
                self._spawn_blink(progress)
            elif pattern == "echo":
                self._spawn_echo(speed_mult, progress)
            elif pattern == "bounce":
                self._spawn_bounce(speed_mult, progress)
            elif pattern == "expand":
                self._spawn_expand(progress)
            elif pattern == "electric":
                self._spawn_electric(speed_mult, progress)
            else:
                self._spawn_default(speed_mult)
            # Play bullet spawn sound every other spawn to avoid spam
            self.bullet_spawn_count += 1
            if self.bullet_spawn_count % 2 == 0:
                blt_snd = self.m.get("bullet_sound")
                if blt_snd and self.game.audio:
                    self.game.audio.play(blt_snd)

        # Update bullets
        for b in self.bullets:
            b.update(dt)

        # Optional bounce: only bullets that explicitly carry bounce charges
        # should rebound. Older Daemon bullets all bounced implicitly, which
        # made phase rules hard to read.
        if pattern == "daemon":
            for b in self.bullets:
                if b.bounces > 0:
                    if b.x <= 0 and b.vx < 0:
                        b.vx = -b.vx * 1.2
                        b.x = 0
                        b.bounces -= 1
                    elif b.x >= self.arena_w - 1 and b.vx > 0:
                        b.vx = -b.vx * 1.2
                        b.x = self.arena_w - 1
                        b.bounces -= 1
                    if b.y <= 0 and b.vy < 0:
                        b.vy = -b.vy * 1.2
                        b.y = 0
                        b.bounces -= 1
                    elif b.y >= self.arena_h - 1 and b.vy > 0:
                        b.vy = -b.vy * 1.2
                        b.y = self.arena_h - 1
                        b.bounces -= 1

        # Update hazards
        for h in self.hazards:
            h.update(dt)
        # Chain spawn: blobs spawn a smaller child when they start shrinking
        # Child offset is predictable: +4 horizontal or +2 vertical
        new_hazards = []
        for h in self.hazards:
            if (isinstance(h, BlobHazard) and h.can_branch
                    and h.timer >= 0 and not h.growing
                    and not h.spawned_child):
                h.spawned_child = True
                # Alternate between horizontal and vertical offset
                if h.cx < self.arena_w // 2:
                    ox, oy = 4, 0   # leak rightward
                else:
                    ox, oy = 0, 2   # leak downward
                cx = max(1, min(self.arena_w - 2, h.cx + ox))
                cy = max(0, min(self.arena_h - 1, h.cy + oy))
                new_hazards.append(
                    BlobHazard(cx, cy, lifetime=1.5, max_radius=1,
                               warning_time=0.25))
        self.hazards.extend(new_hazards)
        self.hazards = [h for h in self.hazards if not h.done]

        # Remove off-screen bullets
        self.bullets = [b for b in self.bullets
                        if -1 <= b.x <= self.arena_w and -1 <= b.y <= self.arena_h + 1]
        # Collision check (sweep from prev position to current position)
        if self.invuln <= 0:
            hit = False
            dmg_mult = get_difficulty_mod(self.game, "enemy_damage_mult")

            for b in self.bullets:
                if self._sweep_hit(b, self.soul_x, self.soul_y):
                    hit = True
                    break

            if not hit:
                for h in self.hazards:
                    if isinstance(h, BlinkHazard):
                        if h.active and h.x == self.soul_x and h.y == self.soul_y:
                            hit = True
                            break
                    elif isinstance(h, BlobHazard):
                        for (hx, hy) in h.cells():
                            if hx == self.soul_x and hy == self.soul_y:
                                hit = True
                                break
                        if hit:
                            break

            if hit and self.buf_shield:
                # BUF Shield absorbs the hit, but being hit still breaks
                # perfect-dodge rewards and Null's endurance proof.
                self.buf_shield = False
                self.hitless_turn = False
                if self.dodge_streak > 0:
                    self.dodge_streak = 0
                    self.streak_bonus_shown = 0
                self.streak_clock = 0.0
                self.invuln = 0.4
                self.hit_flash = 0.15
                if self.game.audio:
                    self.game.audio.play('select')
                hit = False

            if hit:
                self.hitless_turn = False
                if self.dodge_streak > 0:
                    self.dodge_streak = 0
                    self.streak_bonus_shown = 0
                self.streak_clock = 0.0
                # Damage scales with the monster's ATK stat.
                m_atk = self.m.get("atk", 4)
                base_dmg = m_atk
                dmg_total = max(1, int(base_dmg * dmg_mult))
                # Player defense bonus from items (Firewall Shard).
                dmg_total = max(1, dmg_total - self.game.combat_def_bonus)
                # Buffer absorbs damage first
                dmg = dmg_total
                if self.game.player_buf > 0:
                    buf_absorb = min(self.game.player_buf, dmg)
                    self.game.player_buf -= buf_absorb
                    dmg -= buf_absorb
                if dmg > 0:
                    self.game.player_hp = max(0, self.game.player_hp - dmg)
                    # Red damage number at the soul position (arena-local).
                    self.float_nums.append(
                        FloatingNumber(self.soul_x, self.soul_y,
                                       f'-{dmg}', color='damage', big=True))
                    self._trigger_shake(0.40, 3)
                elif dmg_total > 0:
                    # All damage absorbed by buffer — HP is safe, but the
                    # collision still breaks perfect-dodge rewards.
                    self.float_nums.append(
                        FloatingNumber(self.soul_x, self.soul_y,
                                       'BUF', color='buf_full'))
                    self._trigger_shake(0.18, 1)
                self.invuln = 0.65
                self.hit_flash = 0.3
                if self.game.audio:
                    self.game.audio.play('hit')
                if self.game.player_hp <= 0:
                    self._start_death_anim()

    @staticmethod
    def _sweep_hit(b, sx, sy):
        """True if bullet's segment this frame crossed the soul cell.

        Samples the line from (prev_x, prev_y) to (x, y) densely enough
        that no cell is skipped even at the highest bullet speeds.
        """
        dx = b.x - b.prev_x
        dy = b.y - b.prev_y
        steps = max(1, int(max(abs(dx), abs(dy)) * 2) + 1)
        for i in range(steps + 1):
            t = i / steps
            bx = int(round(b.prev_x + dx * t))
            by = int(round(b.prev_y + dy * t))
            if bx == sx and by == sy:
                return True
        return False

    def _spawn_default(self, speed_mult):
        """Default random vertical/horizontal bullet pattern."""
        bx = random.randint(0, self.arena_w - 1)
        speed = (self.m["bullet_speed"] + random.uniform(-1, 1)) * speed_mult
        if random.random() < 0.15:
            side = random.choice([-1, 1])
            bx = 0 if side == 1 else self.arena_w - 1
            self.bullets.append(Bullet(bx, random.randint(0, self.arena_h - 1),
                                       vx=speed * side, vy=0))
        else:
            self.bullets.append(Bullet(bx, -1, vy=speed))

    def _spawn_tears(self, speed_mult, progress=0.0):
        """Null sink: falling curtains with one readable gap.

        The lesson is stillness and recognition. Early curtains have a
        generous gap; later curtains narrow and add inward pull, but every
        wave keeps the same "find the absence" rule.
        """
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult

        curtain_wave = sc // 2
        gap_size = 7 if progress < 0.34 else (6 if progress < 0.67 else 5)
        if self.null_survival_pending:
            gap_size += 1
        gap_center = int(
            self.arena_w / 2
            + math.sin(curtain_wave * 0.65) * (self.arena_w / 2 - 5)
        )
        gap_center = max(gap_size // 2,
                         min(self.arena_w - 1 - gap_size // 2, gap_center))
        gap_start = gap_center - gap_size // 2
        gap_end = gap_center + gap_size // 2 + 1

        if sc % 2 == 0:
            for col in range(self.arena_w):
                if col < gap_start or col >= gap_end:
                    self.bullets.append(Bullet(col, -1, vx=0, vy=speed))
        else:
            # Quiet beats: a few lost bytes fall outside the safe gap.
            for offset in (-10, 0, 10):
                col = (gap_center + offset) % self.arena_w
                if gap_start <= col < gap_end:
                    col = (col + gap_size + 2) % self.arena_w
                self.bullets.append(Bullet(col, -1, vx=0, vy=speed * 0.65))

            # Late pressure pulls inward, but in fixed rows rather than at random.
            if progress > 0.55 and sc % 4 == 1:
                row = (curtain_wave * 2) % self.arena_h
                self.bullets.append(Bullet(0, row, vx=speed * 0.55, vy=0))
                self.bullets.append(
                    Bullet(self.arena_w - 1, row, vx=-speed * 0.55, vy=0))

    def _spawn_blink(self, progress=0.0):
        """Cursor shell: typed command chunks, then the blinking caret."""
        sc = self.bullet_spawn_count
        typed = self.spare_progress.get("0:type", 0)

        row = (self.turn + sc // 3) % self.arena_h
        command_chunks = [
            (1, 7),    # "$ "
            (10, 8),   # command
            (22, 11),  # argument / path
        ]
        chunk_count = 1
        if self.turn >= 2 or progress > 0.34:
            chunk_count = 2
        if self.turn >= 3 or progress > 0.67:
            chunk_count = 3

        start_x, seg_len = command_chunks[sc % chunk_count]
        warning_time = 0.42 + 0.08 * min(2, typed)
        cycles = 2 if typed < 2 else 1
        for i in range(seg_len):
            x = start_x + i
            if 0 <= x < self.arena_w:
                self.hazards.append(
                    BlinkHazard(x, row, on_time=0.42, off_time=0.22,
                                cycles=cycles, warning_time=warning_time))

        # Late fight route: the caret blinks down one column. It reads as
        # Cursor's identity, not a random extra projectile.
        if self.turn >= 3 and sc % 3 == 2:
            caret_x = (4 + (sc // 3) * 7) % self.arena_w
            for y in range(self.arena_h):
                self.hazards.append(
                    BlinkHazard(caret_x, y, on_time=0.22, off_time=0.35,
                                cycles=1, warning_time=0.35))

    def _spawn_bounce(self, speed_mult, progress=0.0):
        """Ping echo: horizontal packets from alternating walls."""
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult

        # Alternate left/right wall each spawn
        from_left = (sc % 2 == 0)
        bx = 0 if from_left else self.arena_w - 1
        vx = speed if from_left else -speed

        # Deterministic row — skips rows for natural gaps
        row = (sc * 2) % self.arena_h

        # Pure horizontal packet
        self.bullets.append(Bullet(bx, row, vx=vx, vy=0))

        # Progress > 0.4: second packet on adjacent row with slight drift
        if progress > 0.4:
            adj_row = (row + 1) % self.arena_h
            drift = 0.5 if from_left else -0.5
            self.bullets.append(Bullet(bx, adj_row, vx=vx, vy=drift))

        # Progress > 0.7: aimed packet at player's row (slower)
        if progress > 0.7:
            aimed_bx = 0 if not from_left else self.arena_w - 1
            aimed_vx = (speed * 0.7) if not from_left else -(speed * 0.7)
            self.bullets.append(
                Bullet(aimed_bx, self.soul_y, vx=aimed_vx, vy=0))

    def _spawn_echo(self, speed_mult, progress=0.0):
        """Ping echo: request, reply, then route hops.

        The player reads network direction: packets are always horizontal
        and rows are deterministic, so the solution is vertical movement.
        """
        sc = self.bullet_spawn_count
        reply_count = self.spare_progress.get("0:reply", 0)
        trace_done = self.spare_progress.get("1:trace", 0) > 0
        protocol_slow = max(0.68, 1.0 - 0.12 * reply_count)
        if trace_done:
            protocol_slow *= 0.85
        speed = self.m["bullet_speed"] * speed_mult * protocol_slow

        # Row cycling: every-other-row first, then fill the gaps.
        _ROW_ORDER = [0, 2, 4, 1, 3, 5]
        row = _ROW_ORDER[sc % len(_ROW_ORDER)]
        row = row % self.arena_h

        # Alternate walls each spawn
        from_left = (sc % 2 == 0)
        bx = 0 if from_left else self.arena_w - 1
        vx = speed if from_left else -speed

        # Outbound packet
        self.bullets.append(Bullet(bx, row, vx=vx, vy=0))

        if self.turn >= 2 or progress > 0.35 or reply_count:
            reply_bx = self.arena_w - 1 if from_left else 0
            reply_vx = -vx * 0.8
            self.bullets.append(Bullet(reply_bx, row, vx=reply_vx, vy=0))

        # Route hops appear as paired TTL probes in neighbouring rows.
        # They are slower and never aimed, so Trace feels like reading a route.
        if (self.turn >= 3 or progress > 0.65) and sc % 2 == 0:
            hop_row = (row + 1 + (sc // 2) % 2) % self.arena_h
            probe_bx = self.arena_w - 1 if from_left else 0
            probe_vx = -vx * 0.58
            self.bullets.append(Bullet(probe_bx, hop_row, vx=probe_vx, vy=0))

    # Fixed blob spawn positions for predictable cycling (spread for variety)
    _BLOB_POSITIONS = [
        (19, 3),   # center
        (8, 2),    # left-upper
        (30, 4),   # right-lower
        (14, 0),   # top-left (forces player south)
        (24, 5),   # bottom-right (forces player north)
    ]

    def _spawn_expand(self, progress=0.0):
        """Blob expand: fixed-cycle positions with predictable growth.

        Contain-weakening: if player has contained ×2, new blobs
        spawn with max_radius=1 instead of 2.
        Late phase: secondary blob at +2 in cycle (starts at 0.4).
        """
        sc = self.bullet_spawn_count

        # Contain-weakening: shrink blobs if player has contained enough
        contained = self.spare_progress.get("0:contain", 0) >= 2
        main_radius = 1 if contained else 2
        lifetime = 1.65 if contained else 1.95

        pos_idx = sc % 5
        cx, cy = self._BLOB_POSITIONS[pos_idx]
        self.hazards.append(
            BlobHazard(cx, cy, lifetime=lifetime, max_radius=main_radius,
                       warning_time=0.45))

        # Progress > 0.4: secondary SMALLER blob at position +2 in cycle
        if (self.turn >= 2 or progress > 0.4) and sc % 2 == 1:
            sec_idx = (pos_idx + 2) % 5
            cx2, cy2 = self._BLOB_POSITIONS[sec_idx]
            self.hazards.append(
                BlobHazard(cx2, cy2, lifetime=1.45, max_radius=1,
                           warning_time=0.35))

    def _spawn_electric(self, speed_mult, progress=0.0):
        """Pkmn ROM: warn scanline columns, then replay them exactly."""
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult
        rom_cols = [3, 12, 21, 30, 7, 25]
        wave = sc // 2
        bx = rom_cols[wave % len(rom_cols)]
        columns = [bx]
        if self.turn >= 2 or progress > 0.55:
            columns.append(rom_cols[(wave + 3) % len(rom_cols)])

        if sc % 2 == 0:
            for col in columns:
                self.hazards.append(
                    Telegraph([(col, y) for y in range(self.arena_h)],
                              lifetime=0.48))
            return

        decoded = self.spare_progress.get("0:decode", 0)
        bolt_speed = speed * max(0.78, 1.0 - 0.08 * decoded)
        for idx, col in enumerate(columns):
            self.bullets.append(
                Bullet(col, -1, vx=0, vy=bolt_speed * (0.9 if idx else 1.0)))

    # ── Daemon boss patterns ────────────────────────────────

    def _spawn_daemon(self, speed_mult, progress):
        """Dispatch to phase-specific daemon pattern."""
        if self.boss_phase == "firewall":
            self._spawn_daemon_firewall(speed_mult, progress)
        elif self.boss_phase == "storm":
            self._spawn_daemon_storm(speed_mult, progress)
        else:
            self._spawn_daemon_panic(speed_mult, progress)

    def _spawn_daemon_firewall(self, speed_mult, progress):
        """Phase 1: firewall rules — row filters with a clear allow-list gap."""
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult

        if sc % 2 == 0:
            # Blink line sweeping top -> bottom.
            row = (sc // 2) % self.arena_h
            gap_center = self.arena_w // 2 + ((sc // 2) * 5) % 14 - 7
            gap_center = max(3, min(self.arena_w - 4, gap_center))
            gap_size = 7 if progress < 0.5 else 6
            for x in range(self.arena_w):
                if abs(x - gap_center) > gap_size // 2:
                    self.hazards.append(
                        BlinkHazard(x, row, on_time=0.42, off_time=0.24,
                                    cycles=2, warning_time=0.42))
        else:
            # Rule packets fall through the allowed columns from the last sweep.
            for offset in (-5, 5):
                col = (self.arena_w // 2 + (sc * 4) + offset) % self.arena_w
                self.bullets.append(
                    Bullet(col, -1, vx=0, vy=speed * 0.72))

    def _spawn_daemon_storm(self, speed_mult, progress):
        """Phase 2: fork storm — Ping rows plus bounded heap pressure."""
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult

        # Deterministic rows from left and right walls.
        row_left = sc % self.arena_h
        row_right = (sc + 3) % self.arena_h

        self.bullets.append(Bullet(0, row_left, vx=speed, vy=0))
        self.bullets.append(Bullet(self.arena_w - 1, row_right, vx=-speed, vy=0))

        # Later storms fork into adjacent rows.
        if progress > 0.4:
            row_left2 = (row_left + 2) % self.arena_h
            row_right2 = (row_right + 2) % self.arena_h
            self.bullets.append(Bullet(0, row_left2, vx=speed * 0.86, vy=0))
            self.bullets.append(
                Bullet(self.arena_w - 1, row_right2, vx=-speed * 0.86, vy=0))

        # Every 3rd wave: bounded memory pressure, telegraphed and non-branching.
        if sc % 3 == 0:
            self.hazards.append(
                BlobHazard(self.arena_w // 2, self.arena_h // 2,
                           lifetime=1.45, max_radius=1,
                           warning_time=0.35, can_branch=False))

        # Every 5th wave: a scheduled interrupt from above.
        if sc % 5 == 0:
            target_vx = speed * 0.5 if self.soul_x > self.arena_w // 2 else -speed * 0.5
            self.bullets.append(
                Bullet(self.arena_w // 2, -1, vx=target_vx, vy=speed * 0.7))

    def _spawn_daemon_panic(self, speed_mult, progress):
        """Phase 3: kernel panic — Null curtains plus process interrupts."""
        sc = self.bullet_spawn_count
        speed = self.m["bullet_speed"] * speed_mult

        # Weakening adjustments
        if self.spare_weakening:
            weaken_turns = self.turn - self.weaken_start_turn
            weaken_factor = min(1.0, weaken_turns / 3.0)
            gap_size = max(4, int(4 + 4 * weaken_factor))
            speed *= max(0.65, 1.0 - 0.35 * weaken_factor)
            track_player = True
        else:
            gap_size = 4
            track_player = False

        is_curtain = (sc % 2 == 0)

        if is_curtain:
            # Curtain wall with gap
            if track_player:
                gap_center = self.soul_x
            else:
                gap_center = int(
                    self.arena_w / 2
                    + math.sin(sc * 0.7) * (self.arena_w / 2 - 4)
                )
            gap_center = max(gap_size // 2, min(self.arena_w - 1 - gap_size // 2,
                                                 gap_center))
            gap_start = gap_center - gap_size // 2
            gap_end = gap_center + gap_size // 2 + 1

            for col in range(self.arena_w):
                if col < gap_start or col >= gap_end:
                    self.bullets.append(Bullet(col, -1, vx=0, vy=speed))
        else:
            # Between curtains: process interrupts from both walls.
            row_l = sc % self.arena_h
            row_r = (sc + 2) % self.arena_h
            pkt_speed = speed * (0.6 if self.spare_weakening else 1.0)
            self.bullets.append(
                Bullet(0, row_l, vx=pkt_speed, vy=0, bounces=0))
            self.bullets.append(
                Bullet(self.arena_w - 1, row_r, vx=-pkt_speed, vy=0,
                       bounces=0))

            # Non-weakening: one direct interrupt at the current row.
            if not self.spare_weakening:
                aimed_side = 1 if sc % 4 < 2 else -1
                aimed_bx = 0 if aimed_side == 1 else self.arena_w - 1
                self.bullets.append(
                    Bullet(aimed_bx, self.soul_y,
                           vx=pkt_speed * aimed_side, vy=0, bounces=0))

    def _upd_turn_end(self, dt, keys):
        g = self.game
        # Buffer regen: +1 per turn, but ONLY if the player took no damage.
        # Rewards perfect dodging and prevents infinite Slow-stalling.
        if self.hitless_turn:
            g.player_buf = min(g.player_max_buf, g.player_buf + 1)

        was_spare = self.spare_ok
        protocol_result = self.protocol.on_turn_end(self.turn, self.hitless_turn)
        self._sync_protocol_state()
        if self.spare_ok and not was_spare and self.is_boss:
            self.spare_weakening = True
            self.weaken_start_turn = self.turn
        if protocol_result and protocol_result.text:
            self.tw = Typewriter(protocol_result.text)
            # S.INTRO's advance handler returns to the menu after [Z].
            self.state = S.INTRO
            return

        self.state = S.MENU
        self.menu_sel = 0

    def _finish_battle(self, killed=False):
        """Handle post-battle rewards and transition."""
        exp_gained = 0
        gold_gained = self.m["gold"]

        dropped = None
        if killed:
            exp_gained = self.m["exp"]
            self.game.gold += gold_gained
            self.levelup_msgs = gain_exp(self.game, exp_gained)
            self.game.kill_count += 1
            if self.m_name == "Daemon":
                self.game.flags["daemon_killed"] = True
            # Killing-only drop: rewards engagement, denies pacifist.
            drop_name = self.m.get("drop_on_kill")
            if drop_name:
                from items import add_item
                if add_item(self.game, drop_name):
                    dropped = drop_name
        else:
            # Spare: 50% gold, no EXP. Keeps pacifist viable.
            self.game.gold += gold_gained // 2
            self.game.spare_count += 1
            if self.m_name == "Daemon":
                self.game.flags["daemon_spared"] = True

        self.game.flags[self._protocol_flag()] = True
        self.game.flags[f"{self._protocol_flag()}_{'killed' if killed else 'spared'}"] = True

        # Mark monster as defeated
        if self.zone_name and self.monster_pos:
            key = f"{self.zone_name}:{self.monster_pos[0]},{self.monster_pos[1]}"
            self.game.defeated_monsters.add(key)

        if self.game.audio:
            self.game.audio.stop_bgm()

        # Always build the summary — it plays after any level-up messages.
        spare_bonus = gold_gained // 2 if not killed else 0
        self.battle_summary = {
            "killed": killed,
            "monster": self.m_name,
            "exp": exp_gained,
            "gold": gold_gained if killed else spare_bonus,
            "peak_streak": self.peak_streak,
            "is_boss": self.is_boss,
            "drop": dropped,
            "protocol": self.m.get("protocol_name", self.m_name),
            "flavor": (
                "You feel something heavy in your chest."
                if killed else
                "You feel a quiet sense of relief."
            ),
        }

        if self.levelup_msgs:
            if self.game.audio:
                self.game.audio.play('levelup')
            self.tw = Typewriter(self.levelup_msgs.pop(0))
            self.state = S.LEVELUP
        else:
            self._enter_summary_state()

    def _enter_summary_state(self):
        """Animate the victory/mercy panel (state S.ENDING)."""
        self.summary_reveal = 0.0
        # Keep a typewriter alive so input plumbing stays consistent.
        self.tw = Typewriter("")
        self.tw.done = True
        self.state = S.ENDING

    def _return_to_exploration(self):
        """Go back to exploration scene."""
        from exploration import ExplorationScene
        self.game.change_scene(
            ExplorationScene(self.game, self.zone_name or self.game.current_zone))

    # ── Render ────────────────────────────────────────────────

    def render(self, r):
        # Game Over menu takes the whole screen — short-circuit render.
        if self.state == S.GAME_OVER_MENU:
            self._draw_gg_menu(r)
            return
        # Death animation: draw monster art + arena-local shatter only.
        # We skip the HP/menu rows so the live UI doesn't cover the anim.
        if self.state == S.DEATH_ANIM:
            self._render_death_frame(r)
            return

        # Dynamic layout: Pkmn sprite is drawn at full resolution (~20 rows)
        # and the UI (textbox/arena) overlays its bottom portion, like Pokemon.
        use_sprite = (self.m_name == "Pkmn" and pkmn_sprite._ready
                      and r.height >= 24)

        monster_y = 1
        if use_sprite:
            # Sprite is ~20 rows.  Place arena so it overlaps the bottom half,
            # leaving the top ~12 rows of sprite visible (head, ears, body).
            sprite_h = pkmn_sprite.height()
            arena_y = monster_y + sprite_h - (self.arena_h + 2)
        else:
            arena_y = 9
        box_h = self.arena_h + 2  # 8
        arena_x = max(1, (r.width - self.arena_w - 2) // 2)
        hp_y = arena_y + box_h
        menu_sep_y = hp_y + 1
        menu_y = menu_sep_y + 1

        # Monster name — flashes yellow (mercy) when the spare is ready,
        # just like Undertale. Null's survival is not yet spare_ok, so it
        # uses the pending-survival colour as a subtler cue.
        name_str = f"* {self.m_name} *"
        if self.spare_ok:
            name_color = 'mercy'
        elif self.null_survival_pending:
            name_color = 'gold_text'
        else:
            name_color = 'monster_name'
        r.put(0, (r.width - len(name_str)) // 2, name_str, name_color, bold=True)

        # Monster HP bar (small, top-right)
        if self.m_hp < self.m["max_hp"]:
            self._draw_monster_hp(r, 0, r.width - 22)

        # Monster art (with damage flash)
        show_art = not (self.m_flash > 0 and int(self.m_flash * 10) % 2 == 0)
        # Vibration offset during CRY state (Gen 1 wild encounter effect)
        vib_x = random.choice([-1, 0, 1]) if self.state == S.CRY else 0
        # Screen shake offset — adds punch to crits and enemy hits.
        if self.shake_timer > 0 and self.shake_mag > 0:
            shake_x = random.randint(-self.shake_mag, self.shake_mag)
            shake_y = random.randint(-self.shake_mag, self.shake_mag) // 2
        else:
            shake_x, shake_y = 0, 0
        vib_x += shake_x
        if use_sprite:
            # Draw full sprite first; the textbox/arena drawn next will
            # naturally overwrite the bottom rows with r.fill() + r.box().
            if show_art:
                pkmn_sprite.draw(r, monster_y + shake_y,
                                 r.width // 2 + vib_x)
        else:
            art = get_art(self.m_name, self.anim_frame)
            if show_art:
                art_color = 'damage' if self.m_flash > 0 else 'monster'
                for i, line in enumerate(art):
                    ax = (r.width - len(line)) // 2 + vib_x
                    r.put(monster_y + i + shake_y, ax, line, art_color)

        # Boss phase indicator — visible whenever the player is deciding
        # or under attack. Hidden during intro and ending states only.
        if self.is_boss and self.state not in (S.INTRO, S.WIN, S.SPARE,
                                               S.GAME_OVER, S.ENDING,
                                               S.LEVELUP, S.CRY):
            phase_label = {
                'firewall': '[PHASE 1 — FIREWALL]',
                'storm':    '[PHASE 2 — STORM]',
                'panic':    '[PHASE 3 — KERNEL PANIC]',
            }.get(self.boss_phase, '')
            if phase_label:
                ph_color = 'ominous' if self.boss_phase == 'panic' else 'monster_name'
                r.put(1, (r.width - len(phase_label)) // 2,
                      phase_label, ph_color, bold=True)

        # State-dependent middle area
        if self.state == S.ENEMY_ATTACK:
            self._draw_arena(r, arena_y, arena_x)
        elif self.state == S.MENU:
            self._draw_protocol_panel(r, arena_y, arena_x)
        elif self.state == S.FIGHT_TIMING:
            self._draw_timing(r, arena_y + 1)
        elif self.state == S.ITEM_MENU:
            self._draw_item_menu(r, arena_y, arena_x)
        elif self.state in (S.INTRO, S.FIGHT_RESULT, S.ACT_RESULT,
                            S.ENEMY_TURN_MSG, S.WIN, S.SPARE,
                            S.GAME_OVER, S.ITEM_RESULT,
                            S.LEVELUP, S.CRY):
            self._draw_textbox(r, arena_y, arena_x)
        elif self.state == S.ENDING:
            self._draw_summary(r, arena_y, arena_x)
        elif self.state == S.ACT_MENU:
            self._draw_act_menu(r, arena_y, arena_x)
        elif self.state == S.BUF_MENU:
            self._draw_buf_menu(r, arena_y, arena_x)
        elif self.state == S.ACT_TIMING:
            self._draw_act_timing(r, arena_y + 1)
        elif self.state == S.ACT_MASH:
            self._draw_act_mash(r, arena_y, arena_x)
        # S.GAME_OVER_MENU and S.DEATH_ANIM handled by early-return
        # dispatch at the top of render() — not reached here.

        # HP + BUF bar (always)
        self._draw_hp(r, hp_y)

        # Menu (always visible, highlighted when active)
        self._draw_menu(r, menu_sep_y, menu_y)

        # Floating damage numbers — drawn last so they overlay everything.
        self._draw_floats(r, monster_y, arena_y, arena_x)

        # Dodge streak counter (only visible during bullet hell).
        if self.state == S.ENEMY_ATTACK and self.dodge_streak > 0:
            self._draw_streak(r, arena_y, arena_x)

    def _draw_floats(self, r, monster_y, arena_y, arena_x):
        for fn in self.float_nums:
            if fn.anchor == 'monster':
                # Rise above the monster art, centred.
                py = monster_y + 4 + int(fn.y)
                px = (r.width - len(fn.text)) // 2 + int(fn.x)
            else:
                # Arena-local coords — relative to inside of arena box.
                py = arena_y + 1 + int(fn.y)
                px = arena_x + 1 + int(fn.x) - (len(fn.text) // 2)
            if py < 0 or py >= r.height:
                continue
            color = fn.color
            if fn.fading:
                color = 'ui_dim'  # fade via dim palette
            text = fn.text
            if fn.big and not fn.fading:
                # Emphasise crits with a small '!' halo
                text = f'!{text}!'
            r.put(py, px, text, color, bold=fn.big)

    def _draw_streak(self, r, arena_y, arena_x):
        label = f'STREAK x{self.dodge_streak}'
        color = 'timing_crit' if self.streak_flash > 0 else 'timing_good'
        bold = self.streak_flash > 0
        # Top-left of arena, inside the box.
        r.put(arena_y, arena_x + 2, label, color, bold=bold)

    def _draw_monster_hp(self, r, y, x):
        bar_w = 16
        ratio = self.m_hp / max(self.m["max_hp"], 1)
        filled = int(bar_w * ratio)
        color = 'hp_full' if ratio > 0.3 else 'hp_low'
        r.put(y, x, '\u2588' * filled, color)
        r.put(y, x + filled, '\u2591' * (bar_w - filled), 'hp_bg')

    def _draw_textbox(self, r, y, ax):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        r.box(y, ax, box_w, box_h, 'ui_border')
        text = self.tw.visible()
        lines = text.split('\n')
        for i, line in enumerate(lines[:box_h - 2]):
            r.put(y + 1 + i, ax + 2, line, 'ui_text')
        if self.tw.done:
            indicator = '>' if int(self.anim_t * 4) % 2 == 0 else ' '
            r.put(y + box_h - 2, ax + box_w - 4, indicator, 'ui_dim')

    def _draw_protocol_panel(self, r, y, ax):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        title = self.m.get("protocol_name", "PROTOCOL")
        border = 'mercy' if self.spare_ok else 'ui_border'
        r.box(y, ax, box_w, box_h, border, title=title[:box_w - 4])

        route = self._protocol_route_line()
        route = f"MERCY: {route}"
        if len(route) > box_w - 4:
            route = f"M: {self._protocol_route_line()}"
        r.put(y + 1, ax + 2, route[:box_w - 4],
              'mercy' if self.spare_ok else 'ui_text',
              bold=self.spare_ok)

        next_line = self._protocol_next_line()
        next_color = 'mercy' if self.spare_ok else (
            'gold_text' if self.null_survival_pending else 'soul')
        r.put(y + 2, ax + 2, next_line[:box_w - 4], next_color,
              bold=not self.spare_ok)

        for i, line in enumerate(self._protocol_progress_lines()[:3]):
            color = 'mercy' if line.startswith("OK") or self.spare_ok else (
                'soul' if line.startswith(">") else 'ui_dim')
            r.put(y + 3 + i, ax + 2, line[:box_w - 4], color,
                  bold=line.startswith(">") or self.spare_ok)

        hint = self.m.get("attack_hint", "")
        if hint:
            r.put(y + box_h - 2, ax + 2,
                  f"ATK: {hint}"[:box_w - 4], 'ui_dim')

    def _draw_timing(self, r, y):
        bar_w = 30
        bx = (r.width - bar_w - 2) // 2

        r.put(y, bx, '> SENDING TERM SIGNAL...', 'ui_text')

        # Bar
        bar_y = y + 1
        r.put(bar_y, bx, '[', 'ui_border')
        r.put(bar_y, bx + bar_w + 1, ']', 'ui_border')

        center = bar_w // 2
        for i in range(bar_w):
            dist = abs(i - center)
            if dist <= 2:
                color = 'timing_crit'
            elif dist <= 6:
                color = 'timing_good'
            else:
                color = 'timing_miss'
            r.put(bar_y, bx + 1 + i, '\u2500', color)

        # Marker
        mp = max(0, min(bar_w - 1, int(self.timing_pos)))
        r.put(bar_y, bx + 1 + mp, '\u2588', 'ui_text', bold=True)

        # Center indicator
        r.put(bar_y + 1, bx + 1 + center, '^', 'timing_crit', bold=True)

        if self.timing_stopped:
            dist = abs(self.timing_pos - center)
            result_y = bar_y + 2
            if self.m.get("invincible"):
                r.put(result_y, bx, '     ...but nothing happened.', 'ui_dim')
            elif dist <= 2:
                r.put(result_y, bx, '     !! CLEAN SIGNAL !!', 'timing_crit', bold=True)
            elif dist <= 6:
                r.put(result_y, bx, '       SIGNAL DELIVERED', 'timing_good', bold=True)
            elif dist <= 10:
                r.put(result_y, bx, '       SIGNAL CLIPPED', 'timing_good')
            else:
                r.put(result_y, bx, '       SIGNAL DRIFTED', 'timing_miss')

    def _draw_act_timing(self, r, y):
        """Render the skill-based ACT timing bar (Ping's Reply)."""
        bar_w = 30
        bx = (r.width - bar_w - 2) // 2

        label = f"> {self.act_current_name.upper()} SIGNAL..."
        r.put(y, bx, label, 'ui_text')

        bar_y = y + 1
        r.put(bar_y, bx, '[', 'ui_border')
        r.put(bar_y, bx + bar_w + 1, ']', 'ui_border')
        center = bar_w // 2
        for i in range(bar_w):
            dist = abs(i - center)
            if dist <= 2:
                color = 'timing_crit'
            elif dist <= 6:
                color = 'timing_good'
            else:
                color = 'timing_miss'
            r.put(bar_y, bx + 1 + i, '─', color)

        mp = max(0, min(bar_w - 1, int(self.act_timing_pos)))
        r.put(bar_y, bx + 1 + mp, '█', 'ui_text', bold=True)
        r.put(bar_y + 1, bx + 1 + center, '^', 'timing_crit', bold=True)

        if self.act_timing_stopped:
            dist = abs(self.act_timing_pos - center)
            msg_y = bar_y + 2
            if dist <= 6:
                r.put(msg_y, bx, '       SIGNAL ACCEPTED', 'timing_good', bold=True)
            else:
                r.put(msg_y, bx, '       SIGNAL LOST', 'timing_miss')
        else:
            hint_y = bar_y + 2
            r.put(hint_y, bx, '    [Z] send when centered', 'ui_dim')

    def _draw_summary(self, r, y, ax):
        """Animated post-battle summary panel.

        Layout (arena box, 6 inner rows):
          row+1: verb line                      (reveal >= 0.15s)
          row+3: EXP / gold                     (reveal >= 0.30s)
          row+4: dodge peak                     (reveal >= 0.45s)
          row+5: [Z] continue indicator         (reveal >= 0.90s)
        Boss flag piggybacks on the box title so no row is wasted on it.
        """
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')

        bs = self.battle_summary or {}
        killed = bs.get("killed", False)
        base_title = "VICTORY" if killed else "MERCY"
        if bs.get("is_boss"):
            base_title = f"{base_title} — BOSS"
        title_color = 'damage' if killed else 'mercy'
        r.box(y, ax, box_w, box_h, title_color,
              title=base_title, double=True)

        t = self.summary_reveal

        # Verb line
        if t >= 0.15:
            verb = "terminated" if killed else "spared"
            line_txt = f"{bs.get('monster', '???')} {verb}."
            r.put(y + 1, ax + 3, line_txt,
                  'ominous' if killed else 'mercy', bold=True)

        # EXP / gold
        if t >= 0.30:
            exp = bs.get("exp", 0)
            gold = bs.get("gold", 0)
            exp_str = f"EXP  +{exp}" if exp > 0 else "EXP  —"
            gold_str = f"$ +{gold}" if gold > 0 else "$ —"
            r.put(y + 3, ax + 3, exp_str,
                  'cycles_text' if exp > 0 else 'ui_dim',
                  bold=exp > 0)
            r.put(y + 3, ax + 16, gold_str,
                  'cycles_text' if gold > 0 else 'ui_dim',
                  bold=gold > 0)

        # Dodge peak (or drop, if there is one — drops trump streak in priority)
        if t >= 0.45:
            drop = bs.get("drop")
            if drop:
                r.put(y + 4, ax + 3,
                      f"DROP  +{drop}",
                      'gold_text', bold=True)
            else:
                peak = bs.get("peak_streak", 0)
                if peak > 0:
                    r.put(y + 4, ax + 3,
                          f"Dodge peak  x{peak}",
                          'timing_good', bold=True)
                else:
                    r.put(y + 4, ax + 3, "No dodge streak.", 'ui_dim')

        if t >= 0.60:
            protocol = bs.get("protocol", "process")
            state = "terminated" if killed else "synced"
            r.put(y + 5, ax + 3,
                  f"Protocol {state}: {protocol}"[:box_w - 6],
                  'ominous' if killed else 'mercy',
                  bold=not killed)

        # Confirm hint (pulsing) on the last inner row
        if t >= 0.90:
            indicator = '>' if int(self.anim_t * 4) % 2 == 0 else ' '
            hint = f"{indicator} [Z] continue"
            r.put(y + box_h - 2, ax + box_w - len(hint) - 2,
                  hint, 'ui_dim')

    def _render_death_frame(self, r):
        """Full-frame render during DEATH_ANIM: monster stays, UI hides."""
        # Monster name (dim)
        name_str = f"* {self.m_name} *"
        r.put(0, (r.width - name_str.__len__()) // 2, name_str,
              'ui_dim', bold=False)

        # Monster art (frozen, dim)
        monster_y = 1
        art = get_art(self.m_name, self.anim_frame)
        for i, line in enumerate(art):
            ax = (r.width - len(line)) // 2
            r.put(monster_y + i, ax, line, 'ui_dim')

        # Arena box + shatter
        arena_y = 9
        arena_x = max(1, (r.width - self.arena_w - 2) // 2)
        self._draw_death_anim(r, arena_y, arena_x)

        # "YOU DIED" hint once the shake has settled a bit
        if self.death_timer > 0.9:
            msg = "..."
            r.put(r.height - 3, (r.width - len(msg)) // 2,
                  msg, 'ominous', bold=True)

    def _draw_death_anim(self, r, y, x):
        """Soul-shatter animation: heart freezes, cracks, shards fly out."""
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2

        # Fade the arena background to black as the death progresses
        t = self.death_timer
        r.fill(y, x, box_w, box_h, ' ', 'flash_black' if t > 0.7 else 'default')
        r.box(y, x, box_w, box_h, 'ominous', double=True)

        # Phase 1 (0 → 0.35s): heart intact, shaking violently
        if t < 0.35:
            # Flicker white every other frame
            flicker = int(t * 40) % 2 == 0
            soul_color = 'flash_white' if flicker else 'damage'
            jx = random.randint(-2, 2)
            jy = random.randint(-1, 1)
            sx = x + 1 + self.soul_x + jx
            sy = y + 1 + self.soul_y + jy
            if y < sy < y + box_h - 1 and x < sx < x + box_w - 1:
                r.put(sy, sx, '♥', soul_color, bold=True)
        else:
            # Phase 2: broken-heart glyph fading at origin + flying shards
            if t < 0.55:
                sx = x + 1 + self.soul_x
                sy = y + 1 + self.soul_y
                if y < sy < y + box_h - 1 and x < sx < x + box_w - 1:
                    r.put(sy, sx, '✗', 'ominous', bold=True)

            for s in self.soul_shards:
                ssx = x + 1 + int(round(s.x))
                ssy = y + 1 + int(round(s.y))
                if y < ssy < y + box_h - 1 and x < ssx < x + box_w - 1:
                    color = 'ui_dim' if s.fading else 'damage'
                    r.put(ssy, ssx, s.char, color, bold=not s.fading)

    def _draw_gg_menu(self, r):
        """Full-screen game over with Retry / Title / Quit options."""
        # Dim everything behind, then draw the menu centered.
        r.fill(0, 0, r.width, r.height, ' ', 'default')

        # Title: SEG FAULT
        title = "SEGMENTATION FAULT"
        ty = max(2, r.height // 3 - 3)
        r.put(ty, (r.width - len(title)) // 2, title,
              'ominous', bold=True)

        sub = f"PID {self.game.player_name} terminated."
        r.put(ty + 2, (r.width - len(sub)) // 2, sub, 'subtitle')

        # Options
        opts = self._gg_options()
        oy = ty + 5
        for i, (label, desc) in enumerate(opts):
            line_y = oy + i * 3
            label_line = f"  {label}  "
            lx = (r.width - len(label_line)) // 2
            if i == self.gg_sel:
                r.put(line_y, lx - 2, '>', 'soul', bold=True)
                r.put(line_y, lx, label_line, 'mercy', bold=True)
                r.put(line_y + 1, (r.width - len(desc)) // 2,
                      desc, 'ui_dim')
            else:
                r.put(line_y, lx, label_line, 'ui_dim')

        # Hint at bottom
        hint = "[W/S] Select   [Z] Confirm"
        r.put(r.height - 2, (r.width - len(hint)) // 2,
              hint, 'ui_dim')

    def _draw_act_mash(self, r, y, ax):
        """Render the mash mini-game (Daemon's Persist)."""
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        r.box(y, ax, box_w, box_h, 'ui_border', title="PERSIST")

        remaining = max(0, self.act_mash_window - self.act_mash_timer)
        r.put(y + 1, ax + 2,
              f'Insist: {self.act_mash_count}/{self.act_mash_target}',
              'ui_text', bold=True)
        r.put(y + 1, ax + box_w - 10, f'{remaining:.1f}s',
              'ui_dim')

        # Progress bar
        bar_w = box_w - 6
        filled = int(bar_w * self.act_mash_count / max(1, self.act_mash_target))
        filled = min(bar_w, filled)
        bar_y = y + 3
        r.put(bar_y, ax + 2, '█' * filled, 'mercy', bold=True)
        r.put(bar_y, ax + 2 + filled, '░' * (bar_w - filled), 'hp_bg')

        # Window countdown bar
        win_filled = int(bar_w * remaining / max(0.01, self.act_mash_window))
        win_filled = max(0, min(bar_w, win_filled))
        win_y = y + 5
        color = 'hp_low' if remaining < 0.6 else 'timing_good'
        r.put(win_y, ax + 2, '█' * win_filled, color)
        r.put(win_y, ax + 2 + win_filled, '░' * (bar_w - win_filled), 'hp_bg')

        r.put(y + box_h - 2, ax + 2, 'MASH [Z]', 'soul', bold=True)

    def _danger_cells(self, include_warnings=True):
        """Return arena cells currently occupied or warned by hazards."""
        cells = set()
        for b in self.bullets:
            bx = int(round(b.x))
            by = int(round(b.y))
            if 0 <= bx < self.arena_w and 0 <= by < self.arena_h:
                cells.add((bx, by))

        for h in self.hazards:
            if isinstance(h, BlinkHazard):
                if h.active or (include_warnings and h.timer < 0):
                    cells.add((h.x, h.y))
            elif isinstance(h, Telegraph):
                if include_warnings:
                    cells.update(h.cells())
            elif isinstance(h, BlobHazard):
                cells.update(h.cells(preview=include_warnings and h.timer < 0))
        return cells

    def _draw_arena(self, r, y, x):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2

        r.box(y, x, box_w, box_h, 'ui_border', double=True)
        r.fill(y + 1, x + 1, self.arena_w, self.arena_h, ' ', 'default')

        # Timer
        remaining = max(0, self.attack_duration - self.attack_timer)
        timer_str = f'{remaining:.1f}s'
        r.put(y, x + box_w - len(timer_str) - 2, timer_str, 'ui_dim')

        # BUF status indicators
        status_x = x + 2
        if self.buf_slow_timer > 0:
            r.put(y, status_x, 'SLOW', 'buf_ability', bold=True)
            status_x += 7
        if self.buf_shield:
            r.put(y, status_x, 'SHLD', 'buf_ability', bold=True)
            status_x += 7
        rule = self.current_attack_read or self.current_attack_rule
        if rule:
            max_rule_w = x + box_w - len(timer_str) - 2 - status_x - 1
            if max_rule_w > 8:
                r.put(y, status_x, rule[:max_rule_w], 'ui_dim')

        bullet_char = self.m.get("bullet_char", "o")

        # Bullets
        for b in self.bullets:
            bsx = x + 1 + int(round(b.x))
            bsy = y + 1 + int(round(b.y))
            if y < bsy < y + box_h - 1 and x < bsx < x + box_w - 1:
                r.put(bsy, bsx, bullet_char, 'bullet', bold=True)

        # Hazards
        for h in self.hazards:
            if isinstance(h, BlinkHazard) and h.active:
                hsx = x + 1 + h.x
                hsy = y + 1 + h.y
                if y < hsy < y + box_h - 1 and x < hsx < x + box_w - 1:
                    r.put(hsy, hsx, bullet_char, 'bullet', bold=True)
            elif isinstance(h, BlinkHazard) and h.timer < 0:
                hsx = x + 1 + h.x
                hsy = y + 1 + h.y
                if y < hsy < y + box_h - 1 and x < hsx < x + box_w - 1:
                    r.put(hsy, hsx, '·', 'ui_dim')
            elif isinstance(h, Telegraph):
                for (hx, hy) in h.cells():
                    hsx = x + 1 + hx
                    hsy = y + 1 + hy
                    if y < hsy < y + box_h - 1 and x < hsx < x + box_w - 1:
                        r.put(hsy, hsx, '·', 'ui_dim')
            elif isinstance(h, BlobHazard):
                preview = h.timer < 0
                for (hx, hy) in h.cells(preview=preview):
                    hsx = x + 1 + hx
                    hsy = y + 1 + hy
                    if y < hsy < y + box_h - 1 and x < hsx < x + box_w - 1:
                        if preview:
                            r.put(hsy, hsx, '·', 'ui_dim')
                        else:
                            r.put(hsy, hsx, bullet_char, 'bullet', bold=True)

        # BUF Predict: highlight currently safe cells in green, based on
        # actual bullets/hazards rather than random columns.
        if self.buf_scan_timer > 0:
            danger = self._danger_cells(include_warnings=True)
            for row in range(self.arena_h):
                for col in range(self.arena_w):
                    if (col, row) in danger:
                        continue
                    # Sparse dots keep the arena readable while still
                    # revealing the safe shape of the attack.
                    if (col + row + int(self.attack_timer * 4)) % 3 != 0:
                        continue
                    r.put(y + 1 + row, x + 1 + col, '\u00b7', 'scan_safe')

        # Soul
        sx = x + 1 + self.soul_x
        sy = y + 1 + self.soul_y
        soul_visible = True
        if self.invuln > 0 and int(self.invuln * 8) % 2 == 0:
            soul_visible = False
        if soul_visible:
            if self.buf_shield:
                # Shield indicator: blue heart
                color = 'buf_ability' if self.hit_flash <= 0 else 'damage'
            else:
                color = 'damage' if self.hit_flash > 0 else 'soul'
            r.put(sy, sx, '\u2665', color, bold=True)

    def _draw_act_menu(self, r, y, ax):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        r.box(y, ax, box_w, box_h, 'ui_border', title=self.m_name)

        current_step = self.protocol.current_step_name()
        for i, opt in enumerate(self.act_options):
            oy = y + 1 + i
            if oy >= y + box_h - 3:
                break
            opt_lower = opt.lower()
            is_next = opt_lower == current_step
            if i == self.act_sel:
                r.put(oy, ax + 3, '>', 'soul', bold=True)
                r.put(oy, ax + 5, opt, 'act', bold=True)
            else:
                color = 'soul' if is_next else 'ui_dim'
                r.put(oy, ax + 5, opt, color, bold=is_next)
            if is_next:
                r.put(oy, ax + box_w - 8, 'NEXT', 'mercy', bold=True)

        selected = self.act_options[self.act_sel].lower()
        hint = self._act_hint(selected)
        r.put(y + box_h - 3, ax + 2, hint[:box_w - 4], 'ui_dim')

        r.put(y + box_h - 2, ax + 2, '[X] Back', 'ui_dim')

    def _draw_item_menu(self, r, y, ax):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        r.box(y, ax, box_w, box_h, 'ui_border', title="INVENTORY")

        inv = self.game.inventory
        # Show up to box_h-3 items (leave room for border + back hint)
        max_visible = box_h - 3
        start = max(0, self.item_sel - max_visible + 1)
        for i in range(start, min(len(inv), start + max_visible)):
            oy = y + 1 + (i - start)
            name = inv[i]
            if i == self.item_sel:
                r.put(oy, ax + 3, '>', 'soul', bold=True)
                r.put(oy, ax + 5, name, 'item', bold=True)
            else:
                r.put(oy, ax + 5, name, 'ui_dim')

        r.put(y + box_h - 2, ax + 2, '[X] Back', 'ui_dim')

    def _draw_buf_menu(self, r, y, ax):
        box_w = self.arena_w + 2
        box_h = self.arena_h + 2
        r.fill(y, ax, box_w, box_h, ' ', 'default')
        r.box(y, ax, box_w, box_h, 'ui_border', title="BUF ABILITIES")

        buf_str = f'BUF: {self.game.player_buf}/{self.game.player_max_buf}'
        r.put(y + 1, ax + box_w - len(buf_str) - 2, buf_str, 'buf_full')

        for i, ability in enumerate(BUF_ABILITIES):
            oy = y + 2 + i * 2
            if oy >= y + box_h - 1:
                break
            cost_str = f'({ability["cost"]} BUF)'
            affordable = self.game.player_buf >= ability["cost"]
            if i == self.buf_sel:
                r.put(oy, ax + 3, '>', 'soul', bold=True)
                color = 'buf_ability' if affordable else 'ui_dim'
                r.put(oy, ax + 5, ability["name"], color, bold=True)
                r.put(oy, ax + 5 + len(ability["name"]) + 1, cost_str, 'ui_dim')
                # Show desc
                r.put(oy + 1, ax + 5, ability["desc"], 'ui_dim')
            else:
                color = 'ui_text' if affordable else 'ui_dim'
                r.put(oy, ax + 5, ability["name"], color)
                r.put(oy, ax + 5 + len(ability["name"]) + 1, cost_str, 'ui_dim')

        r.put(y + box_h - 2, ax + 2, '[X] Back', 'ui_dim')

    def _draw_hp(self, r, y):
        g = self.game
        name = g.player_name
        lv = g.player_lv
        hp = g.player_hp
        max_hp = g.player_max_hp
        buf = g.player_buf
        max_buf = g.player_max_buf

        r.put(y, 2, name, 'ui_text', bold=True)
        r.put(y, 2 + len(name) + 1, f'LV {lv}', 'ui_dim')

        hp_x = 20
        r.put(y, hp_x, 'HP', 'ui_text', bold=True)
        bar_x = hp_x + 3
        bar_w = 16
        ratio = hp / max(max_hp, 1)
        filled = max(0, int(bar_w * ratio))
        color = 'hp_full' if ratio > 0.5 else ('hp_med' if ratio > 0.25 else 'hp_low')
        if self.hit_flash > 0 and int(self.hit_flash * 10) % 2 == 0:
            color = 'damage'
        r.put(y, bar_x, '\u2588' * filled, color)
        r.put(y, bar_x + filled, '\u2591' * (bar_w - filled), 'hp_bg')
        hp_num = f'{hp}/{max_hp}'
        r.put(y, bar_x + bar_w + 1, hp_num, 'ui_text')

        # Buffer bar
        buf_x = bar_x + bar_w + 1 + len(hp_num) + 2
        r.put(y, buf_x, 'BUF', 'buf_full', bold=True)
        buf_bar_x = buf_x + 4
        buf_bar_w = max_buf
        buf_filled = max(0, min(buf_bar_w, buf))
        r.put(y, buf_bar_x, '\u2588' * buf_filled, 'buf_full')
        r.put(y, buf_bar_x + buf_filled, '\u2591' * (buf_bar_w - buf_filled), 'buf_bg')
        r.put(y, buf_bar_x + buf_bar_w + 1, f'{buf}/{max_buf}', 'buf_full')

    def _draw_menu(self, r, sep_y, menu_y):
        r.hline(sep_y, 0, r.width, 'ui_border')
        active = (self.state == S.MENU)
        items = self.menu_items
        spacing = max(1, r.width // len(items))

        for i, (label, cname) in enumerate(items):
            lx = spacing * i + (spacing - len(label)) // 2
            if active and i == self.menu_sel:
                r.put(menu_y, lx - 2, '>', 'soul', bold=True)
                r.put(menu_y, lx, label, cname, bold=True)
            else:
                r.put(menu_y, lx, label, cname if active else 'ui_dim')

        # Hints
        hint_y = menu_y + 1
        if hint_y < r.height:
            if active:
                r.put(hint_y, 2, '<- -> Select   [Z] Confirm', 'ui_dim')
            elif self.state == S.ENEMY_ATTACK:
                r.put(hint_y, 2, 'WASD/Arrows to dodge!', 'ui_dim')
            elif self.state == S.FIGHT_TIMING:
                r.put(hint_y, 2, '[Z] to stop the bar!', 'ui_dim')
