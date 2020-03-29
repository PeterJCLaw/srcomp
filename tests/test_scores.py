import unittest
from unittest import mock

from sr.comp.scores import Scores


class ScoresTests(unittest.TestCase):
    def assertScores(self, league_lsm, knockout_lsm, tiebreaker_lsm, expected):
        with mock.patch(
            'sr.comp.scores.LeagueScores',
        ) as ls, mock.patch(
            'sr.comp.scores.KnockoutScores',
        ) as ks, mock.patch(
            'sr.comp.scores.TiebreakerScores',
        ) as ts:
            ls.return_value = mock.Mock(last_scored_match=league_lsm)
            ks.return_value = mock.Mock(last_scored_match=knockout_lsm)
            ts.return_value = mock.Mock(last_scored_match=tiebreaker_lsm)

            scores = Scores('', None, None, 0)

            lsm = scores.last_scored_match
            assert expected == lsm

    def test_no_scores_yet(self):
        self.assertScores(None, None, None, None)

    def test_league_only(self):
        self.assertScores(13, None, None, 13)

    def test_knockout_only_not_actually_vaild(self):
        self.assertScores(None, 42, None, 42)

    def test_tiebreaker_only_not_actually_vaild(self):
        self.assertScores(None, None, 42, 42)

    def test_league_and_knockout_only(self):
        self.assertScores(13, 42, None, 42)

    def test_all_present_always_choose_tiebreaker_value_a(self):
        self.assertScores(13, 37, 42, 42)

    def test_all_present_always_choose_tiebreaker_value_b(self):
        self.assertScores(42, 37, 13, 13)
