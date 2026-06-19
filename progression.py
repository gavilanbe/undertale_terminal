"""LV/EXP formulas, difficulty modifiers, and stat scaling."""

# ─── EXP Thresholds ──────────────────────────────────────────────────
# Tuned to actual content (~60 EXP total): LV2=6, LV3=18, LV4=36, LV5=60
EXP_THRESHOLDS = [0, 6, 18, 36, 60]
MAX_LV = len(EXP_THRESHOLDS)

# Per-level-up bonuses
HP_PER_LV = 4
ATK_PER_LV = 2


# ─── Difficulty Modifiers ────────────────────────────────────────────

DIFFICULTY = {
    "EASY": {
        "base_max_hp":       30,
        "base_max_buf":      5,
        "base_atk":          12,
        "enemy_damage_mult": 0.7,
        "bullet_speed_mult": 0.8,
        "bullet_rate_mult":  1.4,
        "label": "EASY",
        "desc":  "Safe mode. More memory,\nslower processes.",
    },
    "NORMAL": {
        "base_max_hp":       20,
        "base_max_buf":      3,
        "base_atk":          10,
        "enemy_damage_mult": 1.0,
        "bullet_speed_mult": 1.0,
        "bullet_rate_mult":  1.0,
        "label": "NORMAL",
        "desc":  "Standard boot.\nDefault parameters.",
    },
    "HARD": {
        "base_max_hp":       15,
        "base_max_buf":      1,
        "base_atk":          8,
        "enemy_damage_mult": 1.5,
        "bullet_speed_mult": 1.25,
        "bullet_rate_mult":  0.7,
        "label": "HARD",
        "desc":  "Kernel panic. Less memory,\nhostile environment.",
    },
}


def exp_for_next_lv(current_lv):
    """Return EXP needed for next level, or None if max."""
    if current_lv >= MAX_LV:
        return None
    return EXP_THRESHOLDS[current_lv]  # index = current_lv means next threshold


def gain_exp(game, amount):
    """Add EXP and handle level-ups. Returns list of level-up messages."""
    messages = []
    game.player_exp += amount
    while game.player_lv < MAX_LV:
        needed = EXP_THRESHOLDS[game.player_lv]  # threshold for next level
        if game.player_exp >= needed:
            game.player_lv += 1
            game.player_max_hp += HP_PER_LV
            game.player_atk += ATK_PER_LV
            game.player_hp = game.player_max_hp  # full heal on level-up
            messages.append(
                f"* Your LOVE increased!\n"
                f"  LV {game.player_lv}  "
                f"HP {game.player_max_hp}  "
                f"ATK {game.player_atk}"
            )
        else:
            break
    return messages


def get_difficulty_mod(game, key):
    """Get a difficulty modifier value for the current game difficulty."""
    diff = DIFFICULTY.get(game.difficulty, DIFFICULTY["NORMAL"])
    return diff.get(key, 1.0)
