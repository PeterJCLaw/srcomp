import itertools
import operator
import unittest
from typing import Any

from league_ranker import LeaguePoints

from sr.comp.scores import TeamScore
from sr.comp.types import GamePoints

# Note: these tests deliberately have inline comparisons rather than making
# "better" use of the various helpers in `unittest.TestCase` because we're
# testing that the comparisons work and this is clearer what's being tested.


class TeamScoreTests(unittest.TestCase):
    def test_empty_ctor(self) -> None:
        ts = TeamScore()
        self.assertTrue(ts.game_points == 0)
        self.assertTrue(ts.league_points == 0)

    def test_ctor_args(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts.game_points == 5)
        self.assertTrue(ts.league_points == 4)

    def test_not_equal_none(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertFalse(ts == None)  # noqa:E711  # intentional None equality check
        self.assertTrue(ts != None)  # noqa:E711  # intentional None equality check

    def test_not_equal_empty(self) -> None:
        ts1 = TeamScore()
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts1 != ts2)
        self.assertTrue(ts2 != ts1)
        self.assertFalse(ts1 == ts2)
        self.assertFalse(ts2 == ts1)

    def test_equal_self_empty(self) -> None:
        ts = TeamScore()
        self.assertTrue(ts == ts)
        self.assertFalse(ts != ts)

    def test_equal_self(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts == ts)
        self.assertFalse(ts != ts)

    def test_equal_other_same_values(self) -> None:
        ts1 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts1 == ts2)
        self.assertTrue(ts2 == ts1)
        self.assertFalse(ts1 != ts2)
        self.assertFalse(ts2 != ts1)

    def test_not_equal_other_similar_values(self) -> None:
        ts1 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(6))
        self.assertTrue(ts1 != ts2)
        self.assertTrue(ts2 != ts1)
        self.assertFalse(ts1 == ts2)
        self.assertFalse(ts2 == ts1)


class TeamScoreRichComparisonTests(unittest.TestCase):
    # Scores with more points are greater than those with fewer

    def assertRichComparisons(self, smaller: Any, larger: Any) -> None:
        self.assertTrue(smaller < larger)
        self.assertTrue(smaller <= larger)
        self.assertTrue(larger > smaller)
        self.assertTrue(larger >= smaller)
        self.assertFalse(smaller > larger)
        self.assertFalse(smaller >= larger)
        self.assertFalse(larger < smaller)
        self.assertFalse(larger <= smaller)

    def test_assertion_helper(self) -> None:
        self.assertRichComparisons(1, 2)

    def test_assertion_helper_fail(self) -> None:
        with self.assertRaises(AssertionError):
            self.assertRichComparisons(2, 1)

    def test_none(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))

        comparisons = [
            operator.lt,
            operator.le,
            operator.gt,
            operator.ge,
        ]

        for op, (a, b) in itertools.product(
            comparisons,
            itertools.permutations((ts, None)),
        ):
            with self.subTest("{} {} {}".format(a, op.__name__, b)):
                with self.assertRaisesRegex(
                    TypeError,
                    r'(unorderable types|not supported between instances of)',
                ):
                    op(a, b)

    def test_empty(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        empty = TeamScore()
        self.assertRichComparisons(empty, ts)

    def test_self(self) -> None:
        ts = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts >= ts)
        self.assertTrue(ts <= ts)
        self.assertFalse(ts > ts)
        self.assertFalse(ts < ts)

    def test_same_values(self) -> None:
        ts1 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertTrue(ts1 >= ts2)
        self.assertTrue(ts1 <= ts2)
        self.assertFalse(ts1 > ts2)
        self.assertFalse(ts1 < ts2)

    def test_same_game(self) -> None:
        ts1 = TeamScore(game=GamePoints(5), league=LeaguePoints(3))
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        self.assertRichComparisons(ts1, ts2)

    def test_same_league(self) -> None:
        ts2 = TeamScore(game=GamePoints(15), league=LeaguePoints(4))
        ts1 = TeamScore(game=GamePoints(5), league=LeaguePoints(4))
        # Tied on league points, but game points differentiate
        self.assertRichComparisons(ts1, ts2)

    def test_both_differ(self) -> None:
        ts2 = TeamScore(game=GamePoints(5), league=LeaguePoints(10))
        ts1 = TeamScore(game=GamePoints(25), league=LeaguePoints(4))
        # Only care about league points really -- game are tie-break only
        self.assertRichComparisons(ts1, ts2)
