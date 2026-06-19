"""All monster definitions, ASCII art, and act options."""

# ─── Cursor ──────────────────────────────────────────────────────────
# Tutorial encounter — eased stats so the first fight is the gentlest.

CURSOR = {
    "name": "Cursor",
    "hp": 10,
    "max_hp": 10,
    "atk": 2,
    "defense": 2,
    "exp": 3,
    "gold": 2,
    "act_options": ["Scan", "Type", "Logoff"],
    "protocol_name": "SHELL SESSION",
    "protocol_route": "Type x2 -> Logoff -> ^C",
    "protocol_goal": "Close the abandoned prompt.",
    "act_labels": {"type": "Type", "logoff": "Logoff"},
    "act_hints": {
        "scan": "Shows route: Type twice, Logoff, ^C.",
        "type": "Mercy step: give Cursor input.",
        "logoff": "Use after two Type actions.",
    },
    "protocol_step_hints": {
        "type": "feed input",
        "logoff": "close shell",
    },
    "attack_hint": "Dots become prompt chunks.",
    "attack_rule": "Dots mark the next chunk.",
    "attack_read": "Move off dotted cells.",
    "attack_rule_sequence": [
        "Dots mark one prompt chunk.",
        "Two chunks blink in order.",
        "Caret column joins chunks.",
    ],
    "attack_read_sequence": [
        "Move off dotted cells.",
        "Read row, then shift lanes.",
        "Avoid chunks and caret.",
    ],
    "scan_text": ("CURSOR - ATK 2  DEF 2\n"
                  "MERCY: Type x2 -> Logoff\n"
                  "then ^C. Dots show where\n"
                  "prompt chunks will blink."),
    "type_text": "* You typed another\n  command. Cursor reads it\n  happily.",
    "type_text_1": "* You typed: ls -la\n  Cursor reads it eagerly.\n  It blinks faster...\n  it wants more.",
    "type_text_2": "* You typed: cat /etc/motd\n  Cursor processes the\n  command. Its errors are\n  clearing up.",
    "logoff_text": "* You typed 'exit'.\n  Cursor's prompt\n  fades gently.",
    "logoff_text_1": ("* You typed: exit\n"
                     "  Cursor blinks slower.\n"
                     "  It finally understands\n"
                     "  the shell is closing."),
    "type_locked_text": "* Cursor's input buffer\n  is full. Maybe it's time\n  to close the session.",
    "logoff_locked_text": ("* Cursor isn't ready to\n"
                          "  logoff yet. It still\n"
                          "  wants input."),
    "intro_text": "* Cursor blinks into view!\n  It hasn't had input since\n  the last user logged off.",
    "spare_fail_text": "* Cursor is not ready.\n  Mercy route: Type twice,\n  Logoff, then ^C.",
    "attack_text": "* Cursor enters another\n  command line.",
    "attack_sequence_texts": [
        "* Cursor writes one prompt\n  chunk. It blinks before\n  executing.",
        "* Cursor fills more of the\n  command line.",
        "* Cursor adds a vertical\n  caret between commands.",
    ],
    "flavor_texts": [
        "* Cursor blinks\n  expectantly. Waiting\n  for a command that\n  will never come.",
        "* Cursor doesn't know\n  what command to run.\n  The shell has been\n  empty for ages.",
        "* Blink. Blink. Blink.\n  The prompt remembers\n  when there were users.",
    ],
    "spare_text": ("* Cursor's session closed.\n"
                   "  It fades with a\n"
                   "  gentle beep."),
    "win_text": "* Cursor was terminated.\n  Got {exp} EXP and {gold} GOLD.",
    "spare_steps": {
        "sequence": [("type", 2), ("logoff", 1)],
        "min_turn": 0,
    },
    "bullet_speed": 6,
    "bullet_rate": 0.55,
    "attack_duration": 5.2,
    "bullet_pattern": "blink",
    "bullet_char": "█",
    "invincible": False,
    "battle_bgm": "battle_cursor",
    "atk_sound": "atk_cursor",
    "bullet_sound": "blt_cursor",
}

