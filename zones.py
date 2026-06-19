"""Multi-zone maps, transitions, item placement, and monster placement."""

# ─── RUINS_1 ─────────────────────────────────────────────────────────
# Starting area: init NPC, switch tutorial, mandatory boot sequence
# /home/lost — spawn room, orphan logs, then a locked boot corridor

RUINS_1_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 0
    "WWWWWW......WWWWWWWWWWWWWWWWWW",  # 1  spawn room
    "WWWWWW.fPf..WWWWWWWWWWWWWWWWWW",  # 2
    "WWWWWW.fff..WWWWWWWWWWWWWWWWWW",  # 3
    "WWWWWW..x...WWWWWWWWWWWWWWWWWW",  # 4  save point
    "WWWWWW..S...WWWWWWWWWWWWWWWWWW",  # 5  tutorial sign
    "WWWWWWWW::WWWWWWWWWWWWWWWWWWWW",  # 6  narrow corridor south
    "WWWWWWWW::WWWWWWWWWWWWWWWWWWWW",  # 7
    "WWW.S...S.NWWWWWWWWWWWWWWWWWWW",  # 8  lore signs (4,8)+(8,8), init(10,8)
    "WWW........._iWWWWWWWWWWWWWWWW",  # 9  SECRET wall(12,9), hidden item(13,9)
    "WWWWWWWW::WWWWWWWWWWWWWWWWWWWW",  # 10 corridor continues
    "WWWWWWWW::WWWWWWWWWWWWWWWWWWWW",  # 11
    "W.....#.......WW.....i......WW",  # 12 tutorial switch(6), item(21)
    "W....S......................WW",  # 13 secret-wall hint sign(5,13)
    "W..S..........WWWWWWWWWWWWWWWW",  # 14 sign(3) — boot-sequence hint
    "WWWWWWWWGGWWWWWWWWWWWWWWWWWWWW",  # 15 corridor gates
    "WWWWWWWW::WWWWWWWWWWWWWWWWWWWW",  # 16
    "W....#....#..........#.SGWWWWW",  # 17 HOME/PID1/NET switches, scanner sign, gate
    "W..................i....GWWWWW",  # 18 item(19), boot gate
    "WWWWWWWWWWWWWWWWWWWWWWWWMWWWWW",  # 19 Cursor blocks final scanner
    "WWWWWWWWWWWWWWWWWWWWWWWWEWWWWW",  # 20 exit(24), behind Cursor
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 21
]

RUINS_1_MONSTERS = {
    (24, 19): "Cursor",
}

RUINS_1_ITEMS = {
    (21, 12): "Cache Fragment",
    (19, 18): "Patch",
    (13, 9):  "RAM Juice",     # hidden alcove behind secret wall (12,9)
}

RUINS_1_EXIT = {
    "pos": (24, 20),
    "target_zone": "RUINS_2",
    "spawn": (14, 1),
    "conditions": [
        {
            "type": "defeat_monster",
            "pos": (24, 19),
            "fail_msg": (
                "* The exit scanner rejects\n"
                "  an unsynced shell.\n"
                "  Step into Cursor [M] and\n"
                "  resolve its protocol."
            ),
        },
    ],
}

RUINS_1_NPCS = {
    (10, 8): "init",
}

RUINS_1_PUZZLES = {
    "tutorial": {
        "switch_pos": (6, 12),
        "gate_positions": [(8, 15), (9, 15)],
        "default_state": False,
    },
    # Boot sequence: three stations before the final corridor. The clue names
    # the boot rule (parent -> child -> route), not just the raw coordinates.
    "boot_sequence": {
        "type": "sequence",
        "switches": [
            {"id": "A", "pos": (5, 17),  "label": "HOME"},
            {"id": "B", "pos": (10, 17), "label": "PID1"},
            {"id": "C", "pos": (21, 17), "label": "NET"},
        ],
        "correct_order": ["B", "A", "C"],
        "gate_positions": [(24, 17), (24, 18)],
        "default_state": False,
    },
}

