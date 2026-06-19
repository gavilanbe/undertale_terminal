"""Audio manager using pygame.mixer. Gracefully degrades if unavailable."""

import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

SOUND_FILES = {
    "step":      "sfx_step.wav",
    "select":    "sfx_select.wav",
    "encounter": "sfx_encounter.wav",
    "hit":       "sfx_hit.wav",
    "attack":    "sfx_attack.wav",
    "heal":      "sfx_heal.wav",
    "text":      "sfx_text.wav",
    "spare":     "sfx_spare.wav",
    "save":      "sfx_save.wav",
    "item":      "sfx_item.wav",
    "levelup":   "sfx_levelup.wav",
    "ominous":   "sfx_ominous.wav",
    # Monster-specific attack start SFX
    "atk_cursor": "sfx_atk_cursor.wav",
    "atk_ping":   "sfx_atk_ping.wav",
    "atk_blob":   "sfx_atk_blob.wav",
    "atk_null":   "sfx_atk_null.wav",
    "atk_daemon": "sfx_atk_daemon.wav",
    # Bullet spawn SFX
    "blt_cursor":  "sfx_blt_cursor.wav",
    "blt_ping":    "sfx_blt_ping.wav",
    "blt_blob":    "sfx_blt_blob.wav",
    "blt_null":    "sfx_blt_null.wav",
    "blt_daemon":  "sfx_blt_daemon.wav",
    # Pkmn-specific SFX
    "atk_pkmn":    "sfx_atk_pkmn.wav",
    "blt_pkmn":    "sfx_blt_pkmn.wav",
    "cry_pkmn":    "sfx_cry_pkmn.wav",
    # Monster encounter SFX
    "encounter_pkmn": "sfx_encounter_pkmn.wav",
    # Timing feedback
    "critical":    "sfx_critical.wav",
    "whiff":       "sfx_whiff.wav",
    # v1.3
    "streak":      "sfx_streak.wav",
    "seq_step":    "sfx_seq_step.wav",
    "seq_reject":  "sfx_seq_reject.wav",
    "seq_solve":   "sfx_seq_solve.wav",
    "death":       "sfx_death.wav",
    "menu_open":   "sfx_menu_open.wav",
}

BGM_FILES = {
    "title":         "bgm_title.wav",
    "overworld":     "bgm_overworld.wav",
    "battle":        "bgm_battle.wav",
    "battle_cursor": "bgm_battle_cursor.wav",
    "battle_ping":   "bgm_battle_ping.wav",
    "battle_blob":   "bgm_battle_blob.wav",
    "battle_null":   "bgm_battle_null.wav",
    "battle_daemon": "bgm_battle_daemon.wav",
    "battle_pkmn":   "bgm_battle_pkmn.wav",
}


class AudioManager:
    """Thin wrapper around pygame.mixer."""

    def __init__(self):
        self._mixer = None
        self._sounds = {}
        self._bgm = {}
        self._available = False
        self._current_bgm = None

    def init(self):
        try:
            import pygame
            pygame.mixer.pre_init(22050, -16, 1, 512)
            pygame.mixer.init()
            self._mixer = pygame.mixer
            self._available = True
        except Exception:
            self._available = False
            return

        # Per-sound volume overrides. Quiet SFX sit at 0.15–0.3, punchy
        # feedback at 0.5–0.8. Defaults to 1.0 when unlisted.
        VOLUMES = {
            "step":       0.3,
            "text":       0.2,
            "ominous":    0.15,
            "menu_open":  0.35,
            "streak":     0.45,
            "seq_step":   0.45,
            "seq_reject": 0.55,
            "seq_solve":  0.7,
            "death":      0.75,
            "critical":   0.7,
            "whiff":      0.35,
            "levelup":    0.8,
            "save":       0.55,
            "heal":       0.55,
            "item":       0.55,
        }

        # Load SFX
        for name, fname in SOUND_FILES.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                try:
                    self._sounds[name] = self._mixer.Sound(path)
                    if name in VOLUMES:
                        self._sounds[name].set_volume(VOLUMES[name])
                    elif name.startswith("blt_"):
                        self._sounds[name].set_volume(0.15)
                except Exception:
                    pass

        # Load BGM
        for name, fname in BGM_FILES.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                self._bgm[name] = path

    def play(self, name):
        if not self._available:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def play_bgm(self, name, loops=-1, volume=0.4):
        if not self._available:
            return
        path = self._bgm.get(name)
        if path:
            try:
                if self._current_bgm == name and self._mixer.music.get_busy():
                    self._mixer.music.set_volume(volume)
                    return
                self._mixer.music.load(path)
                self._mixer.music.set_volume(volume)
                self._mixer.music.play(loops)
                self._current_bgm = name
            except Exception:
                pass

    def stop_bgm(self):
        if not self._available:
            return
        try:
            self._mixer.music.fadeout(300)
            self._current_bgm = None
        except Exception:
            pass

    def cleanup(self):
        if self._available:
            try:
                self._mixer.quit()
            except Exception:
                pass
