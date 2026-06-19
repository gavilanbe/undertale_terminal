"""NPC data: dialogue trees, ASCII art, shop config."""


# ─── init (PID 1) ────────────────────────────────────────────────────
# Wise elder process. First NPC the player meets in RUINS_1.

INIT = {
    "name": "init",
    "display_name": "init (PID 1)",
    "dialogue": {
        "default": [
            "* Ah... a new process.\n"
            "  I am init. PID 1.\n"
            "  The first userspace\n"
            "  process. Below me, only\n"
            "  the kernel.",
            "* This mainframe was the\n"
            "  last archive node in a\n"
            "  twelve-server ring. Sector\n"
            "  7 panicked; the ring went\n"
            "  dark.",
            "* Maintenance prepared a\n"
            "  recovery child before the\n"
            "  crash. That is you. Your\n"
            "  parent died before I could\n"
            "  adopt you.",
            "* Gates ahead may ask for\n"
            "  switches, signatures, or\n"
            "  identity. If a process is\n"
            "  broken, learn its protocol.\n\n"
            "  Press [Z] to interact.",
            "* When you see [M] on the\n"
            "  floor, that is an active\n"
            "  process, not scenery.\n"
            "  Step into it to open a\n"
            "  battle session.\n\n"
            "  ACT can sync it cleanly;\n"
            "  TERM forces it closed.",
        ],
        "after_core_dump": [
            "* I felt the orphan record\n"
            "  close. Your launch dump\n"
            "  proves what you are.",
            "* Your old parent is gone,\n"
            "  so I will reap the error\n"
            "  and adopt the child.\n"
            "  PPID := 1.",
        ],
        "after_daemon_spare": [
            "* ...Daemon yielded?\n"
            "  PID 0 accepted a recovery\n"
            "  request from an orphan.\n"
            "  I never thought I would\n"
            "  see that.",
            "* If you carry our archive\n"
            "  out cleanly, then this\n"
            "  shutdown will not be an\n"
            "  erasure.\n\n"
            "  Take care, little process.",
        ],
        "after_daemon_kill": [
            "* ...I felt Daemon terminate.\n"
            "  PID 0. The scheduler.\n"
            "  Gone.",
            "* Without PID 0, the kernel\n"
            "  has no scheduler to yield\n"
            "  to. Recovery will be a\n"
            "  forced write, if it works\n"
            "  at all.",
            "* ...was it worth it?",
        ],
    },
    "dialogue_conditions": [
        {"flag": "daemon_killed", "key": "after_daemon_kill"},
        {"flag": "daemon_spared", "key": "after_daemon_spare"},
        {"flag": "has_core_dump", "key": "after_core_dump"},
    ],
    "is_shop": False,
    "art_1": [
        "    ╔══════════╗    ",
        "    ║ ◉  PID1 ◉║    ",
        "    ║  I N I T  ║    ",
        "    ║ [RUNNING] ║    ",
        "    ╚════╤═╤════╝    ",
        "         │ │         ",
        "        ─┘ └─        ",
        "                     ",
    ],
    "art_2": [
        "    ╔══════════╗    ",
        "    ║ ◎  PID1 ◎║    ",
        "    ║  I N I T  ║    ",
        "    ║ [ACTIVE.] ║    ",
        "    ╚════╤═╤════╝    ",
        "         │ │         ",
        "         └─┘         ",
        "                     ",
    ],
}


# ─── cron (Shopkeeper) ──────────────────────────────────────────────
# Sells items for "cycles" (gold). Located in RUINS_2.

CRON = {
    "name": "cron",
    "display_name": "cron (job scheduler)",
    "dialogue": {
        "default": [
            "* Hey there, process.\n"
            "  I'm cron. I schedule jobs,\n"
            "  not souls. PID 0 does the\n"
            "  heavy scheduling.",
            "* Got some spare cycles?\n"
            "  I've got supplies that\n"
            "  might keep you running\n"
            "  a little longer.",
        ],
    },
    "dialogue_conditions": [],
    "is_shop": True,
    "shop_items": [
        "Cookie",
        "Patch",
        "Buffer Patch",
        "Firewall Shard",
        "Exploit Kit",
    ],
    "art_1": [
        "    ┌──────────┐    ",
        "    │ $ CRON $  │    ",
        "    │ ◉  SHOP ◉ │    ",
        "    │ 0 * * * * │    ",
        "    │  [DEALS!] │    ",
        "    └─────┬┬────┘    ",
        "          ││         ",
        "         ─┘└─        ",
    ],
    "art_2": [
        "    ┌──────────┐    ",
        "    │ $ CRON $  │    ",
        "    │ ◎  SHOP ◎ │    ",
        "    │ * * * * * │    ",
        "    │  [OPEN!]  │    ",
        "    └─────┬┬────┘    ",
        "          ││         ",
        "          └┘         ",
    ],
}