RUINS_1_SIGNS = {
    (8, 5): (
        "* [LOG] Process init says:\n"
        "  Step on [#] switches to\n"
        "  open blocked [G] gates."
    ),
    (4, 8): (
        "* [LOG] /var/log/auth.last\n"
        "    Last login: EPOCH+8191\n"
        "    User:        MAINT\n"
        "    Task:        recovery fork\n"
        "  No human session has\n"
        "  opened here since."
    ),
    (8, 8): (
        "* [LOG] init notes:\n"
        "    Orphan process detected.\n"
        "    PPID := unset.\n"
        "    Reaping deferred.\n"
        "  A Core Dump may still\n"
        "  prove its launch tree."
    ),
    (5, 13): (
        "* [LOG] Maintenance notice:\n"
        "    Some walls in /home are\n"
        "    sparse by design. Recovery\n"
        "    children were trained to\n"
        "    trust missing data.\n"
        "  Walk firmly. You may pass."
    ),
    (3, 14): (
        "* [LOG] BOOT HANDSHAKE:\n"
        "  A recovery fork starts\n"
        "  at its adopter, returns\n"
        "  home, then asks the net\n"
        "  for a route.\n\n"
        "  Plates: LEFT=HOME,\n"
        "  MIDDLE=PID1, RIGHT=NET.\n"
        "  Wrong order resets all."
    ),
    (23, 17): (
        "* [SCANNER]\n"
        "  The exit requires a clean\n"
        "  shell signature.\n"
        "  Step into the active [M]\n"
        "  process ahead.\n\n"
        "  ACT syncs it cleanly.\n"
        "  TERM forces it closed."
    ),
}


# ─── RUINS_2 ─────────────────────────────────────────────────────────
# Hub zone: cron shop, grep/ssh NPCs, protocol router, locked terminal.
# /var/log — a readable diagnostic board instead of an open clutter room:
#
#   • North entry feeds the INDEX room, where the vault establishes the goal.
#   • Two thin side corridors branch out from the index. Each has one active
#     process in the doorway, so the side-log proof is earned, not decorative.
#   • The vault turns those side proofs into an archive checksum.
#   • The router compiler will not accept input until that checksum exists.
#   • The south log becomes a quiet tail stream, then Blob blocks the exit.
RUINS_2_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 0
    "WWWWWWWWWWWWW....WWWWWWWWWWWWW",  # 1  N entry (cols 13-16)
    "WWWWWWWWWWWWW....WWWWWWWWWWWWW",  # 2
    "WWWWWWWWWWWWW.S..WWWWWWWWWWWWW",  # 3  entry sign (14,3)
    "WWWWWWWWWWWWW....WWWWWWWWWWWWW",  # 4
    "WWWWW....................WWWWW",  # 5  INDEX opens from entry
    "WWWWW.x...N...V...N......WWWWW",  # 6  save, grep, vault, cron
    "WWWWW.........S..........WWWWW",  # 7  INDEX rule sign
    "WWWWWWWW..WWW....WWW..WWWWWWWW",  # 8  side-log branches + spine
    "W.iS.M....WWW....WWW....M.SL.W",  # 9  Ping/Pkmn chokepoints
    "W....WWWWWWWW....WWWWWWWW.N.iW",  # 10 proof rooms; ssh behind Pkmn
    "W....WWWWWWWW....WWWWWWWW....W",  # 11 side rooms close back on themselves
    "WWWWWWWWWWWWW.S..WWWWWWWWWWWWW",  # 12 compiler rule sign
    "WWWWWWWW..r...r...r...WWWWWWWW",  # 13 router compiler
    "WWWWWWWWWWWWWGGGGWWWWWWWWWWWWW",  # 14 protocol router gate
    "WWWWWWWWWWWWW.S..WWWWWWWWWWWWW",  # 15 south archive warning
    "WWWWWWWWWWWWW.L..WWWWWWWWWWWWW",  # 16 BUF-locked archive
    "WWWWWWWWWWWWW..N.WWWWWWWWWWWWW",  # 17 tail after the compiler gate
    "WWWWWWWWWWWWWW.WWWWWWWWWWWWWWW",  # 18 single-file heap leak
    "WWWWWWWWWWWWWWMWWWWWWWWWWWWWWW",  # 19 Blob mandatory (14,19)
    "WWWWWWWWWWWWWWEWWWWWWWWWWWWWWW",  # 20 exit (14,20)
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 21
]

