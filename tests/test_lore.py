import unittest

from engine import Game
from lore import (
    current_objective,
    identity_line,
    missing_protocol_names,
    protocol_count,
    route_consequence_line,
    trace_lines,
)


class LoreTraceTests(unittest.TestCase):
    def test_varlog_objective_names_missing_protocol_processes(self):
        game = Game()
        game.current_zone = "RUINS_2"
        game.flags = {"protocol_ping_resolved": True}

        self.assertEqual(current_objective(game), "East wing still needs Pkmn.")
        self.assertIn("Pkmn", missing_protocol_names(game))

    def test_identity_and_route_lines_react_to_core_dump_and_kills(self):
        game = Game()

        self.assertIn("PPID unknown", identity_line(game))
        self.assertIn("Clean route intact", route_consequence_line(game))

        game.flags["has_core_dump"] = True
        game.kill_count = 1

        self.assertIn("PPID := 1", identity_line(game))
        self.assertIn("Forced closures", route_consequence_line(game))

    def test_trace_lines_include_objective_and_signature_count(self):
        game = Game()
        game.current_zone = "RUINS_1"
        game.flags = {
            "protocol_cursor_resolved": True,
            "protocol_ping_resolved": True,
        }

        lines = trace_lines(game)

        self.assertEqual(protocol_count(game), 2)
        self.assertIn(("Signatures", "2/6 synced"), lines)
        self.assertTrue(any(label == "Objective" for label, _text in lines))

    def test_home_objective_follows_map_order_before_cursor(self):
        game = Game()
        game.current_zone = "RUINS_1"

        self.assertEqual(current_objective(game), "Open the first switch gate.")

        game.puzzle_state["RUINS_1:tutorial"] = True
        self.assertEqual(current_objective(game), "Boot order: PID1, HOME, NET.")

        game.puzzle_state["RUINS_1:boot_sequence"] = True
        self.assertEqual(current_objective(game), "Sync Cursor at the exit scanner.")


if __name__ == "__main__":
    unittest.main()
