from __future__ import annotations

import datetime
import random
import unittest
from collections import OrderedDict
from collections.abc import Collection, Mapping
from unittest import mock

from league_ranker import RankedPosition

from sr.comp.knockout_scheduler.base_scheduler import (
    BaseKnockoutScheduler,
    UNKNOWABLE_TEAM,
)
from sr.comp.match_period import Delay, MatchSlot
from sr.comp.scores import LeaguePosition, LeaguePositions
from sr.comp.teams import Team
from sr.comp.types import ArenaName, GamePoints, MatchId, TLA

from .factories import build_match, FakeSchedule


def get_scheduler(
    matches: list[MatchSlot] | None = None,
    positions: LeaguePositions | None = None,
    knockout_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]] | None = None,
    league_game_points: dict[MatchId, Mapping[TLA, GamePoints]] | None = None,
    delays: Collection[Delay] | None = None,
    teams: dict[TLA, Team] | None = None,
    num_teams_per_arena: int = 4,
) -> BaseKnockoutScheduler:
    matches = matches or []
    delays = delays or []
    match_duration = datetime.timedelta(minutes=5)
    league_game_points = league_game_points or {}
    knockout_positions = knockout_positions or {}

    if not positions:
        positions = OrderedDict()
        positions[TLA('ABC')] = LeaguePosition(1)
        positions[TLA('DEF')] = LeaguePosition(2)

    if teams is None:
        teams = {x: Team(x, x, False, None) for x in positions.keys()}

    league_schedule = FakeSchedule(
        matches=matches,
        delays=delays,
        match_duration=match_duration,
    )
    league_scores = mock.Mock(
        positions=positions,
        game_points=league_game_points,
    )
    knockout_scores = mock.Mock(resolved_positions=knockout_positions)
    scores = mock.Mock(league=league_scores, knockout=knockout_scores)

    period_config = {
        'description': "A description of the period",
        'start_time': datetime.datetime(2014, 3, 27, 13),
        'end_time':   datetime.datetime(2014, 3, 27, 17, 30),  # noqa:E241
    }
    config = {
        'match_periods': {'knockout': [period_config]},
    }
    arenas = [ArenaName('A')]

    scheduler = BaseKnockoutScheduler(
        league_schedule,
        scores,
        arenas,
        num_teams_per_arena,
        teams,
        config=config,
    )
    return scheduler


class BaseKnockoutSchedulerTests(unittest.TestCase):
    def test_get_ranking_unknowable(self) -> None:
        resolved_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]]
        resolved_positions = {}
        scheduler = get_scheduler(
            knockout_positions=resolved_positions,
        )

        for n_teams in range(1, 6):
            with self.subTest(n_teams=n_teams):
                teams = [TLA(f'ABC{x}') for x in range(n_teams)]
                random.shuffle(teams)
                self.assertEqual(
                    [UNKNOWABLE_TEAM] * len(teams),
                    scheduler.get_ranking(
                        build_match(num=1, arena='main', teams=teams),
                    ),
                )

    def test_get_ranking_unknowable_with_empty_zones(self) -> None:
        resolved_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]]
        resolved_positions = {}
        scheduler = get_scheduler(
            knockout_positions=resolved_positions,
        )

        for n_teams in range(1, 6):
            with self.subTest(n_teams=n_teams):
                teams: list[TLA | None]
                teams = [TLA(f'ABC{x}') for x in range(n_teams)]
                teams[0] = None
                random.shuffle(teams)
                self.assertEqual(
                    # Rankings consist only of teams, no null placeholders
                    [UNKNOWABLE_TEAM] * (n_teams - 1),
                    scheduler.get_ranking(
                        build_match(num=1, arena='main', teams=teams),
                    ),
                )

    def test_get_ranking_match_played(self) -> None:
        match = build_match(num=1, arena='main', teams=[
            TLA('ABC'),
            TLA('DEF'),
            TLA('GHI'),
            TLA('JKL'),
        ])

        resolved_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]]
        resolved_positions = {
            (match.arena, match.num): {
                TLA('GHI'): RankedPosition(1),
                TLA('DEF'): RankedPosition(2),
                TLA('ABC'): RankedPosition(3),
                TLA('JKL'): RankedPosition(4),
            },
        }
        scheduler = get_scheduler(
            knockout_positions=resolved_positions,
        )

        self.assertEqual(
            ['GHI', 'DEF', 'ABC', 'JKL'],
            scheduler.get_ranking(match),
        )

    def test_get_ranking_match_played_with_empty_zones(self) -> None:
        match = build_match(num=1, arena='main', teams=[
            TLA('ABC'),
            None,
            TLA('GHI'),
            TLA('JKL'),
        ])

        resolved_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]]
        resolved_positions = {
            (match.arena, match.num): {
                TLA('GHI'): RankedPosition(1),
                TLA('JKL'): RankedPosition(2),
                TLA('ABC'): RankedPosition(3),
            },
        }
        scheduler = get_scheduler(
            knockout_positions=resolved_positions,
        )

        self.assertEqual(
            ['GHI', 'JKL', 'ABC'],
            scheduler.get_ranking(match),
        )

    def test_get_seeds_unknowable(self) -> None:
        scheduler = get_scheduler(matches=[
            # Fake an unplayed league match
            MatchSlot({}),
        ])
        self.assertEqual(
            ['ABC', 'DEF'],
            scheduler._get_seeds(),
        )

    def test_get_seeds_known(self) -> None:
        scheduler = get_scheduler()
        self.assertEqual(
            ['ABC', 'DEF'],
            scheduler._get_seeds(),
        )
