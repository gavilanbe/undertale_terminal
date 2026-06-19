import unittest

from combat import (
    BlobHazard,
    BlinkHazard,
    Bullet,
    CombatScene,
    Telegraph,
)
from engine import Game


def make_combat(monster_name):
    game = Game()
    game.audio = None
    scene = CombatScene(game, monster_name)
    scene.turn = 1
    return scene


class AttackPatternTests(unittest.TestCase):
    def test_blob_hazard_previews_before_it_damages(self):
        hazard = BlobHazard(10, 3, warning_time=0.5, max_radius=2)

        self.assertEqual(list(hazard.cells()), [])
        self.assertGreater(len(list(hazard.cells(preview=True))), 1)

        hazard.update(0.49)
        self.assertEqual(list(hazard.cells()), [])

        hazard.update(0.02)
        self.assertNotEqual(list(hazard.cells()), [])

    def test_cursor_attack_is_built_from_warned_prompt_chunks(self):
        scene = make_combat("Cursor")
        scene._spawn_blink(progress=0.0)

        self.assertTrue(scene.hazards)
        self.assertTrue(all(isinstance(h, BlinkHazard) for h in scene.hazards))
        self.assertTrue(all(h.timer < 0 for h in scene.hazards))

    def test_ping_first_wave_is_a_single_horizontal_request(self):
        scene = make_combat("Ping")
        scene._spawn_echo(speed_mult=1.0, progress=0.0)

        self.assertEqual(len(scene.bullets), 1)
        self.assertEqual(scene.bullets[0].vy, 0)

    def test_null_curtain_keeps_a_readable_gap(self):
        scene = make_combat("Null")
        scene._spawn_tears(speed_mult=1.0, progress=0.0)

        blocked = {int(b.x) for b in scene.bullets}
        open_cols = [x for x in range(scene.arena_w) if x not in blocked]
        longest_gap = 0
        run = 0
        prev = None
        for col in open_cols:
            run = run + 1 if prev is not None and col == prev + 1 else 1
            longest_gap = max(longest_gap, run)
            prev = col
        self.assertGreaterEqual(longest_gap, 7)

    def test_pkmn_replays_warned_columns_as_bolts(self):
        scene = make_combat("Pkmn")
        scene.bullet_spawn_count = 0
        scene._spawn_electric(speed_mult=1.0, progress=0.0)

        self.assertTrue(any(isinstance(h, Telegraph) for h in scene.hazards))
        warned_cols = {
            hx
            for h in scene.hazards
            if isinstance(h, Telegraph)
            for hx, _hy in h.cells()
        }
        self.assertEqual(scene.bullets, [])

        scene.bullet_spawn_count = 1
        scene._spawn_electric(speed_mult=1.0, progress=0.0)
        self.assertTrue(any(isinstance(b, Bullet) for b in scene.bullets))
        self.assertTrue({int(b.x) for b in scene.bullets}.issubset(warned_cols))
        self.assertTrue(all(b.vx == 0 for b in scene.bullets))

    def test_daemon_bullets_do_not_bounce_without_bounce_charges(self):
        scene = make_combat("Daemon")
        bullet = Bullet(0, 2, vx=-3.0, vy=0, bounces=0)
        scene.bullets = [bullet]
        scene.bullet_timer = -100.0
        scene.attack_duration = 99.0
        scene._upd_attack(0.1, [])

        self.assertLess(bullet.vx, 0)


if __name__ == "__main__":
    unittest.main()
