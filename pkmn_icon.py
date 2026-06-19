"""Gen 1 substitute doll sprite for Pkmn on the exploration map.

Loads assets/substitute.png (16x16 cropped, 3 grayscale colors) and renders
at native resolution using half-block chars — 16 cols x 8 half-block rows.
Drawn centered on the monster's tile position.

Requires Pillow.  Falls back gracefully if missing.
"""

import os
import curses

_SPRITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "substitute.png")

_ALPHA = 50

# Substitute's 3 colors: RGB -> single-char ID
_RGBA_ID = {
    (0, 0, 0): 'K',        # blacK outline
    (96, 96, 96): 'D',     # Dark gray
    (168, 168, 168): 'L',  # Light gray
}

# 256-color fallback indices
_ID_256 = {'K': 233, 'D': 241, 'L': 249}

# Exact RGB in curses 0-1000 scale
_ID_RGB = {
    'K': (0, 0, 0),
    'D': (376, 376, 376),
    'L': (659, 659, 659),
}

_grid = None
_ready = False
_pair_attrs = {}


def _closest_id(r, g, b):
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

            tid = (_RGBA_ID.get((r0, g0, b0)) or _closest_id(r0, g0, b0)) if a0 >= _ALPHA else None
            bid = (_RGBA_ID.get((r1, g1, b1)) or _closest_id(r1, g1, b1)) if a1 >= _ALPHA else None

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
    _ensure()
    return len(_grid)


def width():
    _ensure()
    return len(_grid[0]) if _grid else 0


def register(color_mgr):
    """Register curses color pairs.  Returns True on success."""
    global _ready, _pair_attrs
    if _ready:
        return True
    _ensure()
    if not _grid or curses.COLORS < 256:
        return False

    combos = set()
    for row in _grid:
        for ch, fid, bid in row:
            if fid is not None or bid is not None:
                combos.add((fid, bid))

    use_exact = False
    id_to_ci = {}
    try:
        if curses.can_change_color():
            for i, (cid, rgb) in enumerate(_ID_RGB.items()):
                ci = 210 + i
                curses.init_color(ci, rgb[0], rgb[1], rgb[2])
                id_to_ci[cid] = ci
            use_exact = True
    except (curses.error, AttributeError):
        pass

    if not use_exact:
        id_to_ci = dict(_ID_256)

    for fid, bid in combos:
        fg = id_to_ci.get(fid, -1) if fid else -1
        bg = id_to_ci.get(bid, -1) if bid else -1
        pname = f"pi_{fid}_{bid}"
        color_mgr._pair(pname, fg, bg)
        attr = color_mgr.pairs.get(pname)
        if attr is not None:
            _pair_attrs[(fid, bid)] = attr

    _ready = bool(_pair_attrs)
    return _ready


def draw(r, center_y, center_x):
    """Draw the substitute icon centered on (center_y, center_x)."""
    if not _ready or not _grid:
        return False

    h = len(_grid)
    w = len(_grid[0]) if _grid else 0
    sy = center_y - h // 2
    sx = center_x - w // 2

    for ri, row in enumerate(_grid):
        y = sy + ri
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
            if y == r.height - 1 and x >= r.width - 1:
                continue
            try:
                r.scr.addstr(y, x, ch, attr)
            except curses.error:
                pass
    return True
