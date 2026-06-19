#!/usr/bin/env python3
"""Render the Gen 1 Pikachu sprite pixel-perfect in the terminal.

Uses Unicode half-block characters (U+2580 ▀) where each character cell
represents 2 vertical pixels: the upper pixel is the foreground color and
the lower pixel is the background color.  ANSI true-color escape codes
(\033[38;2;R;G;Bm / \033[48;2;R;G;Bm) paint each pixel's exact RGB.

Transparent pixels (alpha < 50) are rendered as the terminal's default
background (no color set).
"""

from PIL import Image

SPRITE_PATH = "assets/pikachu.png"
ALPHA_THRESHOLD = 50
HALF_BLOCK = "\u2580"  # ▀  — upper half block
RESET = "\033[0m"


def render_sprite(path: str = SPRITE_PATH) -> str:
    """Return a string of ANSI-colored half-block lines for the sprite."""
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    px = img.load()

    # Ensure even height (pad with transparent row if odd)
    if h % 2 != 0:
        h += 1

    lines: list[str] = []

    for y in range(0, h, 2):
        line_parts: list[str] = []
        for x in range(w):
            # Upper pixel (y) and lower pixel (y+1)
            r0, g0, b0, a0 = px[x, y] if y < img.size[1] else (0, 0, 0, 0)
            r1, g1, b1, a1 = px[x, y + 1] if (y + 1) < img.size[1] else (0, 0, 0, 0)

            top_visible = a0 >= ALPHA_THRESHOLD
            bot_visible = a1 >= ALPHA_THRESHOLD

            if top_visible and bot_visible:
                # ▀ with fg=top color, bg=bottom color
                line_parts.append(
                    f"\033[38;2;{r0};{g0};{b0}m"
                    f"\033[48;2;{r1};{g1};{b1}m"
                    f"{HALF_BLOCK}{RESET}"
                )
            elif top_visible:
                # Only upper pixel visible — ▀ with fg=top, default bg
                line_parts.append(
                    f"\033[38;2;{r0};{g0};{b0}m{HALF_BLOCK}{RESET}"
                )
            elif bot_visible:
                # Only lower pixel visible — ▄ with fg=bottom, default bg
                line_parts.append(
                    f"\033[38;2;{r1};{g1};{b1}m\u2584{RESET}"
                )
            else:
                # Both transparent — space
                line_parts.append(" ")

        # Strip trailing spaces for cleaner output
        line = "".join(line_parts).rstrip()
        lines.append(line)

    return "\n".join(lines)


def render_sprite_cropped(path: str = SPRITE_PATH) -> str:
    """Render only the bounding box (no surrounding transparency)."""
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        return ""
    # Expand bbox to even top boundary
    x0, y0, x1, y1 = bbox
    if y0 % 2 != 0:
        y0 -= 1
    if (y1 - y0) % 2 != 0:
        y1 += 1
    cropped = img.crop((x0, y0, x1, y1))
    # Save temp and render
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cropped.save(tmp.name)
    result = render_sprite(tmp.name)
    os.unlink(tmp.name)
    return result


if __name__ == "__main__":
    print()
    print(render_sprite_cropped())
    print()