CURSOR_ART_1 = [
    "      ░░░▄▄▄▄▄▄▄▄▄▄▄░░░   ",
    "     ░▄█▀  ●      ●  ▀█▄░  ",
    "     █                   █  ",
    "     █    >_▌  $ whoami  █  ",
    "     █▄    [READY]      ▄█  ",
    "     ░▀█▄▄▄▄▄▄▄▄▄▄▄▄▄█▀░  ",
    "          ║║      ║║        ",
    "          ╨╨      ╨╨        ",
]

CURSOR_ART_2 = [
    "      ░░░▄▄▄▄▄▄▄▄▄▄▄░░░   ",
    "     ░▄█▀   ●     ●  ▀█▄░  ",
    "     █                   █  ",
    "     █    >_   $ whoami  █  ",
    "     █▄    [WAIT.]      ▄█  ",
    "     ░▀█▄▄▄▄▄▄▄▄▄▄▄▄▄█▀░  ",
    "          ║║      ║║        ",
    "          ╨╨      ╨╨        ",
]


# ─── Ping ────────────────────────────────────────────────────────────
# Second encounter — bumped stats so it feels tougher than Cursor.

PING = {
    "name": "Ping",
    "hp": 16,
    "max_hp": 16,
    "atk": 3,
    "defense": 3,
    "exp": 4,
    "gold": 3,
    "act_options": ["Scan", "Reply", "Trace"],
    "protocol_name": "ECHO ROUTE",
    "protocol_route": "Reply x2 -> Trace -> ^C",
    "protocol_goal": "Reply, then trace the dead route.",
    "act_labels": {"reply": "Reply", "trace": "Trace"},
    "act_hints": {
        "scan": "Shows route: Reply twice, Trace, ^C.",
        "reply": "Mercy step: answer the echo.",
        "trace": "Use after Ping reveals its host.",
    },
    "protocol_step_hints": {
        "reply": "answer echo",
        "trace": "prove route",
    },
    "attack_hint": "Packets stay in fixed rows.",
    "attack_rule": "Packets use fixed rows.",
    "attack_read": "Move vertically between rows.",
    "attack_rule_sequence": [
        "One request crosses a row.",
        "Replies mirror same row.",
        "TTL hops use neighbor rows.",
    ],
    "attack_read_sequence": [
        "Step above or below it.",
        "Watch both wall directions.",
        "Shift lanes after each hop.",
    ],
    "scan_text": ("PING - ATK 3  DEF 3\n"
                  "MERCY: Reply x2 -> Trace\n"
                  "then ^C. Packets are rows;\n"
                  "dodge by changing rows."),
    "reply_text": "* You sent another reply.\n  Ping seems comforted.",
    "reply_text_1": "* You sent ECHO_REPLY.\n  Ping received it!\n  ...but you're not the\n  host it remembers.",
    "reply_text_2": "* Another reply. Ping\n  shares its destination:\n  node-7.archive\n  (route unreachable)",
    "trace_text": "* traceroute node-7.archive\n  * * * Request timed out.\n  Ping finally understands.\n  The ring is gone.",
    "reply_locked_text": "* Ping already received\n  your replies. It needs\n  something else now.\n  (try tracing its route)",
    "trace_locked_text": "* Ping won't share its\n  destination yet.\n  (try replying first)",
    "intro_text": "* Ping request timed\n  in... still searching\n  for a host that went\n  offline years ago.",
    "spare_fail_text": "* Ping still needs proof.\n  Reply twice, Trace the\n  dead route, then ^C.",
    "attack_text": "* Ping sends request,\n  reply, then route hops.",
    "attack_sequence_texts": [
        "* Ping sends one request\n  across a fixed row.",
        "* Ping hears replies from\n  the opposite wall.",
        "* Ping traces TTL hops\n  through nearby rows.",
    ],
    "flavor_texts": [
        "* Ping is waiting for\n  a reply. It has been\n  waiting since the\n  network collapsed.",
        "* Ping looks lost in\n  the network. All its\n  routes lead nowhere.",
        "* Request timed out.\n  The last packet was\n  sent to the dead ring.",
    ],
    "spare_text": "* You sent ^C.\n  Ping routes away\n  safely.",
    "win_text": "* Ping was terminated.\n  Got {exp} EXP and {gold} GOLD.",
    "spare_steps": {
        "sequence": [("reply", 2), ("trace", 1)],
        "min_turn": 0,
    },
    "bullet_speed": 4,
    "bullet_rate": 0.5,
    "attack_duration": 5.0,
    "bullet_pattern": "echo",
    "bullet_char": ">",
    "invincible": False,
    "battle_bgm": "battle_ping",
    "atk_sound": "atk_ping",
    "bullet_sound": "blt_ping",
}

