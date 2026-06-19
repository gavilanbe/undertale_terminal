import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import save_system


def make_game(**overrides):
    data = {
        "player_name": "TEST",
        "player_hp": 13,
        "player_max_hp": 24,
        "player_lv": 2,
        "player_exp": 7,
        "player_atk": 12,
        "player_buf": 2,
        "player_max_buf": 4,
        "gold": 9,
        "difficulty": "HARD",
        "inventory": ["Cookie", "Patch"],
        "current_zone": "RUINS_2",
        "player_x": 14,
        "player_y": 9,
        "defeated_monsters": {"RUINS_1:13,18"},
        "collected_items": {"RUINS_1:21,12"},
        "flags": {"intro_shown": True},
        "puzzle_state": {"RUINS_1:tutorial": True},
        "kill_count": 1,
        "spare_count": 2,
        "ppid": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class SaveSystemTests(unittest.TestCase):
    def setUp(self):
        self._old_save_path = os.environ.get(save_system.SAVE_PATH_ENV)
        self.tempdir = tempfile.TemporaryDirectory()
        self.save_path = os.path.join(self.tempdir.name, "save.json")
        os.environ[save_system.SAVE_PATH_ENV] = self.save_path

    def tearDown(self):
        self.tempdir.cleanup()
        if self._old_save_path is None:
            os.environ.pop(save_system.SAVE_PATH_ENV, None)
        else:
            os.environ[save_system.SAVE_PATH_ENV] = self._old_save_path

    def test_save_load_delete_roundtrip_uses_overridden_path(self):
        game = make_game()

        self.assertTrue(save_system.save_game(game))
        self.assertTrue(save_system.save_exists())
        self.assertTrue(os.path.exists(self.save_path))

        loaded = make_game(
            player_name="EMPTY",
            defeated_monsters=set(),
            collected_items=set(),
            flags={},
            puzzle_state={},
        )
        self.assertTrue(save_system.load_game(loaded))

        self.assertEqual(loaded.player_name, "TEST")
        self.assertEqual(loaded.player_hp, 13)
        self.assertEqual(loaded.inventory, ["Cookie", "Patch"])
        self.assertEqual(loaded.defeated_monsters, {"RUINS_1:13,18"})
        self.assertEqual(loaded.collected_items, {"RUINS_1:21,12"})
        self.assertEqual(loaded.flags, {"intro_shown": True})
        self.assertEqual(loaded.puzzle_state, {"RUINS_1:tutorial": True})
        self.assertEqual(loaded.kill_count, 1)
        self.assertEqual(loaded.spare_count, 2)
        self.assertEqual(loaded.ppid, 1)

        save_system.delete_save()
        self.assertFalse(save_system.save_exists())

    def test_newer_save_versions_are_rejected(self):
        with open(self.save_path, "w") as handle:
            json.dump({"version": save_system.SAVE_VERSION + 1}, handle)

        game = make_game(player_name="UNCHANGED")
        self.assertFalse(save_system.load_game(game))
        self.assertEqual(game.player_name, "UNCHANGED")


if __name__ == "__main__":
    unittest.main()
