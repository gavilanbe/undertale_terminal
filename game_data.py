"""Game data: tile constants, dialogue texts."""

# ─── Map Tiles ────────────────────────────────────────────────────────
TILE_WALL = 'W'
TILE_FLOOR = '.'
TILE_FLOWER = 'f'
TILE_SIGN = 'S'
TILE_SIGN2 = 'R'        # second sign (corridor hint)
TILE_TRIGGER = 'T'
TILE_MONSTER = 'M'       # visible monster on map (triggers combat)
TILE_COLUMN = 'c'
TILE_PATH = ':'          # path marker (guide the player)
TILE_VOID = ' '
TILE_PLAYER_START = 'P'
TILE_SAVE = 'x'          # save point
TILE_EXIT = 'E'           # zone exit
TILE_ITEM = 'i'           # item pickup

# Phase 1: new tile types
TILE_NPC = 'N'            # NPC (non-player character)
TILE_SWITCH = '#'          # puzzle switch
TILE_GATE = 'G'            # puzzle gate (closed = solid)
TILE_GATE_OPEN = 'g'       # puzzle gate (open = walkable)
TILE_LOCKED = 'L'          # locked terminal (requires BUF / keys)

# Phase 2: secret + conditional tiles
TILE_SECRET = '_'          # looks like wall, is walkable (hidden corridor)
TILE_PACIFIST = 'p'        # walkable ONLY if game.kill_count == 0
TILE_VAULT = 'V'           # vault gate: locked terminal in door form
TILE_PUSH_BLOCK = 'B'      # movable data block for map puzzles
TILE_SOCKET = 'O'          # target socket for push blocks
TILE_ROUTER = 'r'          # rotatable routing node
TILE_MIRROR = 'm'          # rotatable mirror node

SOLID_TILES = {TILE_WALL, TILE_COLUMN, TILE_VOID, TILE_NPC, TILE_GATE,
               TILE_LOCKED, TILE_VAULT, TILE_PUSH_BLOCK,
               TILE_ROUTER, TILE_MIRROR}

# ─── Sign Texts (legacy fallbacks) ─────────────────────────────────
SIGN_TEXT = (
    "* [LOG] WARNING: Unauthorized\n"
    "  process detected. Turn back.\n"
    "  Firewall active ahead."
)

SIGN2_TEXT = (
    "* [LOG] ALERT: Hostile process\n"
    "  ahead. Handle with caution.\n"
    "  Last scan: CORRUPTED."
)

# ─── Intro Text (multi-page for Phase 1) ─────────────────────────────
INTRO_TEXT = [
    (
        "* > BOOT SEQUENCE INITIATED\n"
        "  > LOADING PROCESS...\n"
        "  > PID ASSIGNED: ???\n"
        "  > PPID: LOST\n\n"
        "  You wake as a recovery\n"
        "  child whose parent process\n"
        "  vanished before launch."
    ),
    (
        "* This mainframe was the\n"
        "  archive node for a dead\n"
        "  network. Sector 7 panicked,\n"
        "  and every survivor froze\n"
        "  mid-protocol."
    ),
    (
        "* To mount recovery, collect\n"
        "  clean protocol signatures.\n"
        "  You can force processes\n"
        "  closed, or understand them\n"
        "  enough to exit cleanly.\n\n"
        "  [WASD] Move  [Z] Interact\n"
        "  [I/TAB] Pause"
    ),
]