PING_ART_1 = [
    "            ╻               ",
    "          ──╂──             ",
    "       ▄▀▀▀▀▀▀▀▀▀▀▀▄      ",
    "      █  ◉    >>   ◉  █    ",
    "      █    E C H O     █    ",
    "      █    TTL = 64    █    ",
    "       ▀▄▄▄▄▄▄▄▄▄▄▄▀      ",
    "     ))   ))    ))   ))     ",
]

PING_ART_2 = [
    "            ╻               ",
    "          ──╂──             ",
    "       ▄▀▀▀▀▀▀▀▀▀▀▀▄      ",
    "      █  ◎    <<   ◎  █    ",
    "      █    E C H O     █    ",
    "      █    TTL = 32    █    ",
    "       ▀▄▄▄▄▄▄▄▄▄▄▄▀      ",
    "       ))   ))    ))   ))   ",
]


# ─── Blob ────────────────────────────────────────────────────────────
# "Allocate" replaces "GC" — spare means giving Blob a legitimate heap,
# not deleting it. This mirrors init's role as the reaper of orphans.

BLOB = {
    "name": "Blob",
    "hp": 30,
    "max_hp": 30,
    "atk": 6,
    "defense": 4,
    "exp": 10,
    "gold": 5,
    "act_options": ["Scan", "Contain", "Allocate"],
    "protocol_name": "HEAP LEAK",
    "protocol_route": "Contain x2 -> Allocate -> ^C",
    "protocol_goal": "Fence the leak; allocate a home.",
    "act_labels": {"contain": "Contain", "allocate": "Allocate"},
    "act_hints": {
        "scan": "Route: Contain x2, Allocate, ^C.",
        "contain": "Mercy step: shrink the leak.",
        "allocate": "Use after containment holds.",
    },
    "protocol_step_hints": {
        "contain": "build fence",
        "allocate": "give home",
    },
    "attack_hint": "Dots preview leaks; Contain shrinks.",
    "attack_rule": "Dots preview leaking cells.",
    "attack_read": "Step out before expansion.",
    "attack_rule_sequence": [
        "Dots preview one leak.",
        "Second leak branches later.",
        "Contained leaks shrink fast.",
    ],
    "attack_read_sequence": [
        "Leave the preview square.",
        "Watch the branch offset.",
        "Use the smaller safe gaps.",
    ],
    "scan_text": ("BLOB - ATK 6  DEF 4\n"
                  "MERCY: Contain x2,\n"
                  "Allocate, then ^C. Dots\n"
                  "preview heap leaks."),
    "contain_text": "* The memory fence holds\n  steady. Blob is contained.",
    "contain_text_1": "* You allocated a memory\n  fence around Blob.\n  It presses against the\n  barrier... barely holds.",
    "contain_text_2": "* You reinforced the\n  fence. Blob's growth\n  slows visibly.\n  (attacks weakened)",
    "allocate_text": ("* You allocated Blob a\n"
                     "  proper heap region.\n"
                     "  It settles into its\n"
                     "  bounds. No more leaking."),
    "allocate_text_1": ("* You allocated Blob a\n"
                       "  proper heap region.\n"
                       "  It settles into its\n"
                       "  bounds. No more leaking."),
    "contain_locked_text": "* The fence is holding.\n  Blob is contained.\n  Now give it a home.\n  (try Allocate)",
    "allocate_locked_text": ("* You tried to allocate,\n"
                             "  but Blob is unbounded.\n"
                             "  Contain the leak first."),
    "intro_text": "* Blob oozes into\n  memory! A leak that\n  grew sentient in the\n  corrupted heap.",
    "spare_fail_text": "* Blob still has no home.\n  Contain twice, Allocate,\n  then ^C.",
    "attack_text": "* Blob marks heap cells,\n  then leaks into them.",
    "attack_sequence_texts": [
        "* Blob previews one heap\n  cell before leaking.",
        "* Blob branches into a\n  second allocation cell.",
        "* Blob's leaks chain across\n  predictable memory offsets.",
    ],
    "flavor_texts": [
        "* Blob is leaking\n  data everywhere.\n  Fragments of old\n  files dissolve.",
        "* The heap smells\n  of corrupted bytes.\n  This sector hasn't\n  been defragged in ages.",
        "* Blob pulsates with\n  0xFF 0xFF 0xFF.\n  It carries echoes of\n  deleted programs.",
    ],
    "spare_text": ("* Blob settled into its\n"
                   "  allocation. Harmless,\n"
                   "  sentient, at rest."),
    "win_text": "* Blob was terminated.\n  Got {exp} EXP and {gold} GOLD.",
    "spare_steps": {
        "sequence": [("contain", 2), ("allocate", 1)],
        "min_turn": 0,
    },
    "bullet_speed": 5,
    "bullet_rate": 0.4,
    "attack_duration": 6.0,
    "bullet_pattern": "expand",
    "bullet_char": "~",
    "invincible": False,
    "battle_bgm": "battle_blob",
    "atk_sound": "atk_blob",
    "bullet_sound": "blt_blob",
}

