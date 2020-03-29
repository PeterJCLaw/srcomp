import unittest

from sr.comp.teams import Team


class TeamTests(unittest.TestCase):
    def test_plain(self):
        t = Team('ABC', "name", rookie=False, dropped_out_after=4)

        self.assertFalse(t.rookie)
        self.assertTrue(t.is_still_around(3))
        self.assertTrue(t.is_still_around(4))
        self.assertFalse(t.is_still_around(5))
