from __future__ import annotations

import unittest
from collections import OrderedDict
from typing import cast, Mapping

from league_ranker import LeaguePoints, RankedPosition

from sr.comp.scores import KnockoutScores, LeaguePosition
from sr.comp.types import TLA


class KnockoutScoresTests(unittest.TestCase):
    def calculate_ranking(
        self,
        match_points: Mapping[str, float],
        league_positions: Mapping[str, int],
    ) -> dict[TLA, RankedPosition]:
        return KnockoutScores.calculate_ranking(
            {TLA(k): cast(LeaguePoints, v) for k, v in match_points.items()},
            {TLA(k): LeaguePosition(v) for k, v in league_positions.items()},
        )

    def test_positions_simple(self) -> None:
        knockout_points = {
            'ABC': 1.0,
            'DEF': 2.0,
            'GHI': 3.0,
            'JKL': 4.0,
        }

        positions = self.calculate_ranking(knockout_points, {})

        expected = OrderedDict([
            ('JKL', 1),
            ('GHI', 2),
            ('DEF', 3),
            ('ABC', 4),
        ])

        self.assertEqual(expected, positions)

    def test_positions_tie_bottom(self) -> None:
        knockout_points = {
            'ABC': 1.5,
            'DEF': 1.5,
            'GHI': 3,
            'JKL': 4,
        }

        positions = self.calculate_ranking(knockout_points, {})

        expected = OrderedDict([
            ('JKL', 1),
            ('GHI', 2),
            ('ABC', 3),
            ('DEF', 3),
        ])

        self.assertEqual(expected, positions)

    def test_positions_tie_top_with_league_positions(self) -> None:
        knockout_points = {
            'ABC': 1,
            'DEF': 2,
            'GHI': 3.5,
            'JKL': 3.5,
        }
        league_positions = {
            'ABC': 1,
            'DEF': 2,
            'GHI': 3,
            'JKL': 4,
        }
        positions = self.calculate_ranking(knockout_points, league_positions)

        # Tie should be resolved by league positions
        expected = OrderedDict([
            ('GHI', 1),
            ('JKL', 2),
            ('DEF', 3),
            ('ABC', 4),
        ])

        self.assertEqual(expected, positions)

    def test_knockout_match_winners_tie(self) -> None:
        knockout_points = {
            'ABC': 1,
            'DEF': 2.5,
            'GHI': 2.5,
            'JKL': 4,
        }
        # Deliberately out of order as some python implementations
        # use the creation order of the tuples as a fallback sort comparison
        league_positions = {
            'ABC': 1,
            'DEF': 4,
            'GHI': 3,
            'JKL': 2,
        }
        positions = self.calculate_ranking(knockout_points, league_positions)

        # Tie should be resolved by league positions
        expected = OrderedDict([
            ('JKL', 1),
            ('GHI', 2),
            ('DEF', 3),
            ('ABC', 4),
        ])

        self.assertEqual(expected, positions)