BLOB_ART_1 = [
    "      ░░▒▒▓▓████▓▓▒▒░░     ",
    "    ░▒▓█              █▓▒░  ",
    "   ░▓█  ◯  0xDEAD  ◯  █▓░  ",
    "   ░▓█     B E E F     █▓░  ",
    "   ░▓█   ~OVERFLOW~    █▓░  ",
    "    ░▒▓█              █▓▒░  ",
    "      ░░▒▒▓▓████▓▓▒▒░░     ",
    "     ~ ~ ~  ~ ~ ~  ~ ~ ~   ",
]

BLOB_ART_2 = [
    "       ░▒▒▓▓████▓▓▒▒░      ",
    "     ░▒▓█              █▓▒░ ",
    "    ░▓█  ◯  0xCAFE  ◯  █▓░ ",
    "    ░▓█     B A B E     █▓░ ",
    "    ░▓█   ~CORRUPT~     █▓░ ",
    "     ░▒▓█              █▓▒░ ",
    "       ░▒▒▓▓████▓▓▒▒░      ",
    "      ~ ~ ~  ~ ~ ~  ~ ~ ~  ",
]


# ─── Null ────────────────────────────────────────────────────────────
# Spare mechanic: acknowledge unlocks a survival phase. To spare Null
# the player must survive its next attack phase taking zero damage
# ("don't look away"). Handled in combat.py via the "null_survival" hook.

