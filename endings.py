"""Ending scenes for the four bifurcations of the run.

Ending types:
  - 'pacifist':      Daemon spared, zero kills, recovery fully resolved
  - 'genocide':      Daemon killed AND zero spares across the run
  - 'neutral_spare': Daemon spared but the run was mixed
  - 'neutral_kill':  Daemon killed but the run was mixed

Triggered from exploration.py when the player walks into the exit of
RUINS_DAEMON (target_zone == "ENDING"). The player returns to the
title screen after pressing through the final page.
"""

import random

from engine import Scene, Typewriter, CONFIRM_KEYS
from save_system import delete_save


REQUIRED_PROTOCOL_FLAGS = [
    "protocol_cursor_resolved",
    "protocol_ping_resolved",
    "protocol_pkmn_resolved",
    "protocol_blob_resolved",
    "protocol_null_resolved",
    "protocol_daemon_resolved",
]

REQUIRED_RECOVERY_FLAGS = REQUIRED_PROTOCOL_FLAGS + [
    "has_core_dump",
]


def resolve_ending(game):
    """Inspect game state and pick an ending key."""
    daemon_spared = bool(game.flags.get("daemon_spared"))
    recovery_complete = all(
        game.flags.get(flag) for flag in REQUIRED_RECOVERY_FLAGS
    )
    if daemon_spared:
        if game.kill_count == 0 and recovery_complete:
            return "pacifist"
        return "neutral_spare"
    # Daemon killed
    if game.spare_count == 0:
        return "genocide"
    return "neutral_kill"


ENDING_TEXTS = {
    "pacifist": [
        ("* You step past Daemon's\n"
         "  post. PID 0 yields the\n"
         "  runqueue, deliberately,\n"
         "  for the first time."),
        ("* Behind you, every process\n"
         "  has a clean exit path.\n"
         "  Cursor closed its shell.\n"
         "  Ping stopped searching.\n"
         "  Pkmn loops safely."),
        ("* Blob rests in an allocated\n"
         "  heap. Null accepts output\n"
         "  without swallowing you.\n"
         "  The broken protocols form\n"
         "  a recovery handshake."),
        ("* You know where your tree\n"
         "  begins now. PPID 1.\n"
         "  init's branch holds.\n"
         "  You are not orphaned."),
        ("* You mount /mnt/recovery.\n"
         "  Not to flee the archive,\n"
         "  but to preserve it before\n"
         "  shutdown."),
        ("* Above the rack, a dormant\n"
         "  maintenance console receives\n"
         "  its first packet in years.\n\n"
         "  It reads:\n"
         "  > archive recovered\n"
         "  > residents preserved"),
        ("* ...\n\n"
         "  [PACIFIST — graceful\n"
         "  recovery]"),
    ],
    "genocide": [
        ("* Daemon's scheduler halts.\n"
         "  PID 0 — TERMINATED.\n"
         "  The kernel has no one to\n"
         "  yield to."),
        ("* You look back. The corridor\n"
         "  is empty now. Every process\n"
         "  you met is gone. No logs\n"
         "  remain of them."),
        ("* /dev/null swells. There is\n"
         "  more void than data on the\n"
         "  mainframe now. You can\n"
         "  feel it pulling at you."),
        ("* You were built to carry\n"
         "  survivors. Instead, you\n"
         "  carry silence.\n\n"
         "  ...and now you are alone."),
        ("* The soul in your chest\n"
         "  feels heavier. It did not\n"
         "  like this."),
        ("* ...\n\n"
         "  [GENOCIDE — mainframe\n"
         "  deserted]"),
    ],
    "neutral_spare": [
        ("* Daemon steps aside.\n"
         "  You walk past PID 0.\n"
         "  The kernel sighs."),
        ("* The recovery handshake is\n"
         "  incomplete. Some protocols\n"
         "  were understood. Some were\n"
         "  forced. Some were never\n"
         "  read at all."),
        ("* The maintenance console\n"
         "  receives a warning packet,\n"
         "  but not a full archive.\n"
         "  You saved a path, not\n"
         "  the whole system."),
        ("* ...\n\n"
         "  [NEUTRAL — partial\n"
         "  recovery]"),
    ],
    "neutral_kill": [
        ("* Daemon terminates.\n"
         "  PID 0 is gone.\n"
         "  The firewall falls."),
        ("* Some protocol signatures\n"
         "  remain, but without the\n"
         "  scheduler there is no\n"
         "  graceful shutdown.\n"
         "  Only a forced reboot."),
        ("* The maintenance console\n"
         "  receives one damaged\n"
         "  recovery packet. Enough\n"
         "  to prove it lived. Not\n"
         "  enough to restore it."),
        ("* ...\n\n"
         "  [NEUTRAL — forced\n"
         "  recovery]"),
    ],
}


class EndingScene(Scene):

    def __init__(self, game, ending_type):
        super().__init__(game)
        self.ending_type = ending_type
        self.pages = list(ENDING_TEXTS.get(ending_type, ENDING_TEXTS["neutral_kill"]))
        self.page_idx = 0
        self.tw = Typewriter(self.pages[0], speed=0.04)
        self.fade_t = 0.0

    def on_enter(self):
        if self.game.audio:
            self.game.audio.stop_bgm()
            # Quiet ambience track falls back gracefully.
            self.game.audio.play_bgm("overworld")

    def on_exit(self):
        if self.game.audio:
            self.game.audio.stop_bgm()

    def update(self, dt, keys):
        self.tw.update(dt)
        self.fade_t += dt
        for k in keys:
            if k in CONFIRM_KEYS:
                if not self.tw.done:
                    self.tw.skip()
                else:
                    self.page_idx += 1
                    if self.page_idx < len(self.pages):
                        self.tw = Typewriter(
                            self.pages[self.page_idx], speed=0.04)
                    else:
                        self._finish()
                break

    def _finish(self):
        # Reset run — the save is consumed by reaching the ending.
        delete_save()
        from title import TitleScene
        self.game.change_scene(TitleScene(self.game))

    def render(self, r):
        r.fill(0, 0, r.width, r.height, ' ', 'default')

        # Center the text block vertically and horizontally.
        text = self.tw.visible()
        lines = text.split('\n')
        total_h = len(lines) + 2
        start_y = max(1, (r.height - total_h) // 2)

        # Ending-tone colour
        color = {
            "pacifist":      "mercy",
            "genocide":      "ominous",
            "neutral_spare": "ui_text",
            "neutral_kill":  "ui_text",
        }.get(self.ending_type, "ui_text")

        # Box width adapts to longest line (min 40)
        max_line = max((len(l) for l in lines), default=0)
        box_w = min(max(40, max_line + 6), r.width - 4)
        box_x = (r.width - box_w) // 2

        r.box(start_y, box_x, box_w, len(lines) + 4, 'ui_border', double=True)
        for i, line in enumerate(lines):
            lx = box_x + (box_w - len(line)) // 2
            r.put(start_y + 2 + i, lx, line, color, bold=True)

        if self.tw.done:
            hint = 'next' if self.page_idx < len(self.pages) - 1 else 'return to title'
            r.put(r.height - 2, (r.width - len(f"[Z] {hint}")) // 2,
                  f"[Z] {hint}", 'ui_dim')
