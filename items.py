"""Item database, inventory helpers, and usage logic."""

# ─── Item Definitions ────────────────────────────────────────────────

ITEMS = {
    "Cookie": {
        "heal": 10,
        "desc": "A browser cookie. Tastes like tracking data.",
        "use_msg": "* You consumed the Cookie.\n  (+{heal} HP)",
        "price": 5,
    },
    "Cache Fragment": {
        "heal": 12,
        "desc": "Cached data from a forgotten request.",
        "use_msg": "* You loaded the Cache Fragment.\n  (+{heal} HP)",
    },
    "Patch": {
        "heal": 8,
        "desc": "A software patch. Already applied once.",
        "use_msg": "* You applied the Patch.\n  (+{heal} HP)",
        "price": 8,
    },
    "Full Backup": {
        "heal": 999,  # full heal sentinel
        "desc": "A complete system restore point.",
        "use_msg": "* You restored from Full Backup.\n  HP fully restored!",
    },
    "RAM Juice": {
        "heal": 14,
        "desc": "Freshly squeezed volatile memory.",
        "use_msg": "* You drank the RAM Juice.\n  (+{heal} HP)",
    },
    # Phase 1: new items
    "Firewall Shard": {
        "type": "combat_buff",
        "stat": "def",
        "value": 2,
        "desc": "A fragment of firewall code. Hardens defenses.",
        "use_msg": "* Firewall rules applied!\n  (+{value} DEF this battle)",
        "price": 15,
    },
    "Exploit Kit": {
        "type": "combat_buff",
        "stat": "atk",
        "value": 3,
        "desc": "Offensive payload. Handle with care.",
        "use_msg": "* Exploit loaded!\n  (+{value} ATK this battle)",
        "price": 20,
    },
    "Buffer Patch": {
        "type": "buf_restore",
        "value": 2,
        "desc": "Restores buffer memory allocation.",
        "use_msg": "* Buffer patched!\n  (+{value} BUF)",
        "price": 10,
    },
    "Core Dump": {
        "type": "key_item",
        "flag": "has_core_dump",
        "ppid": 1,
        "desc": "Your interrupted launch dump. Resolves PPID.",
        "use_msg": ("* You analyzed the Core Dump.\n"
                    "  Original parent: terminated.\n"
                    "  init adopts the orphan:\n"
                    "  PPID := 1."),
        "price": 50,
    },
    # ── Vault keys (dropped by killing specific monsters) ─────────────
    "Replication Key": {
        "type": "vault_key",
        "desc": "Echo signature lifted from a Ping process.",
    },
    "Substitute Key": {
        "type": "vault_key",
        "desc": "Patched ROM byte from a corrupted Pkmn fragment.",
    },
}

MAX_INVENTORY = 8

# Starting items per difficulty
STARTING_ITEMS = {
    "EASY":   ["Cookie", "Cookie", "Patch"],
    "NORMAL": ["Cookie"],
    "HARD":   [],
}


# ─── Inventory Functions ─────────────────────────────────────────────

def add_item(game, name):
    """Add an item to the player's inventory. Returns True if added."""
    if name not in ITEMS:
        return False
    if len(game.inventory) >= MAX_INVENTORY:
        return False
    game.inventory.append(name)
    return True


def remove_item(game, index):
    """Remove item at given index from inventory."""
    if 0 <= index < len(game.inventory):
        game.inventory.pop(index)


def item_usable_overworld(name):
    """True if this item type has a valid effect outside combat."""
    item = ITEMS.get(name)
    if not item:
        return False
    t = item.get("type", "heal")
    return t in ("heal", "buf_restore", "key_item")


def consume_key(game, name):
    """Remove one instance of a vault key from the inventory.

    Returns True if the key was found and consumed.
    """
    if name in game.inventory:
        game.inventory.remove(name)
        return True
    return False


def use_item(game, index):
    """Use item at index. Returns (value, message, item_type) or None if invalid.

    item_type is one of: "heal", "combat_buff", "buf_restore", "key_item"
    """
    if index < 0 or index >= len(game.inventory):
        return None
    name = game.inventory[index]
    item = ITEMS.get(name)
    if not item:
        return None

    item_type = item.get("type", "heal")

    if item_type == "heal":
        heal = item["heal"]
        if heal >= 999:
            hp_gained = game.player_max_hp - game.player_hp
            game.player_hp = game.player_max_hp
        else:
            hp_gained = min(heal, game.player_max_hp - game.player_hp)
            game.player_hp = min(game.player_max_hp, game.player_hp + heal)
        msg = item["use_msg"].format(heal=hp_gained if item["heal"] < 999 else "MAX")
        game.inventory.pop(index)
        return (hp_gained, msg, "heal")

    elif item_type == "combat_buff":
        stat = item["stat"]
        value = item["value"]
        if stat == "atk":
            game.combat_atk_bonus += value
        elif stat == "def":
            game.combat_def_bonus += value
        msg = item["use_msg"].format(value=value)
        game.inventory.pop(index)
        return (value, msg, "combat_buff")

    elif item_type == "buf_restore":
        value = item["value"]
        restored = min(value, game.player_max_buf - game.player_buf)
        game.player_buf = min(game.player_max_buf, game.player_buf + value)
        msg = item["use_msg"].format(value=restored)
        game.inventory.pop(index)
        return (restored, msg, "buf_restore")

    elif item_type == "key_item":
        flag = item.get("flag")
        if flag:
            game.flags[flag] = True
        ppid = item.get("ppid")
        if ppid is not None:
            game.ppid = ppid
        msg = item["use_msg"]
        game.inventory.pop(index)
        return (0, msg, "key_item")

    return None