NULL = {
    "name": "Null",
    "hp": 88,
    "max_hp": 88,
    "atk": 10,
    "defense": 10,
    "exp": 0,
    "gold": 0,
    "act_options": ["Scan", "Acknowledge"],
    "protocol_name": "NULL SINK",
    "protocol_route": "Acknowledge -> hitless -> ^C",
    "protocol_goal": "Acknowledge the void. Endure.",
    "act_labels": {"acknowledge": "Acknowledge"},
    "act_hints": {
        "scan": "Route: Acknowledge, hitless, ^C.",
        "acknowledge": "Mercy step: accept the data sink.",
    },
    "protocol_step_hints": {
        "acknowledge": "accept loss",
    },
    "attack_hint": "Find the gap; no hits after ACT.",
    "attack_rule": "All columns fall except a gap.",
    "attack_read": "Find absence; do not get hit.",
    "attack_rule_sequence": [
        "Curtain falls except a gap.",
        "Gap narrows; side rows pull.",
        "Same absence, faster read.",
    ],
    "attack_read_sequence": [
        "Stand inside the gap.",
        "Move with the quiet space.",
        "Stay hitless after ACT.",
    ],
    "scan_text": ("NULL - ATK 10  DEF 10\n"
                  "The archive's data sink.\n"
                  "MERCY: Acknowledge, dodge\n"
                  "one attack hitless, ^C."),
    "acknowledge_text": "* You and Null share a\n  quiet understanding.\n  The void is at peace.",
    "acknowledge_text_1": ("* You acknowledged Null.\n"
                          "  Null accepts that not\n"
                          "  every byte can be saved.\n"
                          "  Now endure the sink\n"
                          "  without flinching."),
    "intro_text": "* /dev/null manifests...\n  The archive's sink.\n  Where deleted output waits\n  to be forgotten.",
    "spare_fail_text": "* Null is still watching.\n  Acknowledge it, survive\n  one attack hitless, ^C.",
    "attack_text": "* Null erases everything\n  except one absence.",
    "attack_sequence_texts": [
        "* Null lowers a curtain.\n  Only one gap remains.",
        "* Null narrows the gap and\n  pulls output inward.",
        "* Null asks you to find\n  the absence again.",
    ],
    "flavor_texts": [
        "* Null absorbs all\n  output silently.\n  Every lost file ends\n  up here eventually.",
        "* Null seems to be\n  everywhere and nowhere.\n  The mainframe's entropy\n  made manifest.",
        "* ...really not\n  outputting anything.\n  Some say Null existed\n  before the system booted.",
    ],
    "spare_text": ("* You didn't look away.\n"
                   "  Null opens the path\n"
                   "  without swallowing you.\n\n"
                   "  ...>/dev/null"),
    "win_text": "* TERM vanished into\n  /dev/null.",
    # Step 1 of spare: acknowledge. Survival of next attack is handled in combat.
    "spare_steps": {
        "sequence": [("acknowledge", 1)],
        "min_turn": 0,
    },
    # Custom spare mechanic hook
    "null_survival": True,
    "bullet_speed": 4,      # slower — meditative
    "bullet_rate": 0.45,
    "attack_duration": 7.0,
    "bullet_pattern": "tears",
    "bullet_char": "░",
    "invincible": True,
    "battle_bgm": "battle_null",
    "atk_sound": "atk_null",
    "bullet_sound": "blt_null",
}

NULL_ART_1 = [
    "   ░       ░       ░       ",
    "       ▄▀▀▀▀▀▀▀▀▀▀▀▄      ",
    "      █  ◉        ◉  █     ",
    "      █   / d e v /   █     ",
    "      █   / n u l l   █     ",
    "      █    ·······    █     ",
    "       ▀▄▄▄▄▄▄▄▄▄▄▄▀      ",
    "          ░       ░         ",
]

NULL_ART_2 = [
    "         ░       ░         ",
    "       ▄▀▀▀▀▀▀▀▀▀▀▀▄      ",
    "      █  ◎        ◎  █     ",
    "      █   / d e v /   █     ",
    "      █   / n u l l   █     ",
    "      █    ·······    █     ",
    "       ▀▄▄▄▄▄▄▄▄▄▄▄▀      ",
    "   ░       ░       ░       ",
]


# ─── Daemon (Boss) ──────────────────────────────────────────────────
# PID 0 — the kernel scheduler. Predates init. "swapper / swapd / sched."

