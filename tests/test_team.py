import unittest

from sr.comp.teams import Team
from sr.comp.types import MatchNumber, TLA


class TeamTests(unittest.TestCase):
    def test_plain(self) -> None:
        t = Team(TLA('ABC'), "name", rookie=False, dropped_out_after=MatchNumber(4))

        self.assertFalse(t.rookie)
        self.assertTrue(t.is_still_around(MatchNumber(3)))
        self.assertTrue(t.is_still_around(MatchNumber(4)))
        self.assertFalse(t.is_still_around(MatchNumber(5)))
