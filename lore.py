"""Lore trace helpers for the pause menu and objective hints."""

PROTOCOL_TRACE = [
    ("protocol_cursor_resolved", "Cursor", "First shell input accepted."),
    ("protocol_ping_resolved", "Ping", "Dead network route proven."),
    ("protocol_pkmn_resolved", "Pkmn", "Archive byte order decoded."),
    ("protocol_blob_resolved", "Blob", "Heap leak given boundaries."),
    ("protocol_null_resolved", "Null", "Loss acknowledged without flinching."),
    ("protocol_daemon_resolved", "Daemon", "Scheduler intent resolved."),
]


def _flag(game, key):
    return bool(game.flags.get(key))


def _puzzle(game, key):
    return bool(game.puzzle_state.get(key))


def current_objective(game):
    """Return the next story objective as a short sentence."""
    zone = game.current_zone

    if zone == "RUINS_1":
        if not _puzzle(game, "RUINS_1:tutorial"):
            return "Open the first switch gate."
        if not _puzzle(game, "RUINS_1:boot_sequence"):
            return "Boot order: PID1, HOME, NET."
        if not _flag(game, "protocol_cursor_resolved"):
            return "Sync Cursor at the exit scanner."
        return "Leave /home/lost for /var/log."

    if zone == "RUINS_2":
        ping = _flag(game, "protocol_ping_resolved")
        pkmn = _flag(game, "protocol_pkmn_resolved")
        if not ping and not pkmn:
            return "Resolve Ping west and Pkmn east."
        if not ping:
            return "West wing still needs Ping."
        if not pkmn:
            return "East wing still needs Pkmn."
        if not _flag(game, "vault_opened"):
            return "Open the vault for archive checksum."
        if not _puzzle(game, "RUINS_2:router_compile"):
            return "Compile the router toward /dev/null."
        if not _flag(game, "protocol_blob_resolved"):
            return "Resolve Blob on the south route."
        return "Enter /dev/null."

    if zone == "RUINS_BOSS":
        if not _flag(game, "protocol_null_resolved"):
            return "Acknowledge Null and endure."
        if not _flag(game, "vault_opened"):
            return "Return to /var/log for checksum."
        if not _puzzle(game, "RUINS_BOSS:checksum_socket"):
            return "Seat checksum block in the socket."
        if not _flag(game, "has_core_dump"):
            return "Use the Core Dump to resolve PPID."
        return "Proceed to /proc/self."

    if zone == "RUINS_DAEMON":
        if not _flag(game, "has_core_dump"):
            return "Use Core Dump; mirrors reject orphans."
        if not _puzzle(game, "RUINS_DAEMON:identity_mirrors"):
            return "Align mirrors to the process tree."
        if not _flag(game, "protocol_daemon_resolved"):
            return "Confront Daemon, PID 0."
        return "Exit to the maintenance console."

    return "Recover the archive."


def identity_line(game):
    if game.ppid == 1 or _flag(game, "has_core_dump"):
        return "PPID := 1; init adopted the orphan."
    return "PPID unknown; Core Dump can prove origin."


def route_consequence_line(game):
    if game.kill_count == 0:
        return "Clean route intact: ACT preserves recovery."
    return "Forced closures logged; ending will remember."


def protocol_count(game):
    return sum(1 for flag, _name, _text in PROTOCOL_TRACE if _flag(game, flag))


def missing_protocol_names(game):
    return [
        name for flag, name, _text in PROTOCOL_TRACE
        if not _flag(game, flag)
    ]


def trace_lines(game):
    """Return (label, text) pairs for the pause Trace tab."""
    done = protocol_count(game)
    missing = missing_protocol_names(game)
    lines = [
        ("Objective", current_objective(game)),
        ("Identity", identity_line(game)),
        ("Route", route_consequence_line(game)),
        ("Signatures", f"{done}/{len(PROTOCOL_TRACE)} synced"),
    ]

    if missing:
        lines.append(("Missing", ", ".join(missing[:3])))
    else:
        lines.append(("Missing", "None. Recovery proof complete."))

    lines.append(("", ""))
    for flag, name, text in PROTOCOL_TRACE:
        state = "OK" if _flag(game, flag) else "--"
        lines.append((state, f"{name}: {text}"))

    return lines