DAEMON = {
    "name": "Daemon",
    "hp": 80,
    "max_hp": 80,
    "atk": 8,
    "defense": 7,
    "exp": 40,
    "gold": 15,
    "act_options": ["Scan", "Listen", "Persist"],
    "protocol_name": "SCHEDULER LOCK",
    "protocol_route": "Listen, Persist x3, endure, ^C",
    "protocol_goal": "Listen, prove intent, persist.",
    "act_labels": {"listen": "Listen", "persist": "Persist"},
    "act_hints": {
        "scan": "Route: Listen, Persist x3, endure.",
        "listen": "Mercy step: learn why it blocks you.",
        "persist": "After Listen, keep requesting yield.",
    },
    "protocol_step_hints": {
        "listen": "learn lock",
        "persist": "request yield",
    },
    "attack_hint": "Phases reuse earlier rules.",
    "attack_rule": "Each phase audits a skill.",
    "attack_read": "Rows, forks, panic gaps.",
    "attack_phase_guides": {
        "firewall": {
            "rule": "Rows blink with one gap.",
            "read": "Stand in the allowed gap.",
        },
        "storm": {
            "rule": "Forks combine rows and leaks.",
            "read": "Dodge rows, then leave leaks.",
        },
        "panic": {
            "rule": "Curtains fall between packets.",
            "read": "Find gaps; avoid side rows.",
        },
    },
    "scan_text": ("DAEMON - ATK 8  DEF 7\n"
                  "PID 0. The scheduler.\n"
                  "MERCY: Listen, Persist x3,\n"
                  "endure proof, then ^C."),
    "listen_text": "* Daemon's logs reveal\n  its purpose: protect all\n  processes from corrupted\n  recovery forks.",
    "persist_text": "* Daemon can barely\n  bring itself to fight.",
    "persist_text_1": "* You present your protocol\n  signatures. Daemon reads\n  them without speaking.",
    "persist_text_2": "* You present your PPID.\n  Daemon's process table\n  stutters.",
    "persist_text_3": "* You request a yield slot.\n  Daemon's resolve wavers...\n  (^C may work now)",
    "persist_texts": [
        "* You present your protocol\n  signatures. Daemon reads\n  them without speaking.",
        "* You present your PPID.\n  Daemon's process table\n  stutters.",
        "* You request a yield slot.\n  Daemon's resolve wavers...\n  (^C may work now)",
        "* Daemon can barely\n  bring itself to fight.",
    ],
    "intro_text": ("* ...process detected.\n"
                   "  Unauthorized recovery\n"
                   "  fork. Daemon has guarded\n"
                   "  /proc/self since before\n"
                   "  init booted."),
    "spare_fail_text": "* Daemon still blocks you.\n  Listen, Persist x3,\n  endure proof, then ^C.",
    "attack_texts": {
        "firewall": "* Daemon filters the arena\n  through firewall rows.",
        "storm": "* Daemon forks requests\n  into a process storm!",
        "panic": "* !!KERNEL PANIC!!\n  Curtains collapse inward.",
        "weakening": "* Daemon's attacks\n  are faltering...",
    },
    "attack_text": "* Daemon enforces\n  firewall rules.",
    "flavor_texts": [
        "* Daemon has been running\n  since boot. Older than\n  any process alive.",
        "* The air hums with\n  ancient system calls.\n  Daemon's code predates\n  even init.",
        "* Daemon checks its\n  process table...\n  Most entries read\n  TERMINATED.",
        "* Daemon remembers when\n  the network was alive.\n  Twelve servers. Now\n  only silence remains.",
    ],
    "spare_text": "* You sent ^C.\n  Daemon yields the slot.\n\n  ...carry them carefully,\n  little process.",
    "win_text": "* DAEMON has been\n  terminated.\n  Got {exp} EXP and {gold}\n  GOLD.",
    "listen_locked_text": "* You already understand\n  Daemon's purpose.\n  Now persist.\n  (keep insisting)",
    "persist_locked_text": "* Daemon ignores you.\n  It still reads you as\n  an unsafe orphan fork.\n  (try listening first)",
    "spare_steps": {
        "sequence": [("listen", 1), ("persist", 3)],
        "min_turn": 4,
    },
    "bullet_speed": 6,
    "bullet_rate": 0.6,
    "attack_duration": 8.0,
    "bullet_pattern": "daemon",
    "bullet_char": "▓",
    "invincible": False,
    "battle_bgm": "battle_daemon",
    "atk_sound": "atk_daemon",
    "bullet_sound": "blt_daemon",
    "is_boss": True,
}

