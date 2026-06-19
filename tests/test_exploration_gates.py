import unittest

from engine import Game
from exploration import ExplorationScene, ST_DIALOGUE
from game_data import (
    TILE_GATE,
    TILE_GATE_OPEN,
    TILE_MONSTER,
    TILE_PUSH_BLOCK,
    TILE_SOCKET,
)


def make_scene(zone_name, flags=None, puzzle_state=None):
    game = Game()
    game.audio = None
    game.current_zone = zone_name
    game.player_x = 0
    game.player_y = 0
    game.flags = dict(flags or {})
    game.puzzle_state = dict(puzzle_state or {})
    return ExplorationScene(game, zone_name)


def make_scene_at(zone_name, pos, flags=None, puzzle_state=None):
    game = Game()
    game.audio = None
    game.current_zone = zone_name
    game.player_x, game.player_y = pos
    game.flags = dict(flags or {})
    game.puzzle_state = dict(puzzle_state or {})
    return ExplorationScene(game, zone_name)


def reachable(scene, target, blocked_tiles=None):
    blocked_tiles = set(blocked_tiles or [])
    frontier = [(scene.px, scene.py)]
    seen = {(scene.px, scene.py)}
    while frontier:
        x, y = frontier.pop(0)
        if (x, y) == target:
            return True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen or not scene._walkable(nx, ny):
                continue
            if scene.tilemap[ny][nx] in blocked_tiles:
                continue
            seen.add((nx, ny))
            frontier.append((nx, ny))
    return False


def can_reach_or_touch(scene, target):
    if reachable(scene, target):
        return True
    x, y = target
    return any(
        reachable(scene, (x + dx, y + dy))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
    )


class ExplorationGateTests(unittest.TestCase):
    def test_home_boot_sequence_is_on_the_main_route(self):
        exit_pos = (24, 20)

        blocked = make_scene("RUINS_1", puzzle_state={
            "RUINS_1:tutorial": True,
        })
        self.assertFalse(reachable(blocked, exit_pos))

        opened = make_scene("RUINS_1", puzzle_state={
            "RUINS_1:tutorial": True,
            "RUINS_1:boot_sequence": True,
        })
        self.assertTrue(reachable(opened, exit_pos))
        self.assertFalse(reachable(opened, exit_pos, blocked_tiles={TILE_MONSTER}))

    def test_router_gate_points_player_to_missing_processes(self):
        scene = make_scene("RUINS_2", {"protocol_ping_resolved": True})
        msg = scene._puzzle_gate_message(14, 14)

        self.assertIn("missing proof", msg)
        self.assertIn("Pkmn", msg)
        self.assertIn("battle", msg)

    def test_varlog_layout_reads_as_index_two_wings_then_south_log(self):
        scene = make_scene("RUINS_2")

        for target in [
            (10, 6),  # grep in INDEX
            (14, 6),  # central vault
            (5, 9),   # Ping blocks NET.LOG
            (24, 9),  # Pkmn blocks ROM.LOG
            (10, 13), # west router node
            (14, 13), # compiler node
            (18, 13), # east router node
        ]:
            self.assertTrue(can_reach_or_touch(scene, target), target)

        for proof_room_target in [
            (2, 9),   # NET.LOG reward behind Ping
            (27, 9),  # ROM.LOG session terminal behind Pkmn
        ]:
            self.assertFalse(
                reachable(scene, proof_room_target, blocked_tiles={TILE_MONSTER}),
                proof_room_target,
            )

        self.assertFalse(reachable(scene, (14, 20)))

        opened = make_scene(
            "RUINS_2",
            {
                "protocol_ping_resolved": True,
                "protocol_pkmn_resolved": True,
                "vault_opened": True,
            },
            {"RUINS_2:router_compile": True},
        )
        self.assertTrue(reachable(opened, (14, 20)))
        self.assertFalse(reachable(opened, (14, 20), blocked_tiles={TILE_MONSTER}))

    def test_varlog_router_requires_signatures_and_dial_alignment(self):
        closed = make_scene("RUINS_2", {"protocol_ping_resolved": True})
        closed._interact_dial(10, 13)
        self.assertEqual(closed.state, ST_DIALOGUE)
        self.assertEqual(closed.tilemap[14][13], TILE_GATE)

        missing_checksum = make_scene("RUINS_2", {
            "protocol_ping_resolved": True,
            "protocol_pkmn_resolved": True,
        })
        missing_checksum._interact_dial(10, 13)
        self.assertEqual(missing_checksum.state, ST_DIALOGUE)
        self.assertIn("INDEX vault", missing_checksum.typewriter.text)

        opened = make_scene("RUINS_2", {
            "protocol_ping_resolved": True,
            "protocol_pkmn_resolved": True,
            "vault_opened": True,
        })
        opened._interact_dial(10, 13)
        for _ in range(3):
            opened._interact_dial(14, 13)
        for _ in range(3):
            opened._interact_dial(18, 13)
        self.assertEqual(opened.tilemap[14][13], TILE_GATE_OPEN)

    def test_varlog_old_save_inside_revised_wall_is_rescued(self):
        scene = make_scene_at("RUINS_2", (8, 10))

        self.assertNotEqual((scene.px, scene.py), (8, 10))
        self.assertTrue(scene._walkable(scene.px, scene.py))
        self.assertEqual((scene.game.player_x, scene.game.player_y),
                         (scene.px, scene.py))

    def test_multi_page_dialogue_is_paginated_to_fit_box(self):
        scene = make_scene("RUINS_2")
        scene._open_multi_dialogue(["one\ntwo\nthree\nfour\nfive"])

        self.assertEqual(scene.dialogue_pages, [
            "one\ntwo\nthree\nfour",
            "five",
        ])

    def test_recovery_alcove_opens_after_push_socket_and_checksum(self):
        closed = make_scene("RUINS_BOSS")
        self.assertEqual(closed.tilemap[16][8], TILE_PUSH_BLOCK)
        self.assertEqual(closed.tilemap[16][6], TILE_SOCKET)
        closed._try_push_block(8, 16, -1, 0)
        closed._try_push_block(7, 16, -1, 0)
        self.assertEqual(closed.tilemap[16][5], TILE_GATE)

        revisited = make_scene("RUINS_BOSS", {"vault_opened": True})
        revisited.game.puzzle_state = dict(closed.game.puzzle_state)
        revisited = ExplorationScene(revisited.game, "RUINS_BOSS")
        self.assertEqual(revisited.tilemap[16][5], TILE_GATE_OPEN)

        opened = make_scene("RUINS_BOSS", {"vault_opened": True})
        opened._try_push_block(8, 16, -1, 0)
        opened._try_push_block(7, 16, -1, 0)
        self.assertEqual(opened.tilemap[16][5], TILE_GATE_OPEN)

    def test_mirror_dials_require_resolved_identity(self):
        scene = make_scene("RUINS_DAEMON")
        scene._interact_dial(5, 10)

        self.assertEqual(scene.state, ST_DIALOGUE)
        self.assertIn("Resolve your PPID", scene.typewriter.text)
        self.assertNotIn("RUINS_DAEMON:identity_mirrors", scene.game.puzzle_state)

        solved = make_scene("RUINS_DAEMON", {"has_core_dump": True})
        solved._interact_dial(5, 10)
        solved._interact_dial(14, 10)
        for _ in range(3):
            solved._interact_dial(24, 10)
        self.assertEqual(solved.tilemap[15][12], TILE_GATE_OPEN)


if __name__ == "__main__":
    unittest.main()
