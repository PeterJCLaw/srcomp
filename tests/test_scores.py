import unittest
from pathlib import Path
from typing import Optional
from unittest import mock

from sr.comp.scores import Scores


class ScoresTests(unittest.TestCase):
    def assertScores(
        self,
        league_lsm: Optional[int],
        knockout_lsm: Optional[int],
        tiebreaker_lsm: Optional[int],
        expected: Optional[int],
    ) -> None:
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

            scores = Scores(Path(), (), mock.Mock(), 0)

            self.assertEqual(expected, scores.last_scored_match)

    def test_no_scores_yet(self) -> None:
        self.assertScores(None, None, None, None)

    def test_league_only(self) -> None:
        self.assertScores(13, None, None, 13)

    def test_knockout_only_not_actually_valid(self) -> None:
        self.assertScores(None, 42, None, 42)

    def test_tiebreaker_only_not_actually_valid(self) -> None:
        self.assertScores(None, None, 42, 42)

    def test_league_and_knockout_only(self) -> None:
        self.assertScores(13, 42, None, 42)

    def test_all_present_always_choose_tiebreaker_value_a(self) -> None:
        self.assertScores(13, 37, 42, 42)

    def test_all_present_always_choose_tiebreaker_value_b(self) -> None:
        self.assertScores(42, 37, 13, 13)