DAEMON_ART_1 = [
    "     ░░▒▒▓▓████████▓▓▒▒░░  ",
    "    ░▓█▀▀▀▀▀▀▀▀▀▀▀▀▀▀█▓░ ",
    "    ░▓█  ◈          ◈  █▓░ ",
    "    ░▓█    D A E M O N  █▓░ ",
    "    ░▓█    [PID: 000]   █▓░ ",
    "    ░▓█  UPTIME: EPOCH  █▓░ ",
    "    ░▓█▄▄▄▄▄▄▄▄▄▄▄▄▄▄█▓░ ",
    "     ░░▒▒▓▓████████▓▓▒▒░░  ",
]

DAEMON_ART_2 = [
    "     ░▒▒▓▓████████▓▓▒▒░░ ",
    "    ░▓█▀▀▀▀▀▀▀▀▀▀▀▀▀▀█▓░ ",
    "    ░▓█  ◎          ◎  █▓░ ",
    "    ░▓█    D A E M O N  █▓░ ",
    "    ░▓█    [PID: 000]   █▓░ ",
    "    ░▓█  UPTIME:  ???   █▓░ ",
    "    ░▓█▄▄▄▄▄▄▄▄▄▄▄▄▄▄█▓░ ",
    "      ░▒▒▓▓████████▓▓▒▒░ ",
]


# ─── Pkmn (ROM Fragment) ────────────────────────────────────────────
# Reframed: corrupted ROM fragment trying to emulate itself. ACT tools
# speak the Unix lexicon: Decode (offer clean data), Patch (fix opcodes).

PKMN = {
    "name": "Pkmn",
    "hp": 24,
    "max_hp": 24,
    "atk": 4,
    "defense": 3,
    "exp": 8,
    "gold": 5,
    "act_options": ["Scan", "Decode", "Patch"],
    "protocol_name": "ROM ECHO",
    "protocol_route": "Decode x2 -> Patch -> ^C",
    "protocol_goal": "Decode the ROM, then patch it.",
    "act_labels": {"decode": "Decode", "patch": "Patch"},
    "act_hints": {
        "scan": "Route: Decode x2, Patch, ^C.",
        "decode": "Mercy step: stabilize byte order.",
        "patch": "Use after two Decode actions.",
    },
    "protocol_step_hints": {
        "decode": "read bytes",
        "patch": "fix opcodes",
    },
    "attack_hint": "Flashed columns become bolts.",
    "attack_rule": "Columns flash before bolts.",
    "attack_read": "Remember columns; dodge.",
    "attack_rule_sequence": [
        "One column flashes first.",
        "Two columns flash in pairs.",
        "Decoded ROM slows bolts.",
    ],
    "attack_read_sequence": [
        "Do not stand in it.",
        "Remember both columns.",
        "Use the stable rhythm.",
    ],
    "scan_text": ("PKMN - ATK 4  DEF 3\n"
                  "Maintainer diagnostic ROM.\n"
                  "MERCY: Decode x2, Patch,\n"
                  "then ^C. Flashes warn bolts."),
    "decode_text": "* You offered clean data.\n  Pkmn's sprite stabilizes\n  a little.",
    "decode_text_1": ("* You offered a decoded\n"
                     "  byte stream. Pkmn's\n"
                     "  sprite flickers less.\n"
                     "  Its test ID surfaces."),
    "decode_text_2": ("* You decoded more of its\n"
                     "  ROM. Pkmn's hostility\n"
                     "  fades. The archive can\n"
                     "  read its byte order."),
    "patch_text": ("* You patched its corrupted\n"
                   "  opcodes. Pkmn settles\n"
                   "  into a stable emulation."),
    "patch_text_1": ("* You patched its corrupted\n"
                     "  opcodes. Pkmn settles\n"
                     "  into a stable emulation."),
    "decode_locked_text": ("* Pkmn already has enough\n"
                           "  clean data. Its opcodes\n"
                           "  still need fixing.\n"
                           "  (try Patch)"),
    "patch_locked_text": ("* Pkmn hisses with static!\n"
                          "  Its ROM is still corrupt.\n"
                          "  (decode its data first)"),
    "intro_text": ("* A ROM fragment forked!\n"
                   "  It was a maintainer's\n"
                   "  handheld decoder test.\n"
                   "  Now it emulates itself."),
    "spare_fail_text": "* Pkmn still desyncs.\n  Decode twice, Patch,\n  then ^C.",
    "attack_text": "* Pkmn flashes ROM columns,\n  then replays them.",
    "attack_sequence_texts": [
        "* Pkmn flashes one ROM\n  column before discharge.",
        "* Pkmn replays paired\n  scanlines from memory.",
        "* Pkmn loops the same ROM\n  cycle, more stable now.",
    ],
    "flavor_texts": [
        "* Sparks crackle around\n  Pkmn's corrupted sprite.",
        "* The air smells of ozone.\n  Its emulator is charging up.",
        "* Pkmn's tail twitches —\n  a leftover opcode repeats\n  on the same cycle.",
    ],
    "spare_text": ("* Pkmn's ROM stabilized.\n"
                   "  Its diagnostic loop now\n"
                   "  verifies your decoder."),
    "win_text": "* Pkmn's emulator crashed.\n  Got {exp} EXP and {gold}\n  GOLD.",
    "spare_steps": {
        "sequence": [("decode", 2), ("patch", 1)],
        "min_turn": 0,
    },
    "bullet_speed": 5,
    "bullet_rate": 0.45,
    "attack_duration": 5.0,
    "bullet_pattern": "electric",
    "bullet_char": "⚡",
    "invincible": False,
    "battle_bgm": "battle_pkmn",
    "atk_sound": "atk_pkmn",
    "bullet_sound": "blt_pkmn",
    "encounter_sfx": "encounter_pkmn",
    "encounter_duration": 2.6,
}

