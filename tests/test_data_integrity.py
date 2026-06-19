import unittest

from engine import MIN_WIDTH
from game_data import (
    TILE_EXIT,
    TILE_GATE,
    TILE_ITEM,
    TILE_LOCKED,
    TILE_MONSTER,
    TILE_NPC,
    TILE_MIRROR,
    TILE_PUSH_BLOCK,
    TILE_ROUTER,
    TILE_SIGN,
    TILE_SIGN2,
    TILE_SOCKET,
    TILE_SWITCH,
    TILE_VAULT,
)
from items import ITEMS
from monsters import MONSTER_DATA
from npcs import NPC_DATA
from title import COMPACT_TITLE_ART
from zones import ZONES


class ZoneDataIntegrityTests(unittest.TestCase):
    def test_maps_are_rectangular(self):
        for zone_name, zone in ZONES.items():
            widths = {len(row) for row in zone["map"]}
            self.assertEqual(
                len(widths), 1,
                f"{zone_name} has inconsistent row widths: {sorted(widths)}",
            )

    def test_registry_positions_match_map_tiles(self):
        expectations = {
            "monsters": (TILE_MONSTER,),
            "items": (TILE_ITEM,),
            "npcs": (TILE_NPC,),
            "locked": (TILE_LOCKED,),
            "vaults": (TILE_VAULT,),
            "signs": (TILE_SIGN, TILE_SIGN2),
        }
        for zone_name, zone in ZONES.items():
            tilemap = zone["map"]
            height = len(tilemap)
            width = len(tilemap[0])
            for registry_name, valid_tiles in expectations.items():
                for x, y in zone.get(registry_name, {}):
                    self.assertTrue(
                        0 <= x < width and 0 <= y < height,
                        f"{zone_name}.{registry_name} position {(x, y)} is out of bounds",
                    )
                    self.assertIn(
                        tilemap[y][x],
                        valid_tiles,
                        f"{zone_name}.{registry_name} position {(x, y)} is on {tilemap[y][x]!r}",
                    )

    def test_exits_and_exit_conditions_are_valid(self):
        for zone_name, zone in ZONES.items():
            exit_data = zone.get("exit")
            self.assertIsNotNone(exit_data, f"{zone_name} is missing exit data")
            x, y = exit_data["pos"]
            self.assertEqual(zone["map"][y][x], TILE_EXIT)

            target = exit_data["target_zone"]
            self.assertTrue(
                target == "ENDING" or target in ZONES,
                f"{zone_name} exit targets unknown zone {target!r}",
            )

            for condition in exit_data.get("conditions", []):
                if condition.get("type") == "defeat_monster":
                    self.assertIn(condition["pos"], zone.get("monsters", {}))

    def test_puzzle_positions_are_valid(self):
        for zone_name, zone in ZONES.items():
            tilemap = zone["map"]
            for puzzle_id, puzzle in zone.get("puzzles", {}).items():
                if puzzle.get("type") == "sequence":
                    switch_ids = {switch["id"] for switch in puzzle["switches"]}
                    self.assertEqual(set(puzzle["correct_order"]), switch_ids)
                    switch_positions = [switch["pos"] for switch in puzzle["switches"]]
                else:
                    switch_positions = [puzzle["switch_pos"]]

                for x, y in switch_positions:
                    self.assertEqual(
                        tilemap[y][x], TILE_SWITCH,
                        f"{zone_name}.{puzzle_id} switch {(x, y)} is not on #",
                    )

                for x, y in puzzle["gate_positions"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_GATE,
                        f"{zone_name}.{puzzle_id} gate {(x, y)} is not on G",
                    )

                for requirement in puzzle.get("required_flags", []):
                    self.assertEqual(len(requirement), 2)
                    self.assertIsInstance(requirement[1], str)
                    self.assertTrue(requirement[1])

    def test_conditional_gate_positions_are_valid(self):
        for zone_name, zone in ZONES.items():
            tilemap = zone["map"]
            for gate_id, gate in zone.get("conditional_gates", {}).items():
                for x, y in gate["gate_positions"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_GATE,
                        f"{zone_name}.{gate_id} gate {(x, y)} is not on G",
                    )
                for requirement in gate.get("required_flags", []):
                    self.assertEqual(len(requirement), 2)
                    self.assertIsInstance(requirement[1], str)
                    self.assertTrue(requirement[1])

    def test_push_puzzle_positions_are_valid(self):
        for zone_name, zone in ZONES.items():
            tilemap = zone["map"]
            for puzzle_id, puzzle in zone.get("push_puzzles", {}).items():
                for x, y in puzzle["blocks"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_PUSH_BLOCK,
                        f"{zone_name}.{puzzle_id} block {(x, y)} is not on B",
                    )
                for x, y in puzzle["sockets"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_SOCKET,
                        f"{zone_name}.{puzzle_id} socket {(x, y)} is not on O",
                    )
                for x, y in puzzle["gate_positions"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_GATE,
                        f"{zone_name}.{puzzle_id} gate {(x, y)} is not on G",
                    )
                for requirement in puzzle.get("required_flags", []):
                    self.assertEqual(len(requirement), 2)
                    self.assertIsInstance(requirement[1], str)
                    self.assertTrue(requirement[1])

    def test_dial_puzzle_positions_are_valid(self):
        for zone_name, zone in ZONES.items():
            tilemap = zone["map"]
            for puzzle_id, puzzle in zone.get("dial_puzzles", {}).items():
                for (x, y), node in puzzle["nodes"].items():
                    self.assertIn(
                        tilemap[y][x], (TILE_ROUTER, TILE_MIRROR),
                        f"{zone_name}.{puzzle_id} dial {(x, y)} is not on a dial tile",
                    )
                    self.assertIn("solution", node)
                    self.assertGreaterEqual(node.get("initial", 0), 0)
                    self.assertLess(node["solution"], puzzle.get("states", 4))
                for x, y in puzzle["gate_positions"]:
                    self.assertEqual(
                        tilemap[y][x], TILE_GATE,
                        f"{zone_name}.{puzzle_id} gate {(x, y)} is not on G",
                    )
                for requirement in puzzle.get("required_flags", []):
                    self.assertEqual(len(requirement), 2)
                    self.assertIsInstance(requirement[1], str)
                    self.assertTrue(requirement[1])

    def test_referenced_content_exists(self):
        for zone_name, zone in ZONES.items():
            for pos, monster_name in zone.get("monsters", {}).items():
                self.assertIn(monster_name, MONSTER_DATA, f"{zone_name} monster {pos}")
            for pos, item_name in zone.get("items", {}).items():
                self.assertIn(item_name, ITEMS, f"{zone_name} item {pos}")
            for pos, npc_name in zone.get("npcs", {}).items():
                self.assertIn(npc_name, NPC_DATA, f"{zone_name} npc {pos}")

        for monster_name, monster in MONSTER_DATA.items():
            drop = monster.get("drop_on_kill")
            if drop:
                self.assertIn(drop, ITEMS, f"{monster_name} drops unknown item")

    def test_vault_protocol_requirements_are_well_formed(self):
        known_protocol_flags = {
            f"protocol_{monster_name.lower()}_resolved"
            for monster_name in MONSTER_DATA
        }
        for zone_name, zone in ZONES.items():
            for pos, vault in zone.get("vaults", {}).items():
                for flag, label in vault.get("required_flags", []):
                    self.assertIn(flag, known_protocol_flags, f"{zone_name} vault {pos}")
                    self.assertIsInstance(label, str)
                    self.assertTrue(label)

    def test_protocol_panel_copy_fits_combat_box(self):
        # Combat protocol panel clips these fields to arena_w - 4 (36 chars).
        for monster_name, monster in MONSTER_DATA.items():
            for key in ("protocol_name", "protocol_goal", "attack_hint"):
                value = monster.get(key, "")
                self.assertIsInstance(value, str, f"{monster_name}.{key}")
                self.assertTrue(value, f"{monster_name}.{key}")
                self.assertLessEqual(
                    len(value), 36,
                    f"{monster_name}.{key} is too long for the protocol panel",
                )

    def test_attack_rule_copy_fits_battle_textbox(self):
        for monster_name, monster in MONSTER_DATA.items():
            for key in ("attack_rule", "attack_read"):
                value = monster.get(key, "")
                self.assertIsInstance(value, str, f"{monster_name}.{key}")
                self.assertTrue(value, f"{monster_name}.{key}")
                self.assertLessEqual(
                    len(value), 30,
                    f"{monster_name}.{key} is too long for the battle textbox",
                )

    def test_battle_guidance_copy_fits_combat_panel(self):
        # The protocol box has 36 usable columns.
        for monster_name, monster in MONSTER_DATA.items():
            route = monster.get("protocol_route")
            self.assertIsInstance(route, str, f"{monster_name}.protocol_route")
            self.assertTrue(route)
            self.assertLessEqual(
                min(len(f"MERCY: {route}"), len(f"M: {route}")),
                36,
                f"{monster_name}.protocol_route is too long for the protocol panel",
            )

            act_hints = monster.get("act_hints", {})
            for option in monster.get("act_options", []):
                key = option.lower()
                self.assertIn(key, act_hints, f"{monster_name}.{key} lacks ACT hint")
                self.assertLessEqual(
                    len(act_hints[key]),
                    36,
                    f"{monster_name}.{key} ACT hint is too long",
                )

            for key in ("attack_rule_sequence", "attack_read_sequence"):
                for line in monster.get(key, []):
                    self.assertLessEqual(
                        len(line),
                        30,
                        f"{monster_name}.{key} line is too long",
                    )

    def test_compact_title_fits_minimum_terminal_width(self):
        self.assertLessEqual(max(len(line) for line in COMPACT_TITLE_ART), MIN_WIDTH)


if __name__ == "__main__":
    unittest.main()
