import unittest

from sr.comp.scores import TeamScore


class TeamScoreTests(unittest.TestCase):
    def test_empty_ctor(self):
        ts = TeamScore()
        assert ts.game_points == 0
        assert ts.league_points == 0

    def test_ctor_args(self):
        ts = TeamScore(game=5, league=4.2)
        assert ts.game_points == 5
        assert ts.league_points == 4.2

    def test_not_equal_none(self):
        ts = TeamScore(game=5, league=4.2)
        assert not ts == None  # noqa:E711  # intentional None equality check
        assert ts != None  # noqa:E711  # intentional None equality check

    def test_not_equal_empty(self):
        ts1 = TeamScore()
        ts2 = TeamScore(game=5, league=4.2)
        assert ts1 != ts2
        assert ts2 != ts1
        assert not ts1 == ts2
        assert not ts2 == ts1

    def test_equal_self_empty(self):
        ts = TeamScore()
        assert ts == ts
        assert not ts != ts

    def test_equal_self(self):
        ts = TeamScore(game=5, league=4.5)
        assert ts == ts
        assert not ts != ts

    def test_equal_other_same_values(self):
        ts1 = TeamScore(game=5, league=4.5)
        ts2 = TeamScore(game=5, league=4.5)
        assert ts1 == ts2
        assert ts2 == ts1
        assert not ts1 != ts2
        assert not ts2 != ts1

    def test_not_equal_other_similar_values(self):
        ts1 = TeamScore(game=5, league=4)
        ts2 = TeamScore(game=5, league=4.5)
        assert ts1 != ts2
        assert ts2 != ts1
        assert not ts1 == ts2
        assert not ts2 == ts1


class TeamScoreRichComparisonTests(unittest.TestCase):
    # Scores with more points are greater than those with fewer

    def assertRichComparisons(self, smaller, larger):
        assert smaller < larger
        assert smaller <= larger
        assert larger > smaller
        assert larger >= smaller
        assert not smaller > larger
        assert not smaller >= larger
        assert not larger < smaller
        assert not larger <= smaller

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
        assert ts >= ts
        assert ts <= ts
        assert not ts > ts
        assert not ts < ts

    def test_same_values(self):
        ts1 = TeamScore(game=5, league=4)
        ts2 = TeamScore(game=5, league=4)
        assert ts1 >= ts2
        assert ts1 <= ts2
        assert not ts1 > ts2
        assert not ts1 < ts2

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
