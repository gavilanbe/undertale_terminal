import unittest
from types import SimpleNamespace

from endings import REQUIRED_RECOVERY_FLAGS, resolve_ending


def make_game(**overrides):
    data = {
        "flags": {"daemon_spared": True, **{flag: True for flag in REQUIRED_RECOVERY_FLAGS}},
        "kill_count": 0,
        "spare_count": 6,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class EndingResolutionTests(unittest.TestCase):
    def test_pacifist_requires_complete_recovery(self):
        self.assertEqual(resolve_ending(make_game()), "pacifist")

        flags = {"daemon_spared": True}
        self.assertEqual(resolve_ending(make_game(flags=flags)), "neutral_spare")

        missing_identity = {
            "daemon_spared": True,
            **{flag: True for flag in REQUIRED_RECOVERY_FLAGS if flag != "has_core_dump"},
        }
        self.assertEqual(
            resolve_ending(make_game(flags=missing_identity)),
            "neutral_spare",
        )

    def test_kill_routes_still_branch_on_spares(self):
        self.assertEqual(
            resolve_ending(make_game(flags={"daemon_killed": True}, spare_count=0)),
            "genocide",
        )
        self.assertEqual(
            resolve_ending(make_game(flags={"daemon_killed": True}, spare_count=2)),
            "neutral_kill",
        )


if __name__ == "__main__":
    unittest.main()