RUINS_2_MONSTERS = {
    (5, 9):   "Ping",   # west log proof chokepoint
    (24, 9):  "Pkmn",   # east ROM/session chokepoint
    (14, 19): "Blob",   # mandatory boss-gate in south corridor
}

RUINS_2_ITEMS = {
    (2, 9):   "Cache Fragment",
    (28, 10): "RAM Juice",
}

RUINS_2_EXIT = {
    "pos": (14, 20),
    "target_zone": "RUINS_BOSS",
    "spawn": (14, 1),
    "conditions": [
        {
            "type": "defeat_monster",
            "pos": (14, 19),
            "fail_msg": (
                "* Blob's heap leak still\n"
                "  corrupts the south route.\n"
                "  Resolve the process before\n"
                "  entering /dev/null."
            ),
        },
    ],
}

RUINS_2_NPCS = {
    (10, 6):  "grep",   # index reader
    (18, 6):  "cron",   # shop in the INDEX safe room
    (26, 10): "ssh",    # session process behind the ROM proof
    (15, 17): "tail",   # south log streamer after router
}

# The side wings gather protocol signatures; the lower trench compiles them.
# The puzzle structure is: side protocols + vault + locked terminals + boss-gate.
RUINS_2_PUZZLES = {}

RUINS_2_SIGNS = {
    (14, 3): [
        (
            "* [LOG] Welcome to /var/log.\n"
            "  This place is not a maze.\n"
            "  It is a log file.\n"
            "  Read it top to bottom:"
        ),
        (
            "* INDEX -> side proofs ->\n"
            "  vault checksum -> router\n"
            "  compiler -> final tail."
        ),
    ],
    (14, 7): [
        (
            "* [INDEX]\n"
            "  The vault asks whether\n"
            "  you can read damaged\n"
            "  processes cleanly."
        ),
        (
            "* NET.LOG is west.\n"
            "  ROM.LOG is east.\n"
            "  Their proofs release\n"
            "  checksum here."
        ),
    ],
    (3, 9): [
        (
            "* [NET.LOG]\n"
            "  Node-7 kept answering\n"
            "  a ring that was already\n"
            "  dark."
        ),
        (
            "* Ping was left in the\n"
            "  doorway. Certify the\n"
            "  route by hearing the\n"
            "  timeout."
        ),
    ],
    (26, 9): [
        (
            "* [ROM.LOG]\n"
            "  Maintenance tested archive\n"
            "  recovery with a handheld\n"
            "  diagnostic ROM."
        ),
        (
            "* Pkmn blocks the session\n"
            "  terminal until your byte\n"
            "  order is trusted."
        ),
    ],
    (14, 12): [
        (
            "* [ROUTER]\n"
            "  The compiler accepts only\n"
            "  a released checksum."
        ),
        (
            "* NET faces east.\n"
            "  CORE faces south.\n"
            "  ROM faces west.\n"
            "  Then tail opens."
        ),
    ],
    (14, 15): [
        (
            "* [TAIL RECORD]\n"
            "  The side logs are no\n"
            "  longer noise."
        ),
        (
            "* They have compiled into\n"
            "  one southbound story.\n"
            "  Something below is leaking\n"
            "  heap across the exit path."
        ),
    ],
}

RUINS_2_DIAL_PUZZLES = {
    "router_compile": {
        "states": 4,
        "gate_positions": [(13, 14), (14, 14), (15, 14), (16, 14)],
        "required_flags": [
            ("protocol_ping_resolved", "Ping route"),
            ("protocol_pkmn_resolved", "Pkmn ROM"),
            ("vault_opened", "archive checksum"),
        ],
        "nodes": {
            (10, 13): {"initial": 0, "solution": 1},  # west input points east
            (14, 13): {"initial": 3, "solution": 2},  # compiler points south
            (18, 13): {"initial": 0, "solution": 3},  # east input points west
        },
        "fail_msg": (
            "* ROUTER: missing proof.\n"
            "  Still needed: {missing}.\n"
            "  Resolve [M] proofs in\n"
            "  battle; then INDEX vault."
        ),
        "gate_msg": (
            "* ROUTER: checksum ready.\n"
            "  Set the [r] nodes:\n"
            "  NET >  CORE v\n"
            "  ROM <"
        ),
        "success_msg": (
            "* > ROUTE COMPILED\n"
            "  Ping > core < Pkmn\n"
            "  Output: /dev/null"
        ),
        "solved_msg": (
            "* The router hums in a\n"
            "  stable southbound route."
        ),
    },
}

