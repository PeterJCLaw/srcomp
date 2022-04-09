import collections
import dataclasses
import unittest
from typing import List, Mapping, Optional, Tuple
from unittest import mock

from league_ranker import LeaguePoints, RankedPosition

from sr.comp.match_period import MatchType
from sr.comp.scores import (
    KnockoutScores,
    LeagueScores,
    MatchScore,
    Scores,
    TiebreakerScores,
)
from sr.comp.types import ArenaName, GamePoints, MatchNumber, TLA

from .factories import build_match, build_score_data, FakeScorer


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


class GetScoresTests(unittest.TestCase):
    maxDiff = 8000

    def as_game_points(self, data: Mapping[str, int]) -> Mapping[TLA, GamePoints]:
        return {TLA(x): GamePoints(y) for x, y in data.items()}

    def as_normalised_points(self, data: Mapping[str, int]) -> Mapping[TLA, LeaguePoints]:
        return {TLA(x): LeaguePoints(y) for x, y in data.items()}

    def as_ranked_position(self, data: List[Tuple[str, int]]) -> Mapping[TLA, RankedPosition]:
        return collections.OrderedDict(
            (TLA(x), RankedPosition(y))
            for x, y in data
        )

    def build_scores(self) -> Scores:
        raw_league_score = build_score_data(
            arena='A',
            num=0,
            scores=self.league_game,
        )
        raw_knockout_score = build_score_data(
            arena='A',
            num=3,
            scores=self.knockout_game,
        )
        raw_tiebreaker_score = build_score_data(
            arena='A',
            num=7,
            scores=self.tiebreaker_game,
        )

        teams = raw_league_score['teams'].keys()

        league = LeagueScores(
            [raw_league_score],
            teams,
            FakeScorer,
            num_teams_per_arena=len(teams),
        )
        knockout = KnockoutScores(
            [raw_knockout_score],
            teams,
            FakeScorer,
            num_teams_per_arena=len(teams),
            league_positions=league.positions,
        )
        tiebreaker = TiebreakerScores(
            [raw_tiebreaker_score],
            teams,
            FakeScorer,
            num_teams_per_arena=len(teams),
            league_positions=league.positions,
        )

        return Scores(league, knockout, tiebreaker)

    def get_scores(
        self,
        num: int,
        arena: str,
        type_: MatchType,
        use_resolved_ranking: bool = False,
    ) -> Optional[MatchScore]:
        scores = self.build_scores()
        return scores.get_scores(build_match(
            num=num,
            arena=arena,
            type_=type_,
            use_resolved_ranking=use_resolved_ranking,
        ))

    def assertMatchScore(self, expected: MatchScore, actual: Optional[MatchScore]) -> None:
        self.assertIsNotNone(actual, "Should have a valid score")
        self.assertEqual(
            dataclasses.asdict(expected),
            dataclasses.asdict(actual),
        )

    def setUp(self) -> None:
        super().setUp()
        self.league_game = {
            'JMS': 4,
            'PAS': 0,
            'RUN': 8,
            'ICE': 2,
        }
        self.knockout_game = {
            'JMS': 7,
            'PAS': 4,
            'RUN': 6,
            'ICE': 3,
        }
        self.tiebreaker_game = {
            'JMS': 1,
            'PAS': 2,
            'RUN': 3,
            'ICE': 9,
        }

    def test_no_match(self) -> None:
        actual = self.get_scores(num=1, arena='B', type_=MatchType.league)
        self.assertIsNone(actual)

    def test_league_match(self) -> None:
        actual = self.get_scores(
            num=0,
            arena='A',
            type_=MatchType.league,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(0)),
            game=self.as_game_points(self.league_game),
            normalised=self.as_normalised_points({
                'JMS': 6,
                'PAS': 2,
                'RUN': 8,
                'ICE': 4,
            }),
            ranking=self.as_ranked_position([
                ('RUN', 1),
                ('JMS', 2),
                ('ICE', 3),
                ('PAS', 4),
            ]),
        )
        self.assertMatchScore(expected, actual)

    def test_knockout_match_no_tie(self) -> None:
        actual = self.get_scores(
            num=3,
            arena='A',
            type_=MatchType.knockout,
            use_resolved_ranking=True,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(3)),
            game=self.as_game_points(self.knockout_game),
            normalised=self.as_normalised_points({
                'JMS': 8,
                'PAS': 4,
                'RUN': 6,
                'ICE': 2,
            }),
            ranking=self.as_ranked_position([
                ('JMS', 1),
                ('RUN', 2),
                ('PAS', 3),
                ('ICE', 4),
            ]),
        )
        self.assertMatchScore(expected, actual)

    def test_knockout_match_tie_broke_by_league_points(self) -> None:
        self.knockout_game = {
            'JMS': 7,
            'PAS': 7,
            'RUN': 7,
            'ICE': 7,
        }

        actual = self.get_scores(
            num=3,
            arena='A',
            type_=MatchType.knockout,
            # Knockout matches don't actually allow ties
            use_resolved_ranking=True,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(3)),
            game=self.as_game_points(self.knockout_game),
            normalised=self.as_normalised_points({
                'JMS': 5,
                'PAS': 5,
                'RUN': 5,
                'ICE': 5,
            }),
            ranking=self.as_ranked_position([
                ('RUN', 1),
                ('JMS', 2),
                ('ICE', 3),
                ('PAS', 4),
            ]),
        )
        self.assertMatchScore(expected, actual)

    def test_finals_match_no_tie(self) -> None:
        actual = self.get_scores(
            num=3,
            arena='A',
            type_=MatchType.knockout,
            use_resolved_ranking=False,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(3)),
            game=self.as_game_points(self.knockout_game),
            normalised=self.as_normalised_points({
                'JMS': 8,
                'PAS': 4,
                'RUN': 6,
                'ICE': 2,
            }),
            ranking=self.as_ranked_position([
                ('JMS', 1),
                ('RUN', 2),
                ('PAS', 3),
                ('ICE', 4),
            ]),
        )
        self.assertMatchScore(expected, actual)

    def test_finals_match_with_tie(self) -> None:
        self.knockout_game = {
            'JMS': 7,
            'PAS': 5,
            'RUN': 7,
            'ICE': 5,
        }

        actual = self.get_scores(
            num=3,
            arena='A',
            type_=MatchType.knockout,
            # The final admits the possibility of a tie
            use_resolved_ranking=False,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(3)),
            game=self.as_game_points(self.knockout_game),
            normalised=self.as_normalised_points({
                'JMS': 7,
                'PAS': 3,
                'RUN': 7,
                'ICE': 3,
            }),
            ranking=self.as_ranked_position([
                ('JMS', 1),
                ('RUN', 1),
                ('ICE', 3),
                ('PAS', 3),
            ]),
        )
        self.assertMatchScore(expected, actual)

    def test_tiebreaker_match(self) -> None:
        actual = self.get_scores(
            num=7,
            arena='A',
            type_=MatchType.tiebreaker,
        )

        expected = MatchScore(
            match_id=(ArenaName('A'), MatchNumber(7)),
            game=self.as_game_points(self.tiebreaker_game),
            normalised=self.as_normalised_points({
                'JMS': 2,
                'PAS': 4,
                'RUN': 6,
                'ICE': 8,
            }),
            ranking=self.as_ranked_position([
                ('ICE', 1),
                ('RUN', 2),
                ('PAS', 3),
                ('JMS', 4),
            ]),
        )
        self.assertMatchScore(expected, actual)