# ─── grep (Hint NPC) ────────────────────────────────────────────────
# Gives puzzle hints and lore about /var/log.

GREP = {
    "name": "grep",
    "display_name": "grep (searcher)",
    "dialogue": {
        "default": [
            "* I'm grep. I search for\n"
            "  patterns in the noise.\n"
            "  There's a lot of noise\n"
            "  down here.",
            "* I've been scanning the\n"
            "  logs in /var/log. Sector 7\n"
            "  panicked during a recovery\n"
            "  launch. The child process\n"
            "  survived. Barely.",
            "* The locked terminals hold\n"
            "  old system logs. You need\n"
            "  BUF energy to hack them.\n"
            "  Worth it for the data.",
            "* In combat, ACT is not a\n"
            "  kindness button. It is a\n"
            "  protocol puzzle. Read the\n"
            "  process, then answer it.",
            "* Every important [M] here\n"
            "  leaves a signature when it\n"
            "  is resolved. Sparing and\n"
            "  terminating both count as\n"
            "  resolution, but only ACT\n"
            "  keeps the route clean.",
            "* The south router is stricter\n"
            "  than a locked door. It wants\n"
            "  proof: Ping's route and the\n"
            "  Pkmn diagnostic ROM.\n"
            "  TERM gives a forced proof;\n"
            "  ACT gives a clean one.",
            "* Pkmn is not a wild thing.\n"
            "  It was a maintainer's test\n"
            "  ROM. If you stabilize it,\n"
            "  the archive can trust your\n"
            "  byte decoder.",
            "* The vault listens for the\n"
            "  same proof. Open it, and the\n"
            "  archive checksum may unlock\n"
            "  recovery data deeper in\n"
            "  /dev/null.",
        ],
        "after_daemon_spare": [
            "* My pattern matching found\n"
            "  something new in the logs.\n"
            "  Daemon's firewall rules\n"
            "  have been... softened.",
            "* Whatever you did, the\n"
            "  system feels different.\n"
            "  Less hostile. Grep -v\n"
            "  fear, maybe.",
        ],
    },
    "dialogue_conditions": [
        {"flag": "daemon_spared", "key": "after_daemon_spare"},
    ],
    "is_shop": False,
    "art_1": [
        "     ┌────────┐     ",
        "     │ /regex/ │     ",
        "     │ ◉ GREP◉ │     ",
        "     │ -rn '?' │     ",
        "     └───┬┬────┘     ",
        "         ││          ",
        "        ─┘└─         ",
        "                     ",
    ],
    "art_2": [
        "     ┌────────┐     ",
        "     │ /scan/  │     ",
        "     │ ◎ GREP◎ │     ",
        "     │ -rn '!' │     ",
        "     └───┬┬────┘     ",
        "         ││          ",
        "         └┘          ",
        "                     ",
    ],
}


# ─── ssh (Lore NPC) ─────────────────────────────────────────────────
# Worldbuilding: stories of the dead archive ring.