RUINS_2_VAULTS = {
    (14, 6): {
        "required_flags": [
            ("protocol_ping_resolved", "Ping route"),
            ("protocol_pkmn_resolved", "Pkmn ROM"),
        ],
        "flag": "vault_opened",
        "reward": "Full Backup",
        "lore": (
            "* [VAULT — UNSEALED]\n"
            "  The archive accepts two\n"
            "  clean signatures:\n"
            "  an echo route, and an\n"
            "  old diagnostic ROM.\n\n"
            "  Protocol signatures are not\n"
            "  keys. They are proof that\n"
            "  the recovery child can read\n"
            "  damaged processes without\n"
            "  erasing them.\n\n"
            "  Maintenance built a child\n"
            "  process to preserve this\n"
            "  archive. Sector 7 failed\n"
            "  before its parent could\n"
            "  schedule it.\n\n"
            "  Checksum released:\n"
            "  /dev/null/recovery"
        ),
    },
}


RUINS_2_LOCKED = {
    (14, 16): {
        "buf_cost": 2,
        "flag": "terminal_varlog_hacked",
        "lore": (
            "* [DECRYPTED LOG]\n"
            "  Timestamp: EPOCH+8192000\n"
            "  Sector 7 panic during\n"
            "  RECOVERY_CHILD launch.\n"
            "  Parent task terminated.\n"
            "  Child PID: unassigned.\n\n"
            "  Note: if the child reaches\n"
            "  PID 0 with a clean trace,\n"
            "  permit scheduled recovery."
        ),
    },
    (27, 9): {
        # Gated narratively by a conversation with ssh, not by BUF.
        "required_flag": "ssh_talked",
        "required_msg": (
            "* This terminal needs a\n"
            "  session key. A remote\n"
            "  process might share one.\n"
            "  (try ssh)"
        ),
        "flag": "terminal_passwd_hacked",
        "lore": (
            "* [DECRYPTED /etc/passwd]\n"
            "  root:x:0:0:Daemon::/kernel\n"
            "  init:x:1:1:init::/sbin\n"
            "  lost:x:?:?:RECOVERY::/home/lost\n\n"
            "  ...you were registered.\n"
            "  The system remembered\n"
            "  what you were for."
        ),
    },
}


# ─── RUINS_BOSS ──────────────────────────────────────────────────────
# Boss chamber: diamond-shaped arena, hidden Full Backup alcove
# /dev/null — ominous approach to Null

RUINS_BOSS_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 0
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 1  narrow entry
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 2
    "WWWWWWWWWW........WWWWWWWWWWWW",  # 3  widening
    "WWWWWWWW............WWWWWWWWWW",  # 4
    "WWWWWW.....c.....c......WWWWWW",  # 5  flowers
    "WWWWW....................WWWWW",  # 6
    "WWWW...........M.........WWWWW",  # 7  Null(15)
    "WWWWW....................WWWWW",  # 8
    "WWWWWW.....c.....c......WWWWWW",  # 9  flowers
    "WWWWWWWW............WWWWWWWWWW",  # 10
    "WWWWWWWWWW........WWWWWWWWWWWW",  # 11
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 12
    "WWWWWWWWWWWW..S.WWWWWWWWWWWWWW",  # 13 recovery sign (14,13)
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 14
    "Wi.i.WWWWWWW....WWWWWWWWWWWWWW",  # 15 hidden alcove: Full Backup(1), Core Dump(3)
    "W....GO.B..........WWWWWWWWWWW",  # 16 checksum block -> socket opens gate
    "WWWWWWWWWW........WWWWWWWWWWWW",  # 17
    "WWWWWWWWWW...E....WWWWWWWWWWWW",  # 18 exit(13)
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 19
]

RUINS_BOSS_MONSTERS = {
    (15, 7): "Null",
}

