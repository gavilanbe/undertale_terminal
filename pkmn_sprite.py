"""Pikachu half-block sprite for combat rendering.

Uses Unicode half-block chars (U+2580/U+2584) with curses color pairs to
render the Gen 1 Pikachu sprite at NATIVE resolution (no scaling).
The cropped bounding box (~39x40 px) becomes ~39 cols x 20 half-block rows.

In combat, the sprite is drawn first and the UI (textbox/arena) overlays
the bottom portion — only the top ~12 rows stay visible (head, ears, body),
just like in Pokemon battles where the enemy sprite sits above the UI.

Requires Pillow for initial PNG load.  Falls back gracefully (draw() returns
False) if Pillow is missing, image not found, or terminal has < 256 colors.
"""

import os
import curses

_SPRITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "pikachu.png")

_ALPHA = 50

# Pikachu's 4 colors: exact RGBA -> single-char ID
_RGBA_ID = {
    (18, 11, 11): 'K',      # blacK outline
    (209, 156, 0): 'D',     # Dark yellow
    (255, 228, 104): 'L',   # Light yellow
    (255, 237, 255): 'W',   # White highlight
}

# 256-color fallback indices
_ID_256 = {'K': 233, 'D': 178, 'L': 222, 'W': 231}

# Exact RGB in curses 0-1000 scale (for init_color)
_ID_RGB = {
    'K': (71, 43, 43),
    'D': (820, 612, 0),
    'L': (1000, 894, 408),
    'W': (1000, 929, 1000),
}

_grid = None           # list[list[(char, fg_id|None, bg_id|None)]]
_ready = False         # True once curses pairs registered successfully
_pair_attrs = {}       # (fg_id, bg_id) -> curses attr int


def _closest_id(r, g, b):
    """Map an unexpected RGB to the nearest Pikachu color ID."""
    best, best_d = 'K', float('inf')
    for (cr, cg, cb), cid in _RGBA_ID.items():
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < best_d:
            best, best_d = cid, d
    return best


def _load():
    global _grid
    try:
        from PIL import Image
    except ImportError:
        _grid = []
        return
    if not os.path.exists(_SPRITE_PATH):
        _grid = []
        return

    img = Image.open(_SPRITE_PATH).convert('RGBA')
    bb = img.getbbox()
    if not bb:
        _grid = []
        return

    x0, y0, x1, y1 = bb
    if y0 % 2:
        y0 -= 1
    if (y1 - y0) % 2:
        y1 += 1

    crop = img.crop((x0, y0, x1, y1))
    w, h = crop.size
    px = crop.load()

    rows = []
    for y in range(0, h, 2):
        row = []
        for x in range(w):
            r0, g0, b0, a0 = px[x, y]
            r1, g1, b1, a1 = px[x, y + 1] if y + 1 < h else (0, 0, 0, 0)

            if a0 >= _ALPHA:
                tid = _RGBA_ID.get((r0, g0, b0)) or _closest_id(r0, g0, b0)
            else:
                tid = None
            if a1 >= _ALPHA:
                bid = _RGBA_ID.get((r1, g1, b1)) or _closest_id(r1, g1, b1)
            else:
                bid = None

            if tid and bid:
                row.append(('\u2580', tid, bid))
            elif tid:
                row.append(('\u2580', tid, None))
            elif bid:
                row.append(('\u2584', bid, None))
            else:
                row.append((' ', None, None))
        rows.append(row)
    _grid = rows


def _ensure():
    if _grid is None:
        _load()


def height():
    """Number of terminal rows the sprite occupies (half-block)."""
    _ensure()
    return len(_grid)


def width():
    """Number of terminal columns the sprite occupies."""
    _ensure()
    return len(_grid[0]) if _grid else 0


def register(color_mgr):
    """Register curses color pairs for the sprite.  Returns True on success."""
    global _ready, _pair_attrs
    if _ready:
        return True
    _ensure()
    if not _grid or curses.COLORS < 256:
        return False

    # Collect unique (fg_id, bg_id) combos
    combos = set()
    for row in _grid:
        for ch, fid, bid in row:
            if fid is not None or bid is not None:
                combos.add((fid, bid))

    # Try exact RGB via init_color (high-numbered slots to avoid conflicts)
    use_exact = False
    id_to_ci = {}
    try:
        if curses.can_change_color():
            for i, (cid, rgb) in enumerate(_ID_RGB.items()):
                ci = 200 + i
                curses.init_color(ci, rgb[0], rgb[1], rgb[2])
                id_to_ci[cid] = ci
            use_exact = True
    except (curses.error, AttributeError):
        pass

    if not use_exact:
        id_to_ci = dict(_ID_256)

    # Register one pair per unique (fg, bg) combo
    for fid, bid in combos:
        fg = id_to_ci.get(fid, -1) if fid else -1
        bg = id_to_ci.get(bid, -1) if bid else -1
        pname = f"pk_{fid}_{bid}"
        color_mgr._pair(pname, fg, bg)
        attr = color_mgr.pairs.get(pname)
        if attr is not None:
            _pair_attrs[(fid, bid)] = attr

    _ready = bool(_pair_attrs)
    return _ready


def draw(r, start_y, center_x):
    """Draw the Pikachu sprite via the Renderer.  Returns True if drawn.

    Rows that fall outside the screen or get overwritten by later UI draws
    (textbox, arena) are harmless — curses handles the overlap naturally.
    """
    if not _ready or not _grid:
        return False

    w = len(_grid[0]) if _grid else 0
    sx = center_x - w // 2

    for ri, row in enumerate(_grid):
        y = start_y + ri
        if y < 0 or y >= r.height:
            continue
        for ci, (ch, fid, bid) in enumerate(row):
            if ch == ' ':
                continue
            x = sx + ci
            if x < 0 or x >= r.width:
                continue
            attr = _pair_attrs.get((fid, bid))
            if attr is None:
                continue
            # Avoid bottom-right corner crash
            if y == r.height - 1 and x >= r.width - 1:
                continue
            try:
                r.scr.addstr(y, x, ch, attr)
            except curses.error:
                pass
    return True
