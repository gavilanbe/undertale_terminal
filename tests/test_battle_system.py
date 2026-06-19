import unittest

from battle_system import ProtocolEngine
from combat import CombatScene, S
from engine import Game
from monsters import get_monster


class BattleSystemTests(unittest.TestCase):
    def test_protocol_enforces_order_and_unlocks_spare(self):
        protocol = ProtocolEngine(get_monster("Cursor"))

        self.assertIn("Type x2", protocol.route_line())
        self.assertEqual(protocol.current_step_name(), "type")
        self.assertIn("ACT Type (1/2)", protocol.next_action_line(turn=0))

        wrong = protocol.use_act("logoff", turn=0)
        self.assertFalse(wrong.advanced)
        self.assertFalse(protocol.can_spare)

        protocol.use_act("type", turn=0)
        self.assertIn("ACT Type (2/2)", protocol.next_action_line(turn=1))
        protocol.use_act("type", turn=1)
        self.assertEqual(protocol.current_step_name(), "logoff")
        self.assertFalse(protocol.can_spare)
        protocol.use_act("logoff", turn=2)

        self.assertTrue(protocol.can_spare)
        self.assertEqual(protocol.next_action_line(turn=2), "NEXT: ^C is ready.")
        self.assertEqual(protocol.progress_dict()["0:type"], 2)
        self.assertEqual(protocol.progress_dict()["1:logoff"], 1)

    def test_daemon_protocol_waits_for_pressure_proof(self):
        protocol = ProtocolEngine(get_monster("Daemon"))

        protocol.use_act("listen", turn=0)
        protocol.use_act("persist", turn=1)
        protocol.use_act("persist", turn=2)
        result = protocol.use_act("persist", turn=3)

        self.assertTrue(result.advanced)
        self.assertFalse(protocol.can_spare)
        proof = protocol.on_turn_end(turn=4, hitless=True)
        self.assertTrue(proof.spare_ready)
        self.assertTrue(protocol.can_spare)

    def test_null_requires_hitless_endurance_after_acknowledge(self):
        protocol = ProtocolEngine(get_monster("Null"))

        result = protocol.use_act("acknowledge", turn=0)
        self.assertTrue(result.survival_pending)
        self.assertFalse(protocol.can_spare)

        failed = protocol.on_turn_end(turn=1, hitless=False)
        self.assertIn("flinch", failed.text)
        self.assertFalse(protocol.can_spare)

        protocol.use_act("acknowledge", turn=1)
        passed = protocol.on_turn_end(turn=2, hitless=True)
        self.assertTrue(passed.spare_ready)
        self.assertTrue(protocol.can_spare)

    def test_buffer_absorption_breaks_perfect_turn(self):
        game = Game()
        game.audio = None
        game.player_buf = 3
        scene = CombatScene(game, "Ping")
        scene.state = S.ENEMY_ATTACK
        scene.hitless_turn = True
        scene.soul_x = 1
        scene.soul_y = 1
        scene.bullets = []
        scene.hazards = []
        scene.invuln = 0

        from combat import Bullet
        scene.bullets = [Bullet(1, 1, vx=0, vy=0)]
        scene._upd_attack(0.01, [])

        self.assertFalse(scene.hitless_turn)
        self.assertLess(game.player_buf, 3)


if __name__ == "__main__":
    unittest.main()
