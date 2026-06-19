"""JSON save/load to ~/.undertale_terminal/save.json."""

import json
import os

SAVE_PATH_ENV = "UNDERSHELL_SAVE_PATH"
DEFAULT_SAVE_DIR = os.path.expanduser("~/.undertale_terminal")
DEFAULT_SAVE_PATH = os.path.join(DEFAULT_SAVE_DIR, "save.json")
SAVE_DIR = DEFAULT_SAVE_DIR
SAVE_PATH = DEFAULT_SAVE_PATH
SAVE_VERSION = 3


def get_save_path():
    """Return the active save path, allowing tests/tools to override it."""
    path = os.environ.get(SAVE_PATH_ENV, DEFAULT_SAVE_PATH)
    return os.path.abspath(os.path.expanduser(path))


def get_save_dir():
    """Return the directory that contains the active save file."""
    return os.path.dirname(get_save_path())


def save_exists():
    """Return True if a save file exists."""
    return os.path.isfile(get_save_path())


def save_game(game):
    """Serialize player state to JSON save file."""
    data = {
        "version": SAVE_VERSION,
        "player_name": game.player_name,
        "player_hp": game.player_hp,
        "player_max_hp": game.player_max_hp,
        "player_lv": game.player_lv,
        "player_exp": game.player_exp,
        "player_atk": game.player_atk,
        "player_buf": game.player_buf,
        "player_max_buf": game.player_max_buf,
        "gold": game.gold,
        "difficulty": game.difficulty,
        "inventory": list(game.inventory),
        "current_zone": game.current_zone,
        "player_x": game.player_x,
        "player_y": game.player_y,
        "defeated_monsters": list(game.defeated_monsters),
        "collected_items": list(game.collected_items),
        "flags": dict(game.flags),
        "puzzle_state": dict(game.puzzle_state),
        "kill_count": game.kill_count,
        "spare_count": game.spare_count,
        # v3 fields
        "ppid": game.ppid,
    }
    os.makedirs(get_save_dir(), exist_ok=True)
    try:
        with open(get_save_path(), 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def load_game(game):
    """Restore player state from save file. Returns True on success.

    Accepts older save versions and fills new fields with sensible defaults.
    """
    if not save_exists():
        return False
    try:
        with open(get_save_path(), 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    if not isinstance(data, dict):
        return False

    version = data.get("version", 1)
    if version > SAVE_VERSION:
        # Save from a newer version — refuse rather than truncate state
        return False

    game.player_name = data.get("player_name", "HUMAN")
    game.player_hp = data.get("player_hp", 20)
    game.player_max_hp = data.get("player_max_hp", 20)
    game.player_lv = data.get("player_lv", 1)
    game.player_exp = data.get("player_exp", 0)
    game.player_atk = data.get("player_atk", 10)
    game.player_buf = data.get("player_buf", 3)
    game.player_max_buf = data.get("player_max_buf", 3)
    game.gold = data.get("gold", 0)
    game.difficulty = data.get("difficulty", "NORMAL")
    game.inventory = data.get("inventory", [])
    game.current_zone = data.get("current_zone", "RUINS_1")
    game.player_x = data.get("player_x", 10)
    game.player_y = data.get("player_y", 3)
    game.defeated_monsters = set(data.get("defeated_monsters", []))
    game.collected_items = set(data.get("collected_items", []))
    game.flags = data.get("flags", {})
    game.puzzle_state = data.get("puzzle_state", {})
    game.kill_count = data.get("kill_count", 0)
    game.spare_count = data.get("spare_count", 0)
    # v3
    game.ppid = data.get("ppid", None)
    return True


def delete_save():
    """Remove the save file."""
    if save_exists():
        try:
            os.remove(get_save_path())
        except Exception:
            pass
