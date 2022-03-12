import unittest
from typing import Optional
from unittest import mock

from sr.comp.scores import Scores


class LastScoredMatchTests(unittest.TestCase):
    def assertLastScoredMatch(
        self,
        league_lsm: Optional[int],
        knockout_lsm: Optional[int],
        tiebreaker_lsm: Optional[int],
        expected: Optional[int],
    ) -> None:
        league = mock.Mock(last_scored_match=league_lsm)
        knockout = mock.Mock(last_scored_match=knockout_lsm)
        tiebreaker = mock.Mock(last_scored_match=tiebreaker_lsm)

        scores = Scores(league, knockout, tiebreaker)

        self.assertEqual(expected, scores.last_scored_match)

    def test_no_scores_yet(self) -> None:
        self.assertLastScoredMatch(None, None, None, None)

    def test_league_only(self) -> None:
        self.assertLastScoredMatch(13, None, None, 13)

    def test_knockout_only_not_actually_valid(self) -> None:
        self.assertLastScoredMatch(None, 42, None, 42)

    def test_tiebreaker_only_not_actually_valid(self) -> None:
        self.assertLastScoredMatch(None, None, 42, 42)

    def test_league_and_knockout_only(self) -> None:
        self.assertLastScoredMatch(13, 42, None, 42)

    def test_all_present_always_choose_tiebreaker_value_a(self) -> None:
        self.assertLastScoredMatch(13, 37, 42, 42)

    def test_all_present_always_choose_tiebreaker_value_b(self) -> None:
        self.assertLastScoredMatch(42, 37, 13, 13)
