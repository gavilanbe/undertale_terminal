#!/usr/bin/env python3
"""
UNDERSHELL — A terminal-based RPG.

Controls:
  WASD / Arrow keys  - Move / Navigate menus
  Z / Enter          - Confirm / Interact
  X                  - Cancel / Back
  ESC                - Quit

Run:
  python main.py
"""

import curses
import sys
import os

def main():
    # Ensure assets exist
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    required_assets = ["bgm_title.wav", "bgm_overworld.wav", "sfx_select.wav"]
    missing_assets = (
        not os.path.exists(assets_dir)
        or any(not os.path.exists(os.path.join(assets_dir, name))
               for name in required_assets)
    )
    if missing_assets:
        print("Generating sound assets...")
        from generate_sounds import generate_all
        generate_all()
        print()

    from engine import Game
    game = Game()
    try:
        curses.wrapper(game.run)
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure terminal is restored
        try:
            curses.endwin()
        except Exception:
            pass

    print("\nProcess terminated. Run './undershell' to reboot.\n")


if __name__ == "__main__":
    main()