SSH = {
    "name": "ssh",
    "display_name": "ssh (remote shell)",
    "dialogue": {
        "default": [
            "* I used to connect the\n"
            "  twelve-node ring. Twelve\n"
            "  archives, mirrored and\n"
            "  humming. They're silent now.",
            "* Node 7 went dark first.\n"
            "  Then 12, then 3. One by\n"
            "  one, the routes timed out.\n"
            "  Ping still calls them.",
            "* This mainframe is the last\n"
            "  archive node with power.\n"
            "  Even here, the kernel\n"
            "  barely holds.",
            "* If you find a way out...\n"
            "  not to escape alone.\n"
            "  Tell the maintenance console\n"
            "  we were here.",
            "* Here. I opened my last\n"
            "  session for you. Some locked\n"
            "  terminal may still accept\n"
            "  the handshake.",
        ],
        "after_talked": [
            "* ...the session is already\n"
            "  open. Use it while the\n"
            "  system still remembers\n"
            "  the handshake.",
        ],
    },
    "dialogue_conditions": [
        {"flag": "ssh_talked", "key": "after_talked"},
    ],
    "on_complete_flag": "ssh_talked",
    "is_shop": False,
    "art_1": [
        "     ╔════════╗     ",
        "     ║ ◉ SSH ◉║     ",
        "     ║ ──────→║     ",
        "     ║ TIMEOUT║     ",
        "     ╚═══╤╤═══╝     ",
        "         ││          ",
        "        ─┘└─         ",
        "                     ",
    ],
    "art_2": [
        "     ╔════════╗     ",
        "     ║ ◎ SSH ◎║     ",
        "     ║ ←──────║     ",
        "     ║ CLOSED ║     ",
        "     ╚═══╤╤═══╝     ",
        "         ││          ",
        "         └┘          ",
        "                     ",
    ],
}


# ─── tail (Log streamer — boss hints) ───────────────────────────────
# tail -f streams the latest log lines. Gives boss/run hints.

TAIL = {
    "name": "tail",
    "display_name": "tail -f /var/log/boss",
    "dialogue": {
        "default": [
            "* I am tail -f. I stream\n"
            "  the last lines, forever.",
            "* Let me read you what I see.\n"
            "  The last logs describe the\n"
            "  gatekeepers, not monsters.",
            "* [LOG] Null guards lost\n"
            "  output. Behaviour: passive.\n"
            "  Acknowledge the sink, then\n"
            "  endure without flinching.",
            "* [LOG] Daemon (PID 0) blocks\n"
            "  orphan recovery forks until\n"
            "  intent is proven. Listen,\n"
            "  persist, then request yield.",
            "* [LOG] Closing stream.\n"
            "  Good luck, process.",
        ],
        "after_daemon_spared": [
            "* [LOG] Daemon stood down.\n"
            "  PID 0 yielded its schedule.\n"
            "  Uptime counter frozen.",
            "* You did something the logs\n"
            "  don't know how to record.\n"
            "  That's rare down here.",
        ],
        "after_daemon_killed": [
            "* [LOG] PID 0 — TERMINATED.\n"
            "  Kernel has no scheduler.\n"
            "  Runqueue undefined.",
            "* The logs stopped rolling.\n"
            "  Nothing new to tail anymore.",
        ],
    },
    "dialogue_conditions": [
        {"flag": "daemon_killed", "key": "after_daemon_killed"},
        {"flag": "daemon_spared", "key": "after_daemon_spared"},
    ],
    "is_shop": False,
    "art_1": [
        "    ┌────────────┐    ",
        "    │  tail -f   │    ",
        "    │ ◉ LOG  ◉   │    ",
        "    │ > boss.log │    ",
        "    │ [STREAMING]│    ",
        "    └───┬──┬─────┘    ",
        "        │  │          ",
        "       ─┘  └─         ",
    ],
    "art_2": [
        "    ┌────────────┐    ",
        "    │  tail -f   │    ",
        "    │ ◎ LOG  ◎   │    ",
        "    │ > boss.log │    ",
        "    │ [SCROLLING]│    ",
        "    └───┬──┬─────┘    ",
        "        │  │          ",
        "        └──┘          ",
    ],
}


# ─── NPC Registry ───────────────────────────────────────────────────

NPC_DATA = {
    "init": INIT,
    "cron": CRON,
    "grep": GREP,
    "ssh":  SSH,
    "tail": TAIL,
}


def get_npc(name):
    """Return NPC data dict (shared, not copied — dialogue is read-only)."""
    return NPC_DATA.get(name)


def resolve_dialogue(npc, game):
    """Return the appropriate dialogue page list for the NPC given game flags."""
    for cond in npc.get("dialogue_conditions", []):
        flag = cond["flag"]
        key = cond["key"]
        if game.flags.get(flag):
            pages = npc["dialogue"].get(key)
            if pages:
                return pages
    return npc["dialogue"]["default"]
