import unittest

from sr.comp.scores import TeamScore

# Note: these tests deliberately have inline comparisons rather than making
# "better" use of the various helpers in `unittest.TestCase` because we're
# testing that the comparisons work and this is clearer what's being tested.


class TeamScoreTests(unittest.TestCase):
    def test_empty_ctor(self):
        ts = TeamScore()
        self.assertTrue(ts.game_points == 0)
        self.assertTrue(ts.league_points == 0)

    def test_ctor_args(self):
        ts = TeamScore(game=5, league=4.2)
        self.assertTrue(ts.game_points == 5)
        self.assertTrue(ts.league_points == 4.2)

    def test_not_equal_none(self):
        ts = TeamScore(game=5, league=4.2)
        self.assertFalse(ts == None)  # noqa:E711  # intentional None equality check
        self.assertTrue(ts != None)  # noqa:E711  # intentional None equality check

    def test_not_equal_empty(self):
        ts1 = TeamScore()
        ts2 = TeamScore(game=5, league=4.2)
        self.assertTrue(ts1 != ts2)
        self.assertTrue(ts2 != ts1)
        self.assertFalse(ts1 == ts2)
        self.assertFalse(ts2 == ts1)

    def test_equal_self_empty(self):
        ts = TeamScore()
        self.assertTrue(ts == ts)
        self.assertFalse(ts != ts)

    def test_equal_self(self):
        ts = TeamScore(game=5, league=4.5)
        self.assertTrue(ts == ts)
        self.assertFalse(ts != ts)

    def test_equal_other_same_values(self):
        ts1 = TeamScore(game=5, league=4.5)
        ts2 = TeamScore(game=5, league=4.5)
        self.assertTrue(ts1 == ts2)
        self.assertTrue(ts2 == ts1)
        self.assertFalse(ts1 != ts2)
        self.assertFalse(ts2 != ts1)

    def test_not_equal_other_similar_values(self):
        ts1 = TeamScore(game=5, league=4)
        ts2 = TeamScore(game=5, league=4.5)
        self.assertTrue(ts1 != ts2)
        self.assertTrue(ts2 != ts1)
        self.assertFalse(ts1 == ts2)
        self.assertFalse(ts2 == ts1)


class TeamScoreRichComparisonTests(unittest.TestCase):
    # Scores with more points are greater than those with fewer

    def assertRichComparisons(self, smaller, larger):
        self.assertTrue(smaller < larger)
        self.assertTrue(smaller <= larger)
        self.assertTrue(larger > smaller)
        self.assertTrue(larger >= smaller)
        self.assertFalse(smaller > larger)
        self.assertFalse(smaller >= larger)
        self.assertFalse(larger < smaller)
        self.assertFalse(larger <= smaller)

    def test_assertion_helper(self):
        self.assertRichComparisons(1, 2)

    def test_assertion_helper_fail(self):
        with self.assertRaises(AssertionError):
            self.assertRichComparisons(2, 1)

    def test_none(self):
        ts = TeamScore(game=5, league=4)
        self.assertRichComparisons(None, ts)

    def test_empty(self):
        ts = TeamScore(game=5, league=4)
        empty = TeamScore()
        self.assertRichComparisons(empty, ts)

    def test_self(self):
        ts = TeamScore(game=5, league=4)
        self.assertTrue(ts >= ts)
        self.assertTrue(ts <= ts)
        self.assertFalse(ts > ts)
        self.assertFalse(ts < ts)

    def test_same_values(self):
        ts1 = TeamScore(game=5, league=4)
        ts2 = TeamScore(game=5, league=4)
        self.assertTrue(ts1 >= ts2)
        self.assertTrue(ts1 <= ts2)
        self.assertFalse(ts1 > ts2)
        self.assertFalse(ts1 < ts2)

    def test_same_game(self):
        ts1 = TeamScore(game=5, league=4)
        ts2 = TeamScore(game=5, league=4.5)
        self.assertRichComparisons(ts1, ts2)

    def test_same_league(self):
        ts2 = TeamScore(game=15, league=4)
        ts1 = TeamScore(game=5, league=4)
        # Tied on league points, but game points differentiate
        self.assertRichComparisons(ts1, ts2)

    def test_both_differ(self):
        ts2 = TeamScore(game=5, league=10)
        ts1 = TeamScore(game=25, league=4)
        # Only care about league points really -- game are tie-break only
        self.assertRichComparisons(ts1, ts2)