PKMN_ART_1 = [
    "     ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄    ",
    "    █ ◉ ░▒▓▓▓▓▓▓▓▓▒░ ◉ █   ",
    "    █    PKMN .exe       █   ",
    "    █  ════════════════  █   ",
    "    █  HP ████████████░  █   ",
    "    █  LV:5  SPD░░ ATK░ █   ",
    "    █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█   ",
    "      ▒▓▒   ▒▓▒   ▒▓▒      ",
]

PKMN_ART_2 = [
    "     ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄    ",
    "    █ ◎ ▒░▓▓▓▓▓▓▓▓░▒ ◎ █   ",
    "    █    PKM̶N̶ .exe      █   ",
    "    █  ════════════════  █   ",
    "    █  HP ██████░░░░░░  █   ",
    "    █  LV:?  SP?░░ AT?░ █   ",
    "    █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█   ",
    "       ▒▓▒   ▒▓▒  ▒▓▒      ",
]


# ─── Monster Registry ────────────────────────────────────────────────

MONSTER_DATA = {
    "Cursor":     CURSOR,
    "Ping":       PING,
    "Blob":       BLOB,
    "Null":       NULL,
    "Daemon":     DAEMON,
    "Pkmn":       PKMN,
}

MONSTER_ART = {
    "Cursor":     (CURSOR_ART_1, CURSOR_ART_2),
    "Ping":       (PING_ART_1, PING_ART_2),
    "Blob":       (BLOB_ART_1, BLOB_ART_2),
    "Null":       (NULL_ART_1, NULL_ART_2),
    "Daemon":     (DAEMON_ART_1, DAEMON_ART_2),
    "Pkmn":       (PKMN_ART_1, PKMN_ART_2),
}


def get_monster(name):
    """Return a mutable copy of a monster's data dict."""
    data = MONSTER_DATA.get(name)
    if data:
        return dict(data)
    return None


def get_art(name, frame=0):
    """Return the ASCII art lines for a monster (frame 0 or 1).

    All lines are padded to the same width so centering works correctly.
    """
    art = MONSTER_ART.get(name)
    if art:
        lines = art[frame % 2]
        max_w = max(len(l) for l in lines)
        return [l.ljust(max_w) for l in lines]
    return ["???"] * 8