RUINS_BOSS_ITEMS = {
    (1, 15): "Full Backup",
    (3, 15): "Core Dump",   # hidden alcove reward — resolves PPID before Daemon
}

RUINS_BOSS_EXIT = {
    "pos": (13, 18),
    "target_zone": "RUINS_DAEMON",
    "spawn": (14, 1),
    "conditions": [
        {
            "type": "defeat_monster",
            "pos": (15, 7),
            "fail_msg": (
                "* /dev/null has not accepted\n"
                "  your output. Acknowledge\n"
                "  Null before continuing."
            ),
        },
    ],
}

RUINS_BOSS_SIGNS = {
    (14, 13): (
        "* [RECOVERY ALCOVE]\n"
        "  The archive checksum has\n"
        "  mass here. Seat its data\n"
        "  block [B] in the socket\n"
        "  [O] to open the orphan\n"
        "  launch record.\n\n"
        "  That record is your Core\n"
        "  Dump: the only proof that\n"
        "  you were launched before\n"
        "  your parent died."
    ),
}

RUINS_BOSS_PUSH_PUZZLES = {
    "checksum_socket": {
        "blocks": [(8, 16)],
        "sockets": [(6, 16)],
        "gate_positions": [(5, 16)],
        "required_flags": [
            ("vault_opened", "archive checksum"),
        ],
        "fail_msg": (
            "* The socket accepts the\n"
            "  block, but stays dark.\n"
            "  The /var/log vault has\n"
            "  not released checksum."
        ),
        "success_msg": (
            "* > CHECKSUM SEATED\n"
            "  Recovery alcove unlocked."
        ),
    },
}


# ─── RUINS_DAEMON ───────────────────────────────────────────────────
# /proc/self — the mirror zone. Three reflection rotors must agree on
# the recovered process tree before the gate to Daemon accepts the player.
# Signs speak of the player seeing their own reflection that doesn't turn
# with them until their PPID is resolved.

RUINS_DAEMON_MAP = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 0
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 1  narrow entry
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 2
    "WWWWWWWWWWWW.S..WWWWWWWWWWWWWW",  # 3  sign(13): enter /proc/self
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 4
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 5
    "WWWWWWWW............WWWWWWWWWW",  # 6  widening
    "WWWWWWWW.S........S.WWWWWWWWWW",  # 7  twin mirror signs (9 & 18)
    "WWWWWWWW............WWWWWWWWWW",  # 8
    "WWWW......................WWWW",  # 9  wide mirror chamber
    "WWWW.m........m.........m.WWWW",  # 10 mirror dials (5,14,24)
    "WS.p......................WWWW",  # 11 PACIFIST alcove: sign(1) floor(2) gate(3)
    "WWWW......................WWWW",  # 12
    "WWWWWWWW............WWWWWWWWWW",  # 13 narrowing back
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 14 bottleneck approach
    "WWWWWWWWWWWWGGGGWWWWWWWWWWWWWW",  # 15 4 gates (12-15) — need mirror alignment
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 16
    "WWWWWWWWWWWW.M..WWWWWWWWWWWWWW",  # 17 Daemon(13)
    "WWWWWWWWWWWW....WWWWWWWWWWWWWW",  # 18
    "WWWWWWWWWWWW.E..WWWWWWWWWWWWWW",  # 19 exit(13) — triggers ending
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",  # 20
]

RUINS_DAEMON_MONSTERS = {
    (13, 17): "Daemon",
}

RUINS_DAEMON_ITEMS = {}

RUINS_DAEMON_EXIT = {
    "pos": (13, 19),
    "target_zone": "ENDING",   # consumed by exploration.py to launch EndingScene
    "spawn": None,
    "conditions": [
        {
            "type": "defeat_monster",
            "pos": (13, 17),
            "fail_msg": (
                "* Daemon's presence fills\n"
                "  the corridor. You cannot\n"
                "  pass without confronting it."
            ),
        },
    ],
}

RUINS_DAEMON_SIGNS = {
    (13, 3): (
        "* [LOG] /proc/self mounted.\n"
        "  Every wall here is a\n"
        "  mirror. Every step is\n"
        "  watched. By you.\n\n"
        "  Mirrors reject orphan PIDs.\n"
        "  Resolve your PPID, then\n"
        "  make every reflection face\n"
        "  the process tree: sides to\n"
        "  self, self to the gate.\n\n"
        "  This is not a lock. It is\n"
        "  the system asking whether\n"
        "  you know who owns you now."
    ),
    (9, 7): (
        "* You see yourself turning\n"
        "  west. It doesn't turn\n"
        "  with you.\n\n"
        "  West mirror must face >"
    ),
    (18, 7): (
        "* You see yourself turning\n"
        "  east. It doesn't turn\n"
        "  with you.\n\n"
        "  East mirror must face <"
    ),
    (1, 11): (
        "* You see a copy of yourself,\n"
        "  also kneeling here.\n"
        "  Your hands are clean.\n"
        "  So are theirs.\n\n"
        "  The wall let you pass\n"
        "  because no process was\n"
        "  erased by your hand.\n"
        "  Take this with you:\n"
        "  the system remembered."
    ),
}

RUINS_DAEMON_DIAL_PUZZLES = {
    "identity_mirrors": {
        "states": 4,
        # Shares the same gate row; listed together so all mirrors must align.
        "gate_positions": [(12, 15), (13, 15), (14, 15), (15, 15)],
        "nodes": {
            (5, 10): {"initial": 0, "solution": 1},   # west reflection points east
            (14, 10): {"initial": 1, "solution": 2},  # self points down-path
            (24, 10): {"initial": 0, "solution": 3},  # east reflection points west
        },
        "required_flags": [("has_core_dump", "resolved PPID")],
        "fail_msg": (
            "* The mirrors show only\n"
            "  ???. Resolve your PPID\n"
            "  with the Core Dump first."
        ),
        "success_msg": (
            "* > SELF TRACE STABLE\n"
            "  The mirrors agree on\n"
            "  one process tree."
        ),
        "solved_msg": (
            "* Your reflection holds\n"
            "  still. PPID := 1."
        ),
    },
}


# ─── Zone Registry ───────────────────────────────────────────────────

ZONES = {
    "RUINS_1": {
        "map": RUINS_1_MAP,
        "monsters": RUINS_1_MONSTERS,
        "items": RUINS_1_ITEMS,
        "exit": RUINS_1_EXIT,
        "name": "/home/lost",
        "bgm": "overworld",
        "npcs": RUINS_1_NPCS,
        "puzzles": RUINS_1_PUZZLES,
        "signs": RUINS_1_SIGNS,
        "locked": {},
    },
    "RUINS_2": {
        "map": RUINS_2_MAP,
        "monsters": RUINS_2_MONSTERS,
        "items": RUINS_2_ITEMS,
        "exit": RUINS_2_EXIT,
        "name": "/var/log",
        "bgm": "overworld",
        "npcs": RUINS_2_NPCS,
        "puzzles": RUINS_2_PUZZLES,
        "signs": RUINS_2_SIGNS,
        "locked": RUINS_2_LOCKED,
        "vaults": RUINS_2_VAULTS,
        "dial_puzzles": RUINS_2_DIAL_PUZZLES,
    },
    "RUINS_BOSS": {
        "map": RUINS_BOSS_MAP,
        "monsters": RUINS_BOSS_MONSTERS,
        "items": RUINS_BOSS_ITEMS,
        "exit": RUINS_BOSS_EXIT,
        "name": "/dev/null",
        "bgm": "overworld",
        "npcs": {},
        "puzzles": {},
        "signs": RUINS_BOSS_SIGNS,
        "locked": {},
        "push_puzzles": RUINS_BOSS_PUSH_PUZZLES,
    },
    "RUINS_DAEMON": {
        "map": RUINS_DAEMON_MAP,
        "monsters": RUINS_DAEMON_MONSTERS,
        "items": RUINS_DAEMON_ITEMS,
        "exit": RUINS_DAEMON_EXIT,
        "name": "/proc/self",
        "bgm": "overworld",
        "npcs": {},
        "puzzles": {},
        "dial_puzzles": RUINS_DAEMON_DIAL_PUZZLES,
        "signs": RUINS_DAEMON_SIGNS,
        "locked": {},
    },
}


def get_zone(name):
    """Return zone data dict, or None."""
    return ZONES.get(name)
